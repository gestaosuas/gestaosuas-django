from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import OperationalError, ProgrammingError
from django.db.models import Count, Q, Sum
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse
from django.http import JsonResponse, HttpResponseForbidden, Http404
from django.template.loader import render_to_string

from apps.accounts.mixins import DirectorateAccessMixin, user_has_directorate_access
import json
import uuid
import math
import unicodedata
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def strip_accents(text):
    """Remove acentos de uma string para comparação insensível a acentuação."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

BIMESTER_LABELS = ["Jan/Fev", "Mar/Abr", "Mai/Jun", "Jul/Ago", "Set/Out", "Nov/Dez"]
BIMESTER_OPTIONS = [(i + 1, f"{i+1}o Bimestre ({BIMESTER_LABELS[i]})") for i in range(6)]

def current_bimester():
    return math.ceil(datetime.now().month / 2)

def bimester_months(bimester):
    return (bimester - 1) * 2 + 1, bimester * 2

def get_persistent_bimester(request):
    bimester = request.GET.get("bimestre")
    if bimester is not None:
        request.session["selected_bimester"] = bimester
    else:
        bimester = request.session.get("selected_bimester", str(current_bimester()))
    return bimester



from .models import Directorate, Osc, Visit, WorkPlan, MonthlyReport, FormDelegation
from apps.beneficios.models import BeneficiosReport
from apps.accounts.models import Profile, ProfileDirectorate
from apps.core.notifications import log_activity


def _fix_str_encoding(value):
    if not isinstance(value, str):
        return value
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return value


def normalize_plan_blocks(content):
    if not isinstance(content, list):
        return []

    normalized = []
    for index, block in enumerate(content, start=1):
        if not isinstance(block, dict):
            continue

        block_type = block.get("type", "paragraph")
        block_content = _fix_str_encoding(block.get("content", ""))
        normalized.append(
            {
                "index": index,
                "type": block_type,
                "content": block_content,
            }
        )
    return normalized


def get_latest_work_plan_for_osc(directorate_id, osc_id):
    if not osc_id:
        return None

    return (
        WorkPlan.objects
        .filter(directorate_id=directorate_id, osc_id=osc_id)
        .order_by("-updated_at", "-created_at")
        .first()
    )


def build_work_plan_document_context(plan):
    osc = plan.osc
    directorate = plan.directorate
    return {
        "plan": plan,
        "osc": osc,
        "directorate": directorate,
        "document_title": plan.title or f"Plano de Trabalho - {osc.name}",
        "content_blocks": normalize_plan_blocks(plan.content),
        "generated_at": datetime.now(),
    }


def get_user_display_name(user):
    profile = getattr(user, "profile", None)
    if profile and profile.full_name:
        return profile.full_name
    return user.get_full_name() or user.get_username()


def get_request_user_display_name(request):
    return get_user_display_name(request.user)


def build_registered_by_map(visits):
    """Fallback para visitas antigas cujo identificacao JSON nunca gravou o nome de quem
    registrou (dado que so passou a ser capturado em 2026-07) - usa o user_id (FK real,
    sempre presente) para resolver um nome/departamento via Profile em vez de "Desconhecido"."""
    missing_user_ids = {
        v.user_id
        for v in visits
        if v.user_id
        and not ((v.identificacao or {}).get("registered_by_name") or (v.identificacao or {}).get("registrado_por"))
    }
    if not missing_user_ids:
        return {}
    profiles = Profile.objects.filter(user_id__in=missing_user_ids).select_related("user")
    return {profile.user_id: get_user_display_name(profile.user) for profile in profiles}


def title_name(value):
    return " ".join(part.capitalize() for part in str(value or "").split())


def _save_file_locally(file_obj, path):
    from django.conf import settings
    import os
    local_path = os.path.join(str(settings.MEDIA_ROOT), path)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    file_obj.seek(0)
    with open(local_path, "wb") as f:
        f.write(file_obj.read())
    return reverse("core:protected-media", kwargs={"file_path": path})


def upload_to_supabase(file_obj, path):
    from django.conf import settings
    import urllib.request
    import urllib.error

    supabase_url = getattr(settings, "SUPABASE_URL", "")
    anon_key = getattr(settings, "SUPABASE_ANON_KEY", "")
    bucket = "system-assets"

    if not supabase_url or not anon_key:
        return _save_file_locally(file_obj, path)

    # Resetar o ponteiro do arquivo para garantir leitura do inicio
    file_obj.seek(0)
    data = file_obj.read()
    
    # URL para upload no Supabase Storage
    url = f"{supabase_url}/storage/v1/object/{bucket}/{path}"
    
    headers = {
        "apikey": anon_key,
        "Authorization": f"Bearer {anon_key}",
        "Content-Type": getattr(file_obj, 'content_type', 'application/octet-stream')
    }

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            # Se der certo, retornamos a URL publica
            return f"{supabase_url}/storage/v1/object/public/{bucket}/{path}"
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        if e.code == 409: # Arquivo ja existe
            return f"{supabase_url}/storage/v1/object/public/{bucket}/{path}"
        logger.error("ERRO SUPABASE STORAGE (fallback local) — URL: %s | Status: %s | Corpo: %s", url, e.code, error_body)
        return _save_file_locally(file_obj, path)
    except Exception as e:
        logger.error("ERRO INESPERADO NO UPLOAD (fallback local) — %s", str(e))
        return _save_file_locally(file_obj, path)

def append_visit_uploaded_documents(visit, files, request=None):
    from django.contrib import messages
    document_fields = {
        "balanco_financeiro": "Balanço Financeiro",
        "fotos_camera": "Foto / Evidência",
        "fotos_galeria": "Foto / Evidência",
    }
    documents = list(visit.documents or [])
    upload_errors = []

    for field_name, label in document_fields.items():
        uploaded_files = files.getlist(field_name)
        for uploaded_file in uploaded_files:
            import uuid
            ext = uploaded_file.name.split('.')[-1]
            unique_name = f"{uuid.uuid4()}.{ext}"
            path = f"visitas/evidencias/{visit.pk}/{unique_name}"
            
            url = upload_to_supabase(uploaded_file, path)
            
            if url:
                documents.append({
                    "name": uploaded_file.name,
                    "type": label,
                    "field": field_name,
                    "url": url,
                    "uploaded_at": datetime.now().isoformat(),
                })
            else:
                upload_errors.append(uploaded_file.name)

    if upload_errors and request:
        messages.warning(request, f"Nao foi possivel salvar as seguintes fotos: {', '.join(upload_errors)}. Verifique a conexao com o Supabase.")

    visit.documents = documents


def sync_atendimento_pse_fields(atendimento, priority=None):
    if not isinstance(atendimento, dict):
        return atendimento
    if "pse_data" not in atendimento or not isinstance(atendimento["pse_data"], dict):
        atendimento["pse_data"] = {}
    pse_data = atendimento["pse_data"]
    
    # Sync Toggle
    if priority == "pse_data":
        if "item5_enabled" in pse_data and pse_data["item5_enabled"] is not None:
            atendimento["pse_habilitado"] = "sim" if pse_data["item5_enabled"] else "nao"
    elif priority == "atendimento":
        if "pse_habilitado" in atendimento and atendimento["pse_habilitado"] is not None:
            pse_data["item5_enabled"] = (atendimento["pse_habilitado"] == "sim")
    else:
        # Default smart check
        if "pse_habilitado" in atendimento and atendimento["pse_habilitado"] is not None:
            pse_data["item5_enabled"] = (atendimento["pse_habilitado"] == "sim")
        elif "item5_enabled" in pse_data and pse_data["item5_enabled"] is not None:
            atendimento["pse_habilitado"] = "sim" if pse_data["item5_enabled"] else "nao"

    # Sync Period
    if priority == "pse_data":
        if "item5_periodo" in pse_data and pse_data["item5_periodo"] is not None:
            atendimento["pse_periodo"] = pse_data["item5_periodo"]
    elif priority == "atendimento":
        if "pse_periodo" in atendimento and atendimento["pse_periodo"] is not None:
            pse_data["item5_periodo"] = atendimento["pse_periodo"]
    else:
        # Default smart check: prefer non-empty string
        pse_periodo_val = atendimento.get("pse_periodo")
        item5_periodo_val = pse_data.get("item5_periodo")
        if isinstance(pse_periodo_val, str) and pse_periodo_val.strip():
            pse_data["item5_periodo"] = pse_periodo_val
        elif isinstance(item5_periodo_val, str) and item5_periodo_val.strip():
            atendimento["pse_periodo"] = item5_periodo_val
        else:
            if pse_periodo_val is not None:
                pse_data["item5_periodo"] = pse_periodo_val
            elif item5_periodo_val is not None:
                atendimento["pse_periodo"] = item5_periodo_val

    # Sync Qualitative
    if priority == "pse_data":
        if "item5_qualitativos" in pse_data and isinstance(pse_data["item5_qualitativos"], list):
            atendimento["pse_qualitativos"] = pse_data["item5_qualitativos"]
    elif priority == "atendimento":
        if "pse_qualitativos" in atendimento and isinstance(atendimento["pse_qualitativos"], list):
            pse_data["item5_qualitativos"] = atendimento["pse_qualitativos"]
    else:
        # Default smart check: check which one has actual user-entered data
        has_atend_qual = False
        if "pse_qualitativos" in atendimento and isinstance(atendimento["pse_qualitativos"], list):
            for row in atendimento["pse_qualitativos"]:
                if isinstance(row, dict) and any(str(v).strip() for v in row.values()):
                    has_atend_qual = True
                    break
        
        has_pse_qual = False
        if "item5_qualitativos" in pse_data and isinstance(pse_data["item5_qualitativos"], list):
            for row in pse_data["item5_qualitativos"]:
                if isinstance(row, dict) and any(str(v).strip() for v in row.values()):
                    has_pse_qual = True
                    break

        if has_pse_qual and not has_atend_qual:
            atendimento["pse_qualitativos"] = pse_data["item5_qualitativos"]
        elif has_atend_qual:
            pse_data["item5_qualitativos"] = atendimento["pse_qualitativos"]
        else:
            # Fallback to whatever exists
            if "pse_qualitativos" in atendimento and isinstance(atendimento["pse_qualitativos"], list):
                pse_data["item5_qualitativos"] = atendimento["pse_qualitativos"]
            elif "item5_qualitativos" in pse_data and isinstance(pse_data["item5_qualitativos"], list):
                atendimento["pse_qualitativos"] = pse_data["item5_qualitativos"]

    # Sync Quantitative
    quant_map = {
        "usuarios_primeiro_dia": "total_1dia",
        "usuarios_inseridos": "inseridos",
        "usuarios_desligados": "desligados",
        "usuarios_ultimo_dia": "total_ultimo"
    }
    
    if priority == "pse_data":
        if "item5_quantitativos" in pse_data and isinstance(pse_data["item5_quantitativos"], dict):
            if "pse_quantitativos" not in atendimento or not isinstance(atendimento["pse_quantitativos"], dict):
                atendimento["pse_quantitativos"] = {}
            for inst_key, rep_key in quant_map.items():
                if rep_key in pse_data["item5_quantitativos"]:
                    atendimento["pse_quantitativos"][inst_key] = pse_data["item5_quantitativos"][rep_key]
    elif priority == "atendimento":
        if "pse_quantitativos" in atendimento and isinstance(atendimento["pse_quantitativos"], dict):
            if "item5_quantitativos" not in pse_data or not isinstance(pse_data["item5_quantitativos"], dict):
                pse_data["item5_quantitativos"] = {}
            for inst_key, rep_key in quant_map.items():
                if inst_key in atendimento["pse_quantitativos"]:
                    pse_data["item5_quantitativos"][rep_key] = atendimento["pse_quantitativos"][inst_key]
    else:
        # Default smart check: check which one has actual values
        has_atend_quant = False
        if "pse_quantitativos" in atendimento and isinstance(atendimento["pse_quantitativos"], dict):
            for row_val in atendimento["pse_quantitativos"].values():
                if isinstance(row_val, dict) and any(str(v).strip() for v in row_val.values()):
                    has_atend_quant = True
                    break
        
        has_pse_quant = False
        if "item5_quantitativos" in pse_data and isinstance(pse_data["item5_quantitativos"], dict):
            for row_val in pse_data["item5_quantitativos"].values():
                if isinstance(row_val, dict) and any(str(v).strip() for v in row_val.values()):
                    has_pse_quant = True
                    break

        if has_pse_quant and not has_atend_quant:
            if "pse_quantitativos" not in atendimento or not isinstance(atendimento["pse_quantitativos"], dict):
                atendimento["pse_quantitativos"] = {}
            for inst_key, rep_key in quant_map.items():
                if rep_key in pse_data["item5_quantitativos"]:
                    atendimento["pse_quantitativos"][inst_key] = pse_data["item5_quantitativos"][rep_key]
        elif has_atend_quant or ("pse_quantitativos" in atendimento and isinstance(atendimento["pse_quantitativos"], dict)):
            if "item5_quantitativos" not in pse_data or not isinstance(pse_data["item5_quantitativos"], dict):
                pse_data["item5_quantitativos"] = {}
            for inst_key, rep_key in quant_map.items():
                if inst_key in atendimento["pse_quantitativos"]:
                    pse_data["item5_quantitativos"][rep_key] = atendimento["pse_quantitativos"][inst_key]
        elif "item5_quantitativos" in pse_data and isinstance(pse_data["item5_quantitativos"], dict):
            if "pse_quantitativos" not in atendimento or not isinstance(atendimento["pse_quantitativos"], dict):
                atendimento["pse_quantitativos"] = {}
            for inst_key, rep_key in quant_map.items():
                if rep_key in pse_data["item5_quantitativos"]:
                    atendimento["pse_quantitativos"][inst_key] = pse_data["item5_quantitativos"][rep_key]
                    
    return atendimento


def normalize_visit_attendance(visit, atendimento):
    presentes = atendimento.get("presentes") or {}
    try:
        manha = int(presentes.get("manha") or 0)
    except (TypeError, ValueError):
        manha = 0
    try:
        tarde = int(presentes.get("tarde") or 0)
    except (TypeError, ValueError):
        tarde = 0

    # "Total automatico" (soma manha+tarde no momento da visita) e o UNICO
    # campo calculado aqui -- fica em presentes.total, nao em total_mes.
    # total_mes e um campo de texto livre, editado pelo usuario, e nunca deve
    # ser sobrescrito (bug real reportado em 2026-08-16: digitar a quantidade
    # da manha tambem recalculava o Total/Mes).
    presentes["total"] = str(manha + tarde)
    atendimento["presentes"] = presentes
    subsidized_count = getattr(visit.osc, "subsidized_count", 0)
    atendimento["subvencionados"] = "Conforme Demanda" if subsidized_count == -1 else str(subsidized_count or 0)

    # Sync PSE fields dynamically
    atendimento = sync_atendimento_pse_fields(atendimento)
    return atendimento


def merge_osc_pse_quantitativos(osc, atendimento):
    """Sobrepoe a tabela central de Quantitativos do PSE (Osc.pse_quantitativos)
    na atendimento.pse_quantitativos da visita, pra exibir/editar -- a central
    entra como base (traz o que outras visitas dessa OSC ja preencheram) e o
    que essa visita especifica ja tinha preenchido localmente tem prioridade
    por mes/indicador (nunca perde o que o usuario ja digitou nesta visita)."""
    central = osc.pse_quantitativos if isinstance(osc.pse_quantitativos, dict) else {}
    if not central:
        return atendimento
    own = atendimento.get("pse_quantitativos")
    own = own if isinstance(own, dict) else {}
    merged = {}
    for key in set(list(central.keys()) + list(own.keys())):
        central_months = central.get(key) if isinstance(central.get(key), dict) else {}
        own_months = own.get(key) if isinstance(own.get(key), dict) else {}
        merged[key] = {**central_months, **own_months}
    atendimento["pse_quantitativos"] = merged
    return atendimento


def write_back_osc_pse_quantitativos(osc, atendimento):
    """Contrapartida de merge_osc_pse_quantitativos(): grava o que foi editado
    nesta visita de volta na tabela central da OSC (merge por mes/indicador,
    nunca um overwrite cego -- assim visitas diferentes em epocas diferentes
    va acumulando dados em vez de se apagarem)."""
    quant = atendimento.get("pse_quantitativos") if isinstance(atendimento, dict) else None
    if not isinstance(quant, dict) or not quant:
        return
    central = osc.pse_quantitativos if isinstance(osc.pse_quantitativos, dict) else {}
    for key, months in quant.items():
        if not isinstance(months, dict):
            continue
        central_months = central.get(key) if isinstance(central.get(key), dict) else {}
        non_empty = {m: v for m, v in months.items() if str(v or "").strip()}
        central[key] = {**central_months, **non_empty}
    osc.pse_quantitativos = central
    osc.save(update_fields=["pse_quantitativos"])


def set_nested_value(target, parts, value):
    current = target
    for index, part in enumerate(parts[:-1]):
        next_part = parts[index + 1]
        if part.isdigit():
            part_index = int(part)
            while len(current) <= part_index:
                current.append({} if not next_part.isdigit() else [])
            current = current[part_index]
            continue

        if part not in current:
            current[part] = [] if next_part.isdigit() else {}
        current = current[part]

    last = parts[-1]
    if last.isdigit() and isinstance(current, list):
        last_index = int(last)
        while len(current) <= last_index:
            current.append("")
        current[last_index] = value
    else:
        current[last] = value


def read_bracket_parts(key, prefix):
    prefix_length = len(prefix) + 1
    return key[prefix_length:-1].split("][")


def is_subvencao_directorate(directorate):
    ascii_name = strip_accents((getattr(directorate, "name", "") or "").lower())
    return "subvencao" in ascii_name or "emenda" in ascii_name or "fundo" in ascii_name


def is_emendas_directorate(directorate):
    """Emendas e Fundos (sem incluir Subvenção): os textos do relatório de
    visita vêm do plano de trabalho vinculado, não da OSC."""
    ascii_name = strip_accents((getattr(directorate, "name", "") or "").lower())
    return "emenda" in ascii_name or "fundo" in ascii_name


def is_outros_directorate(directorate):
    """"Outros" usa o mesmo modulo de OSC/Visita que Subvencao/Emendas e Fundos,
    mas com instrumental de visita simplificado (sem Plano de Trabalho, Forma de
    Acesso, Colaboradores/RH nem PSE) e só 2 abas no dashboard."""
    ascii_name = strip_accents((getattr(directorate, "name", "") or "").lower())
    return "outros" in ascii_name


def get_admin_user_ids():
    """IDs de todo usuario admin/superuser - usado pra excluir visitas
    criadas por admin do que o diretor enxerga (docs/dominio 04 A.6,
    refinado 2026-08-17: diretor ve todas as visitas da propria diretoria,
    EXCETO as feitas por admin - so "seus agentes" contam, mesmo se o
    admin em questao nao tiver diretoria nenhuma atribuida)."""
    User = get_user_model()
    return set(
        User.objects.filter(
            Q(is_superuser=True) | Q(profile__role="admin")
        ).values_list("id", flat=True)
    )


def get_monitoramento_theme(directorate):
    """Cor de tema (navbar/cabeçalho) para Subvenção/Emendas e Fundos/Outros —
    mesma lógica usada em MonitoramentoHomeView, reaproveitada aqui pras telas
    de OSC/Visita/Plano de Trabalho (apps/directorates) que também pertencem a
    essas 3 diretorias. Retorna (theme_class, header_class, icon_color)."""
    normalized = (getattr(directorate, "name", "") or "").lower()
    ascii_name = strip_accents(normalized)

    if "emendas" in ascii_name:
        return "theme-amber", "header-amber", "#d97706"
    if "fundos" in ascii_name:
        return "theme-indigo", "header-indigo", "#4338ca"
    if "subvencao" in ascii_name:
        return "theme-emerald", "header-emerald", "#059669"
    if "outros" in normalized:
        return "theme-rose", "header-rose", "#db2777"
    return "theme-emerald", "header-emerald", "#059669"


def get_work_plan_by_id(directorate_id, plan_id):
    if not plan_id:
        return None
    try:
        return WorkPlan.objects.filter(directorate_id=directorate_id, pk=plan_id).first()
    except (ValueError, ValidationError):
        return None


def resolve_visit_work_plan(directorate_id, osc_id, plan_id):
    """Plano de trabalho a vincular na visita: o enviado no formulário (se
    pertencer à OSC) ou, sem envio válido, o único plano da OSC quando ela
    tiver exatamente um."""
    plans = WorkPlan.objects.filter(directorate_id=directorate_id, osc_id=osc_id)
    if plan_id:
        try:
            plan = plans.filter(pk=plan_id).first()
        except (ValueError, ValidationError):
            plan = None
        if plan:
            return plan
    found = list(plans[:2])
    if len(found) == 1:
        return found[0]
    return None


def build_osc_plans_map(directorate_id):
    """Mapa osc_id → [{id, title}] para o select de plano na visita."""
    osc_plans = {}
    plans = WorkPlan.objects.filter(directorate_id=directorate_id).order_by("-updated_at", "title")
    for plan in plans:
        osc_plans.setdefault(str(plan.osc_id), []).append({"id": str(plan.pk), "title": plan.title})
    return osc_plans


def get_visit_report_texts(visit):
    """Textos-base do relatório de visita: preferem o plano de trabalho
    vinculado à visita (Emendas e Fundos); sem plano, ou com o campo vazio
    no plano, caem para os textos da OSC (comportamento original)."""
    osc = visit.osc
    plan = visit.work_plan

    def pick(plan_value, osc_value):
        return (plan_value or "").strip() or (osc_value or "")

    return {
        "objeto": pick(plan.objeto if plan else "", osc.objeto),
        "objetivos": pick(plan.objetivos if plan else "", osc.objetivos),
        "metas": pick(plan.metas if plan else "", osc.metas),
        "atividades": pick(plan.atividades if plan else "", osc.atividades),
    }


def get_monitoring_back_url(directorate):
    """Retorna a URL de volta correta: monitoramento:home para directorias de monitoramento,
    directorates:visit-list para as demais."""
    ascii_name = strip_accents((getattr(directorate, "name", "") or "").lower())
    is_monitoring = (
        "subvencao" in ascii_name
        or "emenda" in ascii_name
        or "fundo" in ascii_name
        or "outros" in ascii_name
    )
    if is_monitoring:
        return reverse("monitoramento:home", kwargs={"pk": directorate.pk})
    return reverse("directorates:visit-list", kwargs={"pk": directorate.pk})


def get_visit_list_redirect(directorate):
    """Para onde mandar o usuario apos criar/editar/finalizar/excluir uma visita:
    a aba "Instrumental de Visita" do dashboard (Subvencao/Emendas e Fundos/Outros,
    que tem sistema de abas) ou a lista avulsa de visitas (demais diretorias, que
    nao usam o dashboard de monitoramento). Ver docs/dominio/04."""
    if is_subvencao_directorate(directorate) or is_outros_directorate(directorate):
        return reverse("monitoramento:home", kwargs={"pk": directorate.pk}) + "?tab=visits"
    return reverse("directorates:visit-list", kwargs={"pk": directorate.pk})


def get_osc_list_redirect(directorate):
    """Mesma ideia de get_visit_list_redirect, mas para a aba 'Cadastrar OSC'."""
    if is_subvencao_directorate(directorate) or is_outros_directorate(directorate):
        return reverse("monitoramento:home", kwargs={"pk": directorate.pk}) + "?tab=oscs"
    return reverse("directorates:osc-list", kwargs={"pk": directorate.pk})


def get_safe_next_url(request):
    from urllib.parse import urlparse
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url:
        parsed = urlparse(next_url)
        if not parsed.netloc and next_url.startswith("/") and not next_url.startswith("//"):
            return next_url
    return ""


class DirectorateScopedMixin(DirectorateAccessMixin):
    """Para views cujo <dir_slug:pk> na URL é diretamente o pk da diretoria."""

    def get_directorate(self):
        directorate = Directorate.objects.filter(pk=self.kwargs.get("pk")).first()
        if not directorate:
            raise Http404("Diretoria não encontrada.")
        return directorate


class _ObjectDirectorateScopedMixin(DirectorateAccessMixin):
    """Para views cujo <uuid:pk> na URL identifica um objeto (Osc/Visit/
    WorkPlan) — não a diretoria diretamente. O acesso é resolvido a partir
    da diretoria a que esse objeto pertence."""

    scope_model = None

    def get_scoped_object(self):
        if not hasattr(self, "_scoped_object"):
            self._scoped_object = get_object_or_404(self.scope_model, pk=self.kwargs["pk"])
        return self._scoped_object

    def get_directorate(self):
        return self.get_scoped_object().directorate


class OscScopedMixin(_ObjectDirectorateScopedMixin):
    scope_model = Osc


class VisitScopedMixin(_ObjectDirectorateScopedMixin):
    scope_model = Visit


class VisitAccessMixin(VisitScopedMixin):
    """Alem do acesso a diretoria (VisitScopedMixin), restringe o acesso a
    visita conforme dono/delegacao/papel (docs/dominio/04-... A.6, refinado
    em 2026-07-25 e 2026-08-17): admin sempre; diretor tem acesso total se
    ele mesmo criou a visita, senao so leitura (GET) - EXCETO se a visita foi
    criada por um admin, caso em que o diretor nao tem acesso nenhum (nao e
    "dos seus agentes"); agente/user so na propria visita ou com
    FormDelegation, senao 403 ja no GET."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        visit = self.get_scoped_object()
        profile = getattr(request.user, "profile", None)
        is_admin = request.user.is_superuser or (profile and profile.role == "admin")
        # Checagem de diretoria primeiro (mesma regra/mensagem de
        # DirectorateAccessMixin) - senao um usuario sem nenhum acesso a
        # diretoria cairia direto no 403 de dono/delegacao abaixo, em vez do
        # redirect padrao "voce nao tem acesso a esta area".
        if not is_admin and not user_has_directorate_access(request.user, visit.directorate):
            messages.error(request, "Você não tem acesso a esta área.")
            return redirect("core:landing")
        is_owner = str(visit.user_id) == str(request.user.id)
        if not is_admin:
            if profile and profile.role == "diretor":
                visit_made_by_admin = str(visit.user_id) in {str(uid) for uid in get_admin_user_ids()}
                if visit_made_by_admin and not is_owner:
                    return HttpResponseForbidden("Você não tem acesso a esta visita.")
                if not is_owner and request.method != "GET":
                    return HttpResponseForbidden("Você não pode editar uma visita que não criou.")
            else:
                is_delegated = FormDelegation.objects.filter(visit=visit, user_id=request.user.id).exists()
                if not (is_owner or is_delegated):
                    return HttpResponseForbidden("Você não tem acesso a esta visita.")
        self.can_edit = is_admin or is_owner or not (profile and profile.role == "diretor")
        return super().dispatch(request, *args, **kwargs)


class WorkPlanScopedMixin(_ObjectDirectorateScopedMixin):
    scope_model = WorkPlan


class DirectorateListView(LoginRequiredMixin, ListView):
    template_name = "directorates/list.html"
    model = Directorate
    context_object_name = "directorates"

    def get_queryset(self):
        try:
            profile = getattr(self.request.user, 'profile', None)
            if not profile or profile.role == 'admin' or self.request.user.is_superuser:
                return Directorate.objects.order_by("name")
            
            # Filter by primary or linked
            linked_ids = ProfileDirectorate.objects.filter(profile=profile).values_list('directorate_id', flat=True)
            ids = list(linked_ids)
            if profile.primary_directorate_id:
                ids.append(profile.primary_directorate_id)
                
            return Directorate.objects.filter(id__in=ids).order_by("name")
        except (OperationalError, ProgrammingError):
            return Directorate.objects.none()


class DirectorateDetailView(DirectorateScopedMixin, DetailView):
    template_name = "directorates/detail.html"
    model = Directorate
    context_object_name = "directorate"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        normalized_name = strip_accents(self.object.name.lower())
        
        if "pop" in normalized_name or "rua" in normalized_name:
            return redirect("poprua:dashboard")
            
        if "benef" in normalized_name:
            return redirect("beneficios:home")
        if "sine" in normalized_name or "qual" in normalized_name or "profissional" in normalized_name:
            return redirect("sinecp:home")
        if "naica" in normalized_name:
            return redirect("naica:home", pk=self.object.pk)
        if "cras" in normalized_name:
            return redirect("cras:home", pk=self.object.pk)
        if "ceai" in normalized_name:
            return redirect("ceai:dashboard")
        if "especial" in normalized_name or "crianca" in normalized_name:
            return redirect("protecaoespecial:home", pk=self.object.pk)
        if "creas" in normalized_name:
            return redirect("creasidoso:home", pk=self.object.pk)
        if "mulher" in normalized_name:
            return redirect("casamulher:home", pk=self.object.pk)
            
        return redirect("monitoramento:home", pk=self.object.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.object
        normalized_name = directorate.name.lower()
        # Versão sem acentos para comparações (ex: "subvenção" → "subvencao")
        ascii_name = strip_accents(normalized_name)

        # Filtering parameters
        year = self.request.GET.get("year", datetime.now().year)
        month = self.request.GET.get("month", "all")
        bimester = get_persistent_bimester(self.request)
        context["selected_year"] = int(year)
        context["selected_month"] = month
        context["selected_bimester"] = bimester
        context["years_range"] = range(2023, datetime.now().year + 1)
        context["months_range"] = [
            (1, "Janeiro"), (2, "Fevereiro"), (3, "Março"), (4, "Abril"),
            (5, "Maio"), (6, "Junho"), (7, "Julho"), (8, "Agosto"),
            (9, "Setembro"), (10, "Outubro"), (11, "Novembro"), (12, "Dezembro")
        ]
        context["bimester_options"] = BIMESTER_OPTIONS

        try:
            context["recent_visits"] = directorate.visits.select_related("osc").all()[:5]
            context["recent_plans"] = directorate.work_plans.select_related("osc").all()[:5]
            context["recent_oscs"] = directorate.oscs.all()[:5]

            # Detecção do tipo de diretoria (insensível a acentos)
            context["is_beneficios"] = "benef" in ascii_name
            context["is_subvencao_only"] = "subvencao" in ascii_name
            context["is_subvencao"] = (
                any(x in ascii_name for x in ["subvencao", "emendas", "fundos"])
                and "outros" not in ascii_name
            )
            context["is_outros"] = "outros" in ascii_name
            context["is_monitoramento"] = context["is_subvencao"] or context["is_outros"]

            if context["is_beneficios"]:
                # ... (existing beneficios logic) ...
                reports = BeneficiosReport.objects.filter(directorate=directorate, year=year).order_by("month")
                context["beneficios_reports"] = reports
                
                # Filtering logic
                current_month_num = None
                if month != "all":
                    current_month_num = int(month)
                    m_report = reports.filter(month=current_month_num).first()
                    prev_month_num = current_month_num - 1 if current_month_num > 1 else 12
                    prev_year = year if current_month_num > 1 else int(year) - 1
                    p_report = BeneficiosReport.objects.filter(directorate=directorate, year=prev_year, month=prev_month_num).first()
                else:
                    # Year total
                    from django.db.models import Sum
                    m_report_data = reports.aggregate(
                        inclusao=Sum("encaminhadas_inclusao_cadunico"),
                        atualizacao=Sum("encaminhadas_atualizacao_cadunico"),
                        pro_pao=Sum("pro_pao"),
                        cesta=Sum("cesta_basica"),
                        familias_pbf=Sum("familias_pbf"),
                        pessoas_cadunico=Sum("pessoas_cadunico"),
                        v_cadunico=Sum("visitas_cadunico"),
                        v_nucleo=Sum("visita_nucleo_habitacao"),
                        v_cesta=Sum("visita_cesta_fraldas_colchoes"),
                        v_dmae=Sum("visita_dmae"),
                        v_propao=Sum("visitas_pro_pao")
                    )
                    m_report = type('obj', (object,), m_report_data) # Fake object
                    p_report = None # No simple comparison for whole year vs prev year for now

                # Metrics and Variations
                def get_var(curr, prev):
                    if not prev or prev == 0: return 0
                    return round(((curr - prev) / prev) * 100, 1)

                if m_report:
                    metrics = {
                        "inclusao": getattr(m_report, "inclusao", m_report.encaminhadas_inclusao_cadunico if hasattr(m_report, "encaminhadas_inclusao_cadunico") else 0),
                        "atualizacao": getattr(m_report, "atualizacao", m_report.encaminhadas_atualizacao_cadunico if hasattr(m_report, "encaminhadas_atualizacao_cadunico") else 0),
                        "pro_pao": getattr(m_report, "pro_pao", m_report.pro_pao if hasattr(m_report, "pro_pao") else 0),
                        "cesta": getattr(m_report, "cesta", m_report.cesta_basica if hasattr(m_report, "cesta_basica") else 0)
                    }
                    
                    vars = {}
                    if p_report:
                        vars["inclusao"] = get_var(metrics["inclusao"], p_report.encaminhadas_inclusao_cadunico)
                        vars["atualizacao"] = get_var(metrics["atualizacao"], p_report.encaminhadas_atualizacao_cadunico)
                        vars["pro_pao"] = get_var(metrics["pro_pao"], p_report.pro_pao)
                        vars["cesta"] = get_var(metrics["cesta"], p_report.cesta_basica)
                    
                    context["latest_metrics"] = metrics
                    context["variations"] = vars

                # Insights
                visitas = [
                    ("CadÚnico", getattr(m_report, "v_cadunico", m_report.visitas_cadunico if hasattr(m_report, "visitas_cadunico") else 0)),
                    ("Habitação", getattr(m_report, "v_nucleo", m_report.visita_nucleo_habitacao if hasattr(m_report, "visita_nucleo_habitacao") else 0)),
                    ("Cesta/Fralda", getattr(m_report, "v_cesta", m_report.visita_cesta_fraldas_colchoes if hasattr(m_report, "visita_cesta_fraldas_colchoes") else 0)),
                    ("DMAE", getattr(m_report, "v_dmae", m_report.visita_dmae if hasattr(m_report, "visita_dmae") else 0)),
                    ("Pró-Pão", getattr(m_report, "v_propao", m_report.visitas_pro_pao if hasattr(m_report, "visitas_pro_pao") else 0))
                ]
                visitas.sort(key=lambda x: x[1], reverse=True)
                context["top_visita"] = visitas[0] if visitas[0][1] > 0 else None
                context["visitas_sorted"] = visitas
                
                # Growth Insight
                if context.get("variations"):
                    max_growth = max(context["variations"].items(), key=lambda x: x[1])
                    if max_growth[1] > 0:
                        context["growth_insight"] = f"Aumento expressivo em {max_growth[0].replace('_', ' ')} (+{max_growth[1]}%)"

            elif context["is_monitoramento"]:
                now = datetime.now()
                curr_year = int(year)
                if bimester != "all":
                    curr_bimester = int(bimester)
                else:
                    curr_bimester = current_bimester()
                b_start_month, b_end_month = bimester_months(curr_bimester)
                b_labels = BIMESTER_LABELS
                context["bimester_label"] = f"{curr_bimester}o Bimestre ({b_labels[curr_bimester-1]})"
                
                visits = directorate.visits.filter(
                    visit_date__year=curr_year,
                    visit_date__month__gte=b_start_month,
                    visit_date__month__lte=b_end_month
                )
                
                # Filter by status if needed, but for stats we need all in bimester
                all_visits = list(visits)
                
                stats = {
                    "totalOSCs": directorate.oscs.count(),
                    "totalVisits": len(all_visits),
                    "finalizedVisits": len([v for v in all_visits if v.status in ['completed', 'finalized']]),
                    "draftReports": len([v for v in all_visits if v.parecer_tecnico and v.parecer_tecnico.get('status') == 'draft']),
                    "finalizedReports": len([v for v in all_visits if v.parecer_tecnico and v.parecer_tecnico.get('status') == 'finalized']),
                    "finalizedFinalReports": len([v for v in all_visits if v.relatorio_final and v.relatorio_final.get('status') == 'finalized']),
                    "finalizedConclusiveOpinions": len([v for v in all_visits if v.parecer_conclusivo and v.parecer_conclusivo.get('status') == 'finalized'])
                }
                context["subvencao_stats"] = stats
                context["all_visits_data"] = all_visits
                
                # For charts
                context["stats_json"] = stats # To be used in JS
                
                # Mode flags
                context["is_outros_mode"] = context["is_outros"]
                context["is_subvencao_mode"] = context["is_subvencao"]

        except (OperationalError, ProgrammingError):
            context["recent_visits"] = []
            context["recent_plans"] = []
            context["recent_oscs"] = []
            context["beneficios_reports"] = []
            
        return context


class OscListView(DirectorateScopedMixin, ListView):
    template_name = "directorates/monitoring/osc_list.html"
    model = Osc
    context_object_name = "oscs"

    def get_queryset(self):
        # Acesso à diretoria em si já é checado em dispatch() (DirectorateAccessMixin) —
        # quem chega até aqui tem vínculo com esta diretoria. Dentro dela, as OSCs
        # permanecem visíveis para todos os papéis (inclusive agente), pois precisam
        # navegar por todas as OSCs da diretoria para criar visitas/planos.
        return Osc.objects.filter(directorate_id=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.get_directorate()
        context["directorate"] = directorate
        types = (
            Osc.objects.filter(directorate_id=self.kwargs["pk"])
            .exclude(activity_type="")
            .values_list("activity_type", flat=True)
            .distinct()
            .order_by("activity_type")
        )
        context["activity_types"] = list(types)
        profile = getattr(self.request.user, 'profile', None)
        context["can_delete"] = self.request.user.is_superuser or (profile and profile.role == 'admin')
        context["theme_class"] = get_monitoramento_theme(directorate)[0]
        return context

class VisitListView(DirectorateScopedMixin, ListView):
    template_name = "directorates/monitoring/visit_list.html"
    model = Visit
    context_object_name = "visits"
    paginate_by = 50

    def get_queryset(self):
        qs = Visit.objects.filter(directorate_id=self.kwargs["pk"]).select_related("osc", "directorate", "work_plan")
        profile = getattr(self.request.user, 'profile', None)
        
        # --- PERMISSION FILTERING ---
        if not (self.request.user.is_superuser or (profile and profile.role == 'admin')):
            if profile and profile.role == 'diretor':
                # Diretor sees all in their primary or linked directorates,
                # exceto visitas feitas por admin (nao sao "dos seus agentes")
                is_primary = str(profile.primary_directorate_id) == str(self.kwargs["pk"])
                is_linked = ProfileDirectorate.objects.filter(profile=profile, directorate_id=self.kwargs["pk"]).exists()
                if not (is_primary or is_linked):
                    qs = qs.none()
                else:
                    qs = qs.exclude(user_id__in=get_admin_user_ids())
            else:
                # Agente sees only owned or delegated
                delegated_visit_ids = FormDelegation.objects.filter(user_id=self.request.user.id).values_list('visit_id', flat=True)
                qs = qs.filter(Q(user_id=self.request.user.id) | Q(id__in=delegated_visit_ids))
        # ----------------------------

        bimester = get_persistent_bimester(self.request)
        year = self.request.GET.get("year", datetime.now().year)
        start_date = self.request.GET.get("start_date", "")
        end_date = self.request.GET.get("end_date", "")

        if start_date and end_date:
            qs = qs.filter(visit_date__gte=start_date, visit_date__lte=end_date)
        elif bimester != "all":
            start, end = bimester_months(int(bimester))
            qs = qs.filter(
                visit_date__year=year,
                visit_date__month__gte=start,
                visit_date__month__lte=end,
            )
        if not start_date:
            qs = qs.filter(visit_date__year=year)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.get_directorate()
        context["directorate"] = directorate
        context["theme_class"] = get_monitoramento_theme(directorate)[0]
        context["show_reports_nav"] = is_subvencao_directorate(directorate)
        context["is_emendas"] = is_emendas_directorate(directorate)
        registered_by_map = build_registered_by_map(context["visits"])
        for visit in context["visits"]:
            identificacao = visit.identificacao or {}
            visit.registered_by_name = (
                identificacao.get("registered_by_name")
                or identificacao.get("registrado_por")
                or registered_by_map.get(visit.user_id)
                or "Desconhecido"
            )
            assinaturas = visit.assinaturas or {}
            visit.tecnico1_display = title_name(assinaturas.get("tecnico1_nome", ""))
            visit.tecnico2_display = title_name(assinaturas.get("tecnico2_nome", ""))
            visit.is_subvencao = is_subvencao_directorate(visit.directorate)
            relatorio = visit.parecer_tecnico or {}
            visit.relatorio_status = relatorio.get("status") if isinstance(relatorio, dict) else None
        context["profiles"] = Profile.objects.all().order_by("full_name")
        context["all_directorates"] = Directorate.objects.all().order_by("name")
        context["years_range"] = range(2023, datetime.now().year + 1)
        context["selected_year"] = int(self.request.GET.get("year", datetime.now().year))
        context["selected_bimester"] = get_persistent_bimester(self.request)
        context["bimester_options"] = BIMESTER_OPTIONS
        profile = getattr(self.request.user, 'profile', None)
        is_admin_user = self.request.user.is_superuser or (profile and profile.role == 'admin')
        context["can_delete"] = is_admin_user
        context["is_admin_user"] = is_admin_user
        return context

class VisitDelegateView(VisitScopedMixin, View):
    """So admin pode delegar visitas (restrito 2026-08-16 - antes diretor
    tambem podia, mas o usuario pediu que delegar/reverter fiquem exclusivos
    de admin)."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        profile = getattr(request.user, "profile", None)
        is_allowed = request.user.is_superuser or (profile and profile.role == "admin")
        if not is_allowed:
            return HttpResponseForbidden("Apenas administradores podem delegar visitas.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        visit = self.get_scoped_object()
        user_ids = request.POST.getlist("user_ids")

        # Clear existing
        FormDelegation.objects.filter(visit=visit).delete()

        # Add Users
        for uid in user_ids:
            FormDelegation.objects.create(
                id=uuid.uuid4(),
                visit=visit,
                user_id=uid,
                delegated_by=request.user.id
            )

        return redirect(get_visit_list_redirect(visit.directorate))

class WorkPlanListView(DirectorateScopedMixin, ListView):
    template_name = "directorates/monitoring/plan_list.html"
    model = WorkPlan
    context_object_name = "oscs"

    def get_queryset(self):
        queryset = Osc.objects.filter(directorate_id=self.kwargs["pk"]).prefetch_related("work_plans")
        profile = getattr(self.request.user, 'profile', None)
        
        # Admin
        if self.request.user.is_superuser or (profile and profile.role == 'admin'):
            pass # No filtering
        elif profile and profile.role == 'diretor':
            is_primary = str(profile.primary_directorate_id) == str(self.kwargs["pk"])
            is_linked = ProfileDirectorate.objects.filter(profile=profile, directorate_id=self.kwargs["pk"]).exists()
            if not (is_primary or is_linked):
                queryset = queryset.none()
        else:
            # Agente - filter plans they created.
            # Since WorkPlans are linked to OSCs, and an OSC might have multiple plans, 
            # we should probably filter the prefetch or the OSC list.
            # Let's filter OSCs that have at least one plan by the user.
            queryset = queryset.filter(work_plans__user_id=self.request.user.id).distinct()

        osc_id = self.request.GET.get("osc")
        if osc_id:
            queryset = queryset.filter(pk=osc_id)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.get_directorate()
        context["directorate"] = directorate
        context["is_emendas"] = is_emendas_directorate(directorate)
        context["selected_osc_id"] = self.request.GET.get("osc", "")
        profile = getattr(self.request.user, 'profile', None)
        context["can_delete"] = self.request.user.is_superuser or (profile and profile.role == 'admin')
        context["theme_class"] = get_monitoramento_theme(directorate)[0]
        return context

class WorkPlanObjectivesView(WorkPlanScopedMixin, View):
    """Salva os textos do plano herdados pelo relatório de visita
    (Emendas e Fundos): objeto, objetivos, metas e atividades."""

    def post(self, request, pk):
        plan = self.get_scoped_object()
        plan.objeto = (request.POST.get("objeto") or "").strip()
        plan.objetivos = (request.POST.get("objetivos") or "").strip()
        plan.metas = (request.POST.get("metas") or "").strip()
        plan.atividades = (request.POST.get("atividades") or "").strip()
        plan.save()
        messages.success(request, f"Objeto e objetivos do plano \"{plan.title}\" salvos com sucesso.")
        log_activity(request, plan.directorate, "updated", "work_plan", f"Plano de Trabalho — {plan.title}",
                     url=reverse("directorates:plan-update", kwargs={"pk": plan.pk}))
        next_url = get_safe_next_url(request)
        if next_url:
            return redirect(next_url)
        return redirect(reverse("directorates:plan-list", kwargs={"pk": plan.directorate.pk}))

class WorkPlanUpdateView(WorkPlanScopedMixin, UpdateView):
    model = WorkPlan
    template_name = "directorates/monitoring/plan_form.html"
    fields = ["title", "content", "status"]

    def dispatch(self, request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        is_admin = request.user.is_superuser or (profile and profile.role == 'admin')
        if not is_admin:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.get_scoped_object()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["directorate"] = self.object.directorate
        context["selected_osc_id"] = str(self.object.osc_id)
        context["return_url"] = get_safe_next_url(self.request) or reverse("directorates:plan-list", kwargs={"pk": self.object.directorate.pk})
        context["theme_class"] = get_monitoramento_theme(self.object.directorate)[0]
        context["plan_content_json"] = self.object.content or []
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request, self.object.directorate, "updated", "work_plan",
                     f"Plano de Trabalho — {self.object.title}",
                     url=reverse("directorates:plan-update", kwargs={"pk": self.object.pk}))
        return response

    def get_success_url(self):
        next_url = get_safe_next_url(self.request)
        if next_url:
            return next_url
        return reverse("directorates:plan-list", kwargs={"pk": self.object.directorate.pk})

class WorkPlanCreateView(DirectorateScopedMixin, CreateView):
    model = WorkPlan
    template_name = "directorates/monitoring/plan_form.html"
    fields = ["title", "content", "status", "osc"]

    def dispatch(self, request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        is_admin = request.user.is_superuser or (profile and profile.role == 'admin')
        if not is_admin:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.get_directorate()
        context["directorate"] = directorate
        context["selected_osc_id"] = self.request.GET.get("osc", "")
        context["return_url"] = get_safe_next_url(self.request) or reverse("directorates:plan-list", kwargs={"pk": self.kwargs["pk"]})
        context["theme_class"] = get_monitoramento_theme(directorate)[0]
        context["plan_content_json"] = []
        return context

    def form_valid(self, form):
        form.instance.directorate_id = self.kwargs["pk"]
        form.instance.user_id = self.request.user.pk
        response = super().form_valid(form)
        log_activity(self.request, self.object.directorate, "created", "work_plan",
                     f"Plano de Trabalho — {self.object.title}",
                     url=reverse("directorates:plan-update", kwargs={"pk": self.object.pk}))
        return response

    def get_success_url(self):
        next_url = get_safe_next_url(self.request)
        if next_url:
            return next_url
        return reverse("directorates:plan-list", kwargs={"pk": self.kwargs["pk"]})

class WorkPlanDeleteView(WorkPlanScopedMixin, DeleteView):
    model = WorkPlan
    template_name = "directorates/monitoring/confirm_delete.html"

    def dispatch(self, request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        is_admin = request.user.is_superuser or (profile and profile.role == 'admin')
        if not is_admin:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.get_scoped_object()

    def get_success_url(self):
        next_url = get_safe_next_url(self.request)
        if next_url:
            return next_url
        return reverse("directorates:plan-list", kwargs={"pk": self.object.directorate.pk})


class WorkPlanPreviewView(DirectorateScopedMixin, View):
    def get(self, request, pk):
        osc_id = request.GET.get("osc")
        plan = get_work_plan_by_id(pk, request.GET.get("plan"))
        if not plan:
            if not osc_id:
                return JsonResponse({"success": False, "error": "Selecione uma OSC para visualizar o plano."}, status=400)
            plan = get_latest_work_plan_for_osc(pk, osc_id)
        if not plan:
            return JsonResponse({"success": False, "error": "Nenhum plano de trabalho encontrado para esta OSC."}, status=404)

        context = build_work_plan_document_context(plan)
        html = render_to_string("directorates/monitoring/partials/work_plan_preview.html", context, request=request)
        open_url = reverse("directorates:plan-document", kwargs={"pk": plan.directorate.pk}) + f"?osc={plan.osc.pk}&plan={plan.pk}"
        return JsonResponse(
            {
                "success": True,
                "title": context["document_title"],
                "html": html,
                "open_url": open_url,
            }
        )


class WorkPlanDocumentView(DirectorateScopedMixin, TemplateView):
    template_name = "directorates/monitoring/work_plan_document.html"

    def get(self, request, *args, **kwargs):
        osc_id = request.GET.get("osc")
        plan = get_work_plan_by_id(self.kwargs["pk"], request.GET.get("plan"))
        if not plan:
            if not osc_id:
                messages.error(request, "Selecione uma OSC para visualizar o plano de trabalho.")
                return redirect("directorates:plan-list", pk=self.kwargs["pk"])
            plan = get_latest_work_plan_for_osc(self.kwargs["pk"], osc_id)
        if not plan:
            messages.error(request, "Nenhum plano de trabalho encontrado para esta OSC.")
            return redirect("directorates:plan-list", pk=self.kwargs["pk"])

        context = self.get_context_data(**kwargs)
        context.update(build_work_plan_document_context(plan))
        context["theme_class"] = get_monitoramento_theme(self.get_directorate())[0]

        if request.GET.get("export") == "pdf":
            from apps.directorates.pdf_documents import render_work_plan_document_pdf
            return render_work_plan_document_pdf(context)

        return render(request, self.template_name, context)

class MonitoringReportListView(DirectorateScopedMixin, ListView):
    template_name = "directorates/monitoring/report_list.html"
    model = Visit
    context_object_name = "visits"

    def get_queryset(self):
        qs = Visit.objects.filter(directorate_id=self.kwargs["pk"]).order_by("-visit_date")
        profile = getattr(self.request.user, 'profile', None)
        
        if not (self.request.user.is_superuser or (profile and profile.role == 'admin')):
            if profile and profile.role == 'diretor':
                is_primary = str(profile.primary_directorate_id) == str(self.kwargs["pk"])
                is_linked = ProfileDirectorate.objects.filter(profile=profile, directorate_id=self.kwargs["pk"]).exists()
                if not (is_primary or is_linked):
                    qs = qs.none()
                else:
                    qs = qs.exclude(user_id__in=get_admin_user_ids())
            else:
                delegated_visit_ids = FormDelegation.objects.filter(user_id=self.request.user.id).values_list('visit_id', flat=True)
                qs = qs.filter(Q(user_id=self.request.user.id) | Q(id__in=delegated_visit_ids))

        # Bimester filter persistence
        bimester = get_persistent_bimester(self.request)
        year = self.request.GET.get("year", datetime.now().year)
        if bimester != "all":
            start, end = bimester_months(int(bimester))
            qs = qs.filter(
                visit_date__year=year,
                visit_date__month__gte=start,
                visit_date__month__lte=end
            )
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.get_directorate()
        context["directorate"] = directorate
        context["selected_bimester"] = get_persistent_bimester(self.request)
        context["theme_class"] = get_monitoramento_theme(directorate)[0]
        profile = getattr(self.request.user, 'profile', None)
        context["is_admin_user"] = self.request.user.is_superuser or (profile and profile.role == 'admin')
        context["profiles"] = Profile.objects.all().order_by("full_name")
        return context

class VisitReportView(VisitAccessMixin, DetailView):
    """Generic view to handle the 3 types of specialized reports."""
    model = Visit
    template_name = "directorates/monitoring/report_form.html"
    context_object_name = "visit"

    def get_object(self, queryset=None):
        return self.get_scoped_object()

    REPORT_LABELS = {
        "parecer_tecnico": "Relatório de Visita",
        "parecer_conclusivo": "Parecer Conclusivo",
        "relatorio_final": "Relatório Final",
    }

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data()
        if request.GET.get("export") == "pdf":
            from apps.directorates.pdf_documents import render_visit_report_pdf
            return render_visit_report_pdf(context)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report_type = self.kwargs.get("report_type", "parecer_tecnico")
        context["report_type"] = report_type
        context["report_label"] = self.REPORT_LABELS.get(report_type, report_type.replace("_", " ").title())
        context["theme_class"] = get_monitoramento_theme(self.object.directorate)[0]
        context["can_edit"] = self.can_edit
        
        MONTH_NAMES = {
            1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril",
            5: "maio", 6: "junho", 7: "julho", 8: "agosto",
            9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro"
        }
        from datetime import datetime
        now = datetime.now()
        local_date_default = f"Uberlândia, {now.strftime('%d')} de {MONTH_NAMES.get(now.month)} de {now.year}"
        
        report_data = getattr(self.object, report_type) or {}
        report_texts = get_visit_report_texts(self.object)

        directorate = self.object.directorate
        dir_name_lower = (directorate.name or "").lower()
        import unicodedata
        normalized_dir_name = "".join(c for c in unicodedata.normalize('NFD', dir_name_lower) if unicodedata.category(c) != 'Mn')
        is_emendas = "emenda" in normalized_dir_name or "fundo" in normalized_dir_name
        is_subvencao = "subvencao" in normalized_dir_name

        if report_type == "relatorio_final":
            if not report_data:
                report_data = {
                    "osc_name": self.object.osc.name,
                    "cnpj": "",
                    "termo_fomento": "",
                    "vigencia": "",
                    "valor_autorizado": "",
                    "objeto_relatorio": report_texts["objeto"],
                    "referencias": "",
                    "anotacoes": "",
                    "objetivos": report_texts["objetivos"],
                    "metas": report_texts["metas"],
                    "atividades": report_texts["atividades"],
                    "resultados": "",
                    "execucao_financeira": "",
                    "cumprimento_objeto_final": "",
                    "texto_homologacao": "A Comissão de Monitoramento e Avaliação homologa o presente relatório.",
                    "local_data": local_date_default,
                    "homologacao_local_data": local_date_default,
                    "signature_tecnico": None,
                    "tecnico_nome": "",
                    "signature_financeiro": None,
                    "financeiro_nome": "",
                    "signature_comissao_tecnico": None,
                    "comissao_tecnico_nome": "",
                    "signature_comissao_financeiro": None,
                    "comissao_financeiro_nome": "",
                    "status": "draft",
                }
                if is_subvencao:
                    report_data["conclusao"] = ""
                else:
                    report_data["emenda"] = ""
            else:
                if not report_data.get("osc_name"):
                    report_data["osc_name"] = self.object.osc.name

        elif report_type == "parecer_conclusivo":
            if not report_data:
                rf = self.object.relatorio_final or {}
                report_data = {
                    "osc_name": rf.get("osc_name") or self.object.osc.name,
                    "cnpj": rf.get("cnpj") or "00.000.000/0000-00",
                    "termo_fomento": rf.get("termo_fomento") or "Ex: 629/2024",
                    "vigencia": rf.get("vigencia") or "Ex: 04/12/2024 a 30/06/2025",
                    "valor_autorizado": rf.get("valor_autorizado") or "R$ 0,00",
                    "fundamentacao": "",
                    "cumprimento_objeto": "",
                    "beneficios_impactos": "",
                    "conclusao": "",
                    "local_data": local_date_default,
                    "signature_tecnico": None,
                    "tecnico_nome": "",
                    "signature_financeiro": None,
                    "financeiro_nome": "",
                    "status": "draft",
                }
                if is_subvencao:
                    report_data["conclusao_final"] = ""
                else:
                    report_data["emenda"] = rf.get("emenda") or "Ex: 1430/2023"
            else:
                if not report_data.get("osc_name"):
                    report_data["osc_name"] = self.object.osc.name

        elif report_type == "parecer_tecnico":
            osc = self.object.osc
            osc_objeto = report_texts["objeto"]
            osc_objetivos = report_texts["objetivos"]
            osc_metas = report_texts["metas"]
            osc_atividades = report_texts["atividades"]
            
            # Dynamically pull defaults from self.object.atendimento if present
            # Dynamically pull defaults from self.object.atendimento or parecer_tecnico if present
            atendimento = self.object.atendimento or {}
            atendimento = sync_atendimento_pse_fields(atendimento)
            parecer_tecnico = self.object.parecer_tecnico or {}
            pse_data = {}
            if isinstance(atendimento, dict):
                pse_data = atendimento.get("pse_data") or {}
                if not isinstance(pse_data, dict):
                    pse_data = {}
            
            # Helpers to robustly detect non-empty qualitative or quantitative records
            def get_non_empty_qual_list(*lists):
                for lst in lists:
                    if isinstance(lst, list) and len(lst) > 0:
                        for row in lst:
                            if isinstance(row, dict) and any(str(val).strip() for val in row.values()):
                                return lst
                return None

            def get_non_empty_quant_dict(*dicts):
                for d in dicts:
                    if isinstance(d, dict) and len(d) > 0:
                        for row_val in d.values():
                            if isinstance(row_val, dict):
                                if any(str(val).strip() for val in row_val.values()):
                                    return d
                            elif str(row_val).strip():
                                return d
                return None

            # Prioritize source of truth based on the report type
            if report_type == "relatorio_final":
                default_item5_enabled = (
                    report_data.get("item5_enabled") or 
                    parecer_tecnico.get("item5_enabled") or 
                    pse_data.get("item5_enabled") or 
                    atendimento.get("item5_enabled") or 
                    False
                )
                default_item5_periodo = (
                    report_data.get("item5_periodo") or 
                    parecer_tecnico.get("item5_periodo") or 
                    pse_data.get("item5_periodo") or 
                    atendimento.get("item5_periodo") or 
                    "Janeiro a março de 2026"
                )
                default_item5_qual = (
                    get_non_empty_qual_list(
                        report_data.get("item5_qualitativos"),
                        parecer_tecnico.get("item5_qualitativos"),
                        pse_data.get("item5_qualitativos"),
                        atendimento.get("item5_qualitativos")
                    ) or [
                        { "data": "", "situacao": "", "recomendacoes": "", "observacao": "" },
                        { "data": "", "situacao": "", "recomendacoes": "", "observacao": "" },
                        { "data": "", "situacao": "", "recomendacoes": "", "observacao": "" },
                        { "data": "", "situacao": "", "recomendacoes": "", "observacao": "" },
                    ]
                )
                loaded_quant = (
                    get_non_empty_quant_dict(
                        report_data.get("item5_quantitativos"),
                        parecer_tecnico.get("item5_quantitativos"),
                        pse_data.get("item5_quantitativos"),
                        atendimento.get("item5_quantitativos")
                    ) or {}
                )
            else:  # report_type == "parecer_tecnico" or others
                default_item5_enabled = (
                    report_data.get("item5_enabled") or 
                    pse_data.get("item5_enabled") or 
                    atendimento.get("item5_enabled") or 
                    False
                )
                default_item5_periodo = (
                    report_data.get("item5_periodo") or 
                    pse_data.get("item5_periodo") or 
                    atendimento.get("item5_periodo") or 
                    "Janeiro a março de 2026"
                )
                default_item5_qual = (
                    get_non_empty_qual_list(
                        report_data.get("item5_qualitativos"),
                        pse_data.get("item5_qualitativos"),
                        atendimento.get("item5_qualitativos")
                    ) or [
                        { "data": "", "situacao": "", "recomendacoes": "", "observacao": "" },
                        { "data": "", "situacao": "", "recomendacoes": "", "observacao": "" },
                        { "data": "", "situacao": "", "recomendacoes": "", "observacao": "" },
                        { "data": "", "situacao": "", "recomendacoes": "", "observacao": "" },
                    ]
                )
                loaded_quant = (
                    get_non_empty_quant_dict(
                        pse_data.get("item5_quantitativos"),
                        atendimento.get("item5_quantitativos")
                    ) or {}
                )
            
            default_item5_quant_structure = {
                "total_1dia": { "jan": "", "fev": "", "mar": "", "abr": "", "mai": "", "jun": "", "jul": "", "ago": "", "set": "", "out": "", "nov": "", "dez": "" },
                "inseridos": { "jan": "", "fev": "", "mar": "", "abr": "", "mai": "", "jun": "", "jul": "", "ago": "", "set": "", "out": "", "nov": "", "dez": "" },
                "desligados": { "jan": "", "fev": "", "mar": "", "abr": "", "mai": "", "jun": "", "jul": "", "ago": "", "set": "", "out": "", "nov": "", "dez": "" },
                "total_ultimo": { "jan": "", "fev": "", "mar": "", "abr": "", "mai": "", "jun": "", "jul": "", "ago": "", "set": "", "out": "", "nov": "", "dez": "" },
            }
            
            default_item5_quant = {}
            for row_key, month_dict in default_item5_quant_structure.items():
                default_item5_quant[row_key] = {}
                loaded_row = loaded_quant.get(row_key) if isinstance(loaded_quant, dict) else {}
                for m_key, default_val in month_dict.items():
                    default_item5_quant[row_key][m_key] = loaded_row.get(m_key, default_val) if isinstance(loaded_row, dict) else default_val
            
            # Query the previous visit of the same OSC to set completion date
            previous_visit = Visit.objects.filter(
                osc=self.object.osc,
                visit_date__lt=self.object.visit_date
            ).order_by('-visit_date').first()
            
            if previous_visit:
                visit_date_str = previous_visit.visit_date.strftime("%d/%m/%Y")
            else:
                visit_date_str = self.object.visit_date.strftime("%d/%m/%Y") if self.object.visit_date else datetime.now().strftime("%d/%m/%Y")

            default_report = {
                "objeto_relatorio": osc_objeto,
                "item2_a_objetivos": osc_objetivos,
                "item2_b_metas": osc_metas,
                "item2_b_metas_quant": "",
                "item2_c_atividades": osc_atividades,
                "item3_resultados": "",
                "item4_type": "fully",
                "item4_custom": "",
                "item5_enabled": default_item5_enabled,
                "item5_periodo": default_item5_periodo,
                "item5_qualitativos": default_item5_qual,
                "item5_quantitativos": default_item5_quant,
                "assinaturas": {
                    "tecnico1": "",
                    "tecnico1_nome": "",
                    "tecnico2": "",
                    "tecnico2_nome": ""
                },
                "status": "draft",
                "term_type": "colaboracao",
                "date": visit_date_str
            }
            
            # Deep merge default_report and report_data
            for key, val in default_report.items():
                if key not in report_data:
                    report_data[key] = val
                elif isinstance(val, dict) and isinstance(report_data[key], dict):
                    for subkey, subval in val.items():
                        if subkey not in report_data[key]:
                            report_data[key][subkey] = subval
                        elif isinstance(subval, dict) and isinstance(report_data[key][subkey], dict):
                            for subsubkey, subsubval in subval.items():
                                if subsubkey not in report_data[key][subkey]:
                                    report_data[key][subkey][subsubkey] = subsubval
            
            # If report_type is relatorio_final, and qualitative or quantitative data is completely empty/blank,
            # we sync/copy it from parecer_tecnico so the user has continuity.
            if report_type == "relatorio_final":
                parecer_tecnico = self.object.parecer_tecnico or {}
                
                # Check if item5_qualitativos is completely blank/empty
                is_empty_qual = True
                qual_list = report_data.get("item5_qualitativos")
                if isinstance(qual_list, list) and len(qual_list) > 0:
                    for row in qual_list:
                        if isinstance(row, dict) and any(str(val).strip() for val in row.values()):
                            is_empty_qual = False
                            break
                if is_empty_qual:
                    pt_qual = parecer_tecnico.get("item5_qualitativos")
                    if isinstance(pt_qual, list) and len(pt_qual) > 0:
                        # Check if pt_qual itself has actual data
                        has_pt_qual_data = False
                        for row in pt_qual:
                            if isinstance(row, dict) and any(str(val).strip() for val in row.values()):
                                has_pt_qual_data = True
                                break
                        if has_pt_qual_data:
                            report_data["item5_qualitativos"] = pt_qual
                
                # Check if item5_quantitativos is completely blank/empty
                is_empty_quant = True
                quant_dict = report_data.get("item5_quantitativos")
                if isinstance(quant_dict, dict) and len(quant_dict) > 0:
                    for row_key, month_dict in quant_dict.items():
                        if isinstance(month_dict, dict) and any(str(val).strip() for val in month_dict.values()):
                            is_empty_quant = False
                            break
                if is_empty_quant:
                    pt_quant = parecer_tecnico.get("item5_quantitativos")
                    if isinstance(pt_quant, dict) and len(pt_quant) > 0:
                        # Check if pt_quant has actual data
                        has_pt_quant_data = False
                        for row_key, month_dict in pt_quant.items():
                            if isinstance(month_dict, dict) and any(str(val).strip() for val in month_dict.values()):
                                has_pt_quant_data = True
                                break
                        if has_pt_quant_data:
                            report_data["item5_quantitativos"] = pt_quant

            # Ensure item5_qualitativos e uma lista com pelo menos 1 linha para
            # editar -- a tabela aceita adicionar/excluir linhas em tempo real
            # (ver addQualRow/removeQualRow em report_form.html), entao nao ha
            # mais um numero fixo de linhas.
            if "item5_qualitativos" not in report_data or not isinstance(report_data["item5_qualitativos"], list):
                report_data["item5_qualitativos"] = []

            while len(report_data["item5_qualitativos"]) < 1:
                report_data["item5_qualitativos"].append({ "data": "", "situacao": "", "recomendacoes": "", "observacao": "" })

            for idx in range(len(report_data["item5_qualitativos"])):
                if not isinstance(report_data["item5_qualitativos"][idx], dict):
                    report_data["item5_qualitativos"][idx] = {}
                row = report_data["item5_qualitativos"][idx]
                for key in ["data", "situacao", "recomendacoes", "observacao"]:
                    if key not in row:
                        row[key] = ""
            
            # Force automatically the previous visit's date for prefilling
            report_data["date"] = visit_date_str

        context["is_emendas"] = is_emendas
        context["is_subvencao"] = is_subvencao
        context["report_data"] = report_data
        context["directorate"] = directorate
        # Relatorio Final e Parecer Conclusivo voltam pra aba "Relatorios e
        # Pareceres" (de onde normalmente se abre esses dois), nao pra aba
        # "Instrumental de Visita" que e o fallback genérico de
        # get_visit_list_redirect() -- só pra Subvenção/Emendas e Fundos, que
        # são as únicas diretorias com essa aba (Outros não tem).
        if report_type in ("relatorio_final", "parecer_conclusivo") and is_subvencao_directorate(directorate):
            fallback_return_url = f"{reverse('monitoramento:home', kwargs={'pk': directorate.pk})}?tab=reports"
        else:
            fallback_return_url = get_visit_list_redirect(directorate)
        context["return_url"] = get_safe_next_url(self.request) or fallback_return_url
        return context

    def post(self, request, *args, **kwargs):
        visit = self.get_object()
        report_type = self.kwargs.get("report_type", "parecer_tecnico")
        
        try:
            data = json.loads(request.POST.get("data", "{}"))
            if isinstance(data, dict):
                # Nome do tecnico responsavel sempre em maiusculas nas assinaturas
                # (reforcado no servidor -- o JS ja faz .toUpperCase() antes de
                # enviar, mas isso normaliza tambem dados antigos re-salvos).
                for key in list(data.keys()):
                    if key.endswith("_nome") and isinstance(data[key], str):
                        data[key] = data[key].upper()
            setattr(visit, report_type, data)

            # Bidirectional sync back to visit.atendimento
            if isinstance(data, dict) and report_type == "parecer_tecnico":
                atendimento = visit.atendimento or {}
                if not isinstance(atendimento, dict):
                    atendimento = {}
                if "pse_data" not in atendimento or not isinstance(atendimento["pse_data"], dict):
                    atendimento["pse_data"] = {}
                pse_data = atendimento["pse_data"]
                if "item5_enabled" in data:
                    pse_data["item5_enabled"] = data["item5_enabled"]
                if "item5_periodo" in data:
                    pse_data["item5_periodo"] = data["item5_periodo"]
                if "item5_qualitativos" in data:
                    pse_data["item5_qualitativos"] = data["item5_qualitativos"]
                if "item5_quantitativos" in data:
                    pse_data["item5_quantitativos"] = data["item5_quantitativos"]
                
                # Normalize and synchronize with explicit priority on pse_data
                atendimento = sync_atendimento_pse_fields(atendimento, priority="pse_data")
                visit.atendimento = atendimento

                # Also sync back to the other report type so there is absolute sync across the 2 forms
                other_report_type = "relatorio_final" if report_type == "parecer_tecnico" else "parecer_tecnico"
                other_report = getattr(visit, other_report_type) or {}
                if isinstance(other_report, dict):
                    if "item5_enabled" in data:
                        other_report["item5_enabled"] = data["item5_enabled"]
                    if "item5_periodo" in data:
                        other_report["item5_periodo"] = data["item5_periodo"]
                    if "item5_qualitativos" in data:
                        other_report["item5_qualitativos"] = data["item5_qualitativos"]
                    if "item5_quantitativos" in data:
                        other_report["item5_quantitativos"] = data["item5_quantitativos"]
                    setattr(visit, other_report_type, other_report)
            
            visit.save()
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

class VisitUploadDocumentView(VisitAccessMixin, View):
    def post(self, request, pk):
        visit = self.get_scoped_object()
        file = request.FILES.get("file")
        if not file:
            return JsonResponse({"success": False, "error": "No file provided"}, status=400)

        # TODO: implementar persistência real do arquivo (usar upload_to_supabase ou FileSystemStorage)
        ext = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else ""
        safe_name = f"{uuid.uuid4().hex}.{ext}" if ext else f"{uuid.uuid4().hex}"
        path = f"visitas/documentos/{visit.pk}/{safe_name}"
        url = upload_to_supabase(file, path)
        logger.warning("VisitUploadDocumentView: arquivo %s salvo em %s", file.name, url)

        doc_data = {
            "name": file.name,
            "url": url,
            "uploaded_at": datetime.now().isoformat()
        }

        if not visit.documents:
            visit.documents = []
        visit.documents.append(doc_data)
        visit.save()

        return JsonResponse({"success": True, "document": doc_data})


class VisitUploadNotificationView(VisitAccessMixin, View):
    def post(self, request, pk):
        visit = self.get_scoped_object()
        file = request.FILES.get("file")
        if not file:
            return JsonResponse({"success": False, "error": "Arquivo não fornecido"}, status=400)
        
        if not file.name.lower().endswith(".pdf"):
            return JsonResponse({"success": False, "error": "Apenas arquivos PDF são permitidos"}, status=400)
        
        try:
            from django.core.files.storage import default_storage
            saved_path = default_storage.save(f"notifications/{file.name}", file)
            uploaded_file_url = reverse("core:protected-media", kwargs={"file_path": saved_path})

            notif_data = {
                "name": file.name,
                "url": uploaded_file_url,
                "uploaded_at": datetime.now().isoformat()
            }
            
            if not isinstance(visit.notificacoes, list):
                visit.notificacoes = []
            visit.notificacoes.append(notif_data)
            visit.save()
            
            return JsonResponse({"success": True, "notificacao": notif_data})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)


class VisitRemoveNotificationView(VisitAccessMixin, View):
    def post(self, request, pk):
        visit = self.get_scoped_object()
        try:
            import json
            data = json.loads(request.body.decode('utf-8'))
            index = data.get("index")
        except Exception:
            index = request.POST.get("index")
            
        if index is None:
            return JsonResponse({"success": False, "error": "Index não fornecido"}, status=400)
        
        try:
            index = int(index)
            if not isinstance(visit.notificacoes, list) or index < 0 or index >= len(visit.notificacoes):
                return JsonResponse({"success": False, "error": "Index inválido"}, status=400)
            
            visit.notificacoes.pop(index)
            visit.save()
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)



from .forms import OscForm, VisitForm

class OscCreateView(DirectorateScopedMixin, CreateView):
    model = Osc
    form_class = OscForm
    template_name = "directorates/monitoring/osc_form.html"

    def dispatch(self, request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        is_admin = request.user.is_superuser or (profile and profile.role == 'admin')
        if not is_admin:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = self.get_directorate()
        context["directorate"] = directorate
        context["return_url"] = get_safe_next_url(self.request) or get_osc_list_redirect(directorate)
        context["theme_class"] = get_monitoramento_theme(directorate)[0]
        return context

    def form_valid(self, form):
        form.instance.directorate_id = self.kwargs["pk"]
        form.instance.id = uuid.uuid4()
        response = super().form_valid(form)
        log_activity(self.request, self.object.directorate, "created", "osc", f"OSC {self.object.name}",
                     url=reverse("directorates:osc-update", kwargs={"pk": self.object.pk}))
        return response

    def get_success_url(self):
        next_url = self.request.POST.get("next") or self.request.GET.get("next")
        if next_url and next_url.startswith("/"):
            return next_url
        return get_osc_list_redirect(self.get_directorate())

class OscUpdateView(OscScopedMixin, UpdateView):
    model = Osc
    form_class = OscForm
    template_name = "directorates/monitoring/osc_form.html"

    def dispatch(self, request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        is_admin = request.user.is_superuser or (profile and profile.role == 'admin')
        if not is_admin:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.get_scoped_object()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["directorate"] = self.object.directorate
        context["return_url"] = get_safe_next_url(self.request) or get_osc_list_redirect(self.object.directorate)
        context["theme_class"] = get_monitoramento_theme(self.object.directorate)[0]
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request, self.object.directorate, "updated", "osc", f"OSC {self.object.name}",
                     url=reverse("directorates:osc-update", kwargs={"pk": self.object.pk}))
        return response

    def get_success_url(self):
        next_url = self.request.POST.get("next") or self.request.GET.get("next")
        if next_url and next_url.startswith("/"):
            return next_url
        return get_osc_list_redirect(self.object.directorate)

class OscDeleteView(OscScopedMixin, DeleteView):
    model = Osc

    def dispatch(self, request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        is_admin = request.user.is_superuser or (profile and profile.role == 'admin')
        if not is_admin:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.get_scoped_object()

    def get_success_url(self):
        next_url = self.request.POST.get("next") or self.request.GET.get("next")
        if next_url and next_url.startswith("/"):
            return next_url
        return get_osc_list_redirect(self.object.directorate)

class VisitCreateView(DirectorateScopedMixin, TemplateView):
    template_name = "directorates/monitoring/visit_instrumental.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        directorate = get_object_or_404(Directorate, pk=self.kwargs["pk"])
        context["directorate"] = directorate
        context["oscs"] = Osc.objects.filter(directorate=directorate).order_by("name")
        context["is_new"] = True
        context["object"] = None
        context["is_subvencao_visit"] = is_subvencao_directorate(directorate)
        context["is_emendas_visit"] = is_emendas_directorate(directorate)
        context["is_outros_visit"] = is_outros_directorate(directorate)
        context["osc_plans"] = build_osc_plans_map(directorate.pk) if context["is_subvencao_visit"] else {}
        context["osc_pse_map"] = (
            {str(osc.pk): osc.pse_quantitativos for osc in context["oscs"] if osc.pse_quantitativos}
            if context["is_subvencao_visit"] else {}
        )
        context["return_url"] = get_safe_next_url(self.request) or get_visit_list_redirect(directorate)
        context["theme_class"] = get_monitoramento_theme(directorate)[0]
        return context

    def post(self, request, *args, **kwargs):
        directorate = get_object_or_404(Directorate, pk=self.kwargs["pk"])
        data = request.POST
        access_checkbox_fields = ("demanda_espontanea", "busca_ativa", "encaminhamento", "outros")

        osc_id = data.get("osc")
        if not osc_id:
            messages.error(request, "Selecione uma OSC.")
            next_url = get_safe_next_url(request)
            create_url = reverse("directorates:visit-create", kwargs={"pk": directorate.pk})
            return redirect(f"{create_url}?next={next_url}" if next_url else create_url)

        work_plan = None
        if is_subvencao_directorate(directorate):
            work_plan = resolve_visit_work_plan(directorate.pk, osc_id, data.get("work_plan"))

        visit = Visit(
            id=uuid.uuid4(),
            directorate=directorate,
            osc_id=osc_id,
            work_plan=work_plan,
            visit_date=data.get("identificacao[visit_date_1]", "") or datetime.now(),
            # visit_time nao tem campo proprio no formulario (so "Turno"
            # manha/tarde) - usa o horario real de criacao em vez de um
            # valor fixo, ja que o campo e NOT NULL no banco e nao pode
            # ficar vazio (achado 2026-08-17: toda visita criada mostrava
            # 09:00, sempre igual, porque era hardcoded aqui).
            visit_time=datetime.now().time(),
            status=data.get("status", "draft"),
            user_id=request.user.pk,
        )

        identificacao = {}
        for key, value in data.items():
            if key.startswith("identificacao[") and key.endswith("]"):
                identificacao[key[14:-1]] = value
        identificacao["registered_by_name"] = get_request_user_display_name(request)
        identificacao["registered_by_username"] = request.user.get_username()
        if identificacao:
            visit.identificacao = identificacao

        atendimento = {}
        for key, value in data.items():
            if key.startswith("atendimento[") and key.endswith("]"):
                set_nested_value(atendimento, read_bracket_parts(key, "atendimento"), value)
        if atendimento:
            visit.atendimento = normalize_visit_attendance(visit, atendimento)
            if is_subvencao_directorate(directorate):
                write_back_osc_pse_quantitativos(visit.osc, visit.atendimento)

        forma_acesso = {
            field: data.get(f"forma_acesso[{field}]") == "on"
            for field in access_checkbox_fields
        }
        forma_acesso["quem_encaminha"] = data.get("forma_acesso[quem_encaminha]", "").strip()
        if any(forma_acesso[field] for field in access_checkbox_fields) or forma_acesso["quem_encaminha"]:
            visit.forma_acesso = forma_acesso

        assinaturas = {}
        for key, value in data.items():
            if key.startswith("assinaturas[") and key.endswith("]"):
                inner_key = key[12:-1]
                if inner_key.endswith("_nome") and isinstance(value, str):
                    value = value.upper()
                assinaturas[inner_key] = value
        if assinaturas:
            visit.assinaturas = assinaturas

        if "rh_data" in data:
            try:
                visit.rh_data = json.loads(data["rh_data"])
            except json.JSONDecodeError:
                pass

        visit.observacoes = data.get("observacoes", "")
        visit.recomendacoes = data.get("recomendacoes", "")
        append_visit_uploaded_documents(visit, request.FILES)

        try:
            visit.save()
        except Exception:
            logger.exception("Falha ao salvar Visit (pk=%s)", getattr(visit, "pk", None))
            messages.error(request, "Nao foi possivel salvar a visita. Tente novamente.")
            next_url = get_safe_next_url(request)
            create_url = reverse("directorates:visit-create", kwargs={"pk": directorate.pk})
            return redirect(f"{create_url}?next={next_url}" if next_url else create_url)

        visit_url = reverse("directorates:visit-instrumental", kwargs={"pk": visit.pk})
        if visit.status == "finalized":
            messages.success(request, "Visita finalizada com sucesso.")
            log_activity(request, directorate, "finalized", "visit", f"Visita — {visit.osc.name}", url=visit_url)
            # Sempre volta para a lista de visitas (nao para o "next" generico de
            # voltar/cancelar da pagina) - e la que o botao "Relatorio de Visita"
            # aparece habilitado para o proximo passo.
            return redirect(get_visit_list_redirect(directorate))
        messages.success(request, "Rascunho salvo com sucesso.")
        log_activity(request, directorate, "created", "visit", f"Visita — {visit.osc.name}", url=visit_url)
        next_url = get_safe_next_url(request)
        if next_url:
            return redirect(next_url)
        return redirect(get_visit_list_redirect(directorate))

class VisitInstrumentalView(VisitAccessMixin, UpdateView):
    model = Visit
    template_name = "directorates/monitoring/visit_instrumental.html"
    fields = ["status", "observacoes", "recomendacoes"]

    def get_object(self, queryset=None):
        obj = self.get_scoped_object()
        if obj and obj.atendimento:
            obj.atendimento = sync_atendimento_pse_fields(obj.atendimento)
            if is_subvencao_directorate(obj.directorate):
                obj.atendimento = merge_osc_pse_quantitativos(obj.osc, obj.atendimento)
        return obj

    def get_template_names(self):
        if self.get_object().status in ['finalized', 'completed']:
            return ["directorates/monitoring/visit_document.html"]
        return ["directorates/monitoring/visit_instrumental.html"]

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.GET.get("export") == "pdf" and self.object.status in ("finalized", "completed"):
            from apps.directorates.pdf_documents import render_visit_document_pdf
            return render_visit_document_pdf(self.get_context_data())
        return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["directorate"] = self.object.directorate
        context["oscs"] = Osc.objects.filter(directorate_id=self.object.directorate.pk).order_by("name")
        context["is_new"] = False
        context["can_edit"] = self.can_edit
        context["theme_class"] = get_monitoramento_theme(self.object.directorate)[0]
        context["is_subvencao_visit"] = is_subvencao_directorate(self.object.directorate)
        context["is_emendas_visit"] = is_emendas_directorate(self.object.directorate)
        context["is_outros_visit"] = is_outros_directorate(self.object.directorate)
        if context["is_subvencao_visit"]:
            context["visit_osc_plans"] = WorkPlan.objects.filter(
                osc_id=self.object.osc_id, directorate_id=self.object.directorate.pk
            ).order_by("-updated_at", "title")
        context["return_url"] = get_safe_next_url(self.request) or get_visit_list_redirect(self.object.directorate)
        extra_visits = []
        identificacao = self.object.identificacao or {}
        i = 2
        while f"visit_date_{i}" in identificacao or f"visit_shift_{i}" in identificacao:
            extra_visits.append({
                "num": i,
                "date": identificacao.get(f"visit_date_{i}", ""),
                "shift": identificacao.get(f"visit_shift_{i}", ""),
            })
            i += 1
        context["extra_visits"] = extra_visits
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Manually extract nested data from POST
        data = request.POST
        access_checkbox_fields = ("demanda_espontanea", "busca_ativa", "encaminhamento", "outros")
        
        # Process Identificacao
        identificacao = self.object.identificacao or {}
        for key, value in data.items():
            if key.startswith("identificacao[") and key.endswith("]"):
                inner_key = key[14:-1]
                identificacao[inner_key] = value
        if not identificacao.get("registered_by_name"):
            identificacao["registered_by_name"] = get_request_user_display_name(request)
        if not identificacao.get("registered_by_username"):
            identificacao["registered_by_username"] = request.user.get_username()
        self.object.identificacao = identificacao

        # Process Atendimento
        atendimento = self.object.atendimento or {}
        for key, value in data.items():
            if key.startswith("atendimento[") and key.endswith("]"):
                set_nested_value(atendimento, read_bracket_parts(key, "atendimento"), value)
        
        # Synchronize and normalize PSE data with explicit priority on atendimento fields
        atendimento = sync_atendimento_pse_fields(atendimento, priority="atendimento")
        self.object.atendimento = normalize_visit_attendance(self.object, atendimento)
        if is_subvencao_directorate(self.object.directorate):
            write_back_osc_pse_quantitativos(self.object.osc, self.object.atendimento)

        # Also sync to report fields!
        pse_data = atendimento.get("pse_data") or {}
        for report_type in ["parecer_tecnico", "relatorio_final"]:
            report_data = getattr(self.object, report_type) or {}
            if isinstance(report_data, dict):
                if "item5_enabled" in pse_data:
                    report_data["item5_enabled"] = pse_data["item5_enabled"]
                if "item5_periodo" in pse_data:
                    report_data["item5_periodo"] = pse_data["item5_periodo"]
                if "item5_qualitativos" in pse_data:
                    report_data["item5_qualitativos"] = pse_data["item5_qualitativos"]
                if "item5_quantitativos" in pse_data:
                    report_data["item5_quantitativos"] = pse_data["item5_quantitativos"]
                setattr(self.object, report_type, report_data)

        self.object.forma_acesso = {
            **{
                field: data.get(f"forma_acesso[{field}]") == "on"
                for field in access_checkbox_fields
            },
            "quem_encaminha": data.get("forma_acesso[quem_encaminha]", "").strip(),
        }

        # Process Assinaturas
        assinaturas = self.object.assinaturas or {}
        for key, value in data.items():
            if key.startswith("assinaturas[") and key.endswith("]"):
                inner_key = key[12:-1]
                if inner_key.endswith("_nome") and isinstance(value, str):
                    value = value.upper()
                assinaturas[inner_key] = value
        self.object.assinaturas = assinaturas

        # RH Data is already JSON string from JS
        if "rh_data" in data:
            import json
            try:
                self.object.rh_data = json.loads(data["rh_data"])
            except:
                pass

        self.object.observacoes = data.get("observacoes", "")
        self.object.recomendacoes = data.get("recomendacoes", "")
        self.object.status = data.get("status") or "draft"
        if is_subvencao_directorate(self.object.directorate) and "work_plan" in data:
            self.object.work_plan = resolve_visit_work_plan(
                self.object.directorate.pk, self.object.osc_id, data.get("work_plan")
            )
        append_visit_uploaded_documents(self.object, request.FILES, request)

        try:
            self.object.save()
        except Exception:
            logger.exception("Falha ao salvar Visit (pk=%s)", getattr(self.object, "pk", None))
            messages.error(request, "Nao foi possivel salvar a visita. Tente novamente.")
            next_url = get_safe_next_url(request)
            edit_url = reverse("directorates:visit-instrumental", kwargs={"pk": self.object.pk})
            return redirect(f"{edit_url}?next={next_url}" if next_url else edit_url)

        visit_url = reverse("directorates:visit-instrumental", kwargs={"pk": self.object.pk})
        if self.object.status == "finalized":
            messages.success(request, "Visita finalizada com sucesso.")
            log_activity(request, self.object.directorate, "finalized", "visit",
                         f"Visita — {self.object.osc.name}", url=visit_url)
            # Sempre volta para a lista de visitas (nao para o "next" generico de
            # voltar/cancelar da pagina) - e la que o botao "Relatorio de Visita"
            # aparece habilitado para o proximo passo.
            return redirect(get_visit_list_redirect(self.object.directorate))
        messages.success(request, "Rascunho salvo com sucesso.")
        log_activity(request, self.object.directorate, "updated", "visit",
                     f"Visita — {self.object.osc.name}", url=visit_url)
        return redirect(self.get_success_url())

    def get_success_url(self):
        next_url = get_safe_next_url(self.request)
        if next_url:
            return next_url
        return get_visit_list_redirect(self.object.directorate)

class VisitDeleteDocumentView(VisitAccessMixin, View):
    def post(self, request, pk):
        import json
        import urllib.request
        from django.conf import settings
        visit = self.get_scoped_object()

        try:
            data = json.loads(request.body)
            index = int(data.get("index"))
            
            documents = list(visit.documents or [])
            if 0 <= index < len(documents):
                doc = documents[index]
                doc_url = doc.get('url', '')
                
                # Tentar deletar no Supabase se for um link de la
                if "storage/v1/object/public/" in doc_url:
                    try:
                        # Extrair o path do bucket 'system-assets'
                        path_parts = doc_url.split("system-assets/")
                        if len(path_parts) > 1:
                            storage_path = path_parts[1]
                            supabase_url = getattr(settings, "SUPABASE_URL", "")
                            anon_key = getattr(settings, "SUPABASE_ANON_KEY", "")
                            
                            delete_url = f"{supabase_url}/storage/v1/object/system-assets/{storage_path}"
                            headers = {
                                "apikey": anon_key,
                                "Authorization": f"Bearer {anon_key}",
                            }
                            req = urllib.request.Request(delete_url, headers=headers, method="DELETE")
                            with urllib.request.urlopen(req, timeout=5) as resp:
                                pass
                    except Exception as e:
                        logger.warning("Erro ao deletar no Supabase: %s", e)
                
                documents.pop(index)
                visit.documents = documents
                visit.save()
                return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
            
        return JsonResponse({"success": False, "error": "Index invalido"}, status=400)

class VisitRevertView(VisitScopedMixin, View):
    """Reverte o status (instrumental inteiro) para 'draft'. So admin
    (restrito 2026-08-16 - antes o dono, mesmo diretor/agente, tambem podia;
    usuario pediu exclusividade admin, mesma regra do RevertReportView)."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        profile = getattr(request.user, "profile", None)
        is_allowed = request.user.is_superuser or (profile and profile.role == "admin")
        if not is_allowed:
            return HttpResponseForbidden("Apenas administradores podem reverter visitas.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        visit = self.get_scoped_object()
        visit.status = "draft"
        visit.save()
        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        return redirect(get_visit_list_redirect(visit.directorate))

class RevertReportView(VisitScopedMixin, View):
    """Reverte o status de relatorio_final ou parecer_conclusivo para 'draft'.
    So admin (restrito 2026-08-16 - antes o dono, mesmo sendo diretor/agente,
    tambem podia reverter a propria visita; usuario pediu exclusividade admin)."""
    ALLOWED = ("relatorio_final", "parecer_conclusivo")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        profile = getattr(request.user, "profile", None)
        is_allowed = request.user.is_superuser or (profile and profile.role == "admin")
        if not is_allowed:
            return HttpResponseForbidden("Apenas administradores podem reverter relatórios.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk, report_type):
        if report_type not in self.ALLOWED:
            return JsonResponse({"success": False, "error": "Tipo inválido"}, status=400)
        visit = self.get_scoped_object()
        report_data = getattr(visit, report_type) or {}
        if not isinstance(report_data, dict):
            return JsonResponse({"success": False, "error": "Dados inválidos"}, status=400)
        report_data["status"] = "draft"
        setattr(visit, report_type, report_data)
        visit.save()
        return JsonResponse({"success": True})


class VisitDeleteView(VisitScopedMixin, DeleteView):
    model = Visit

    def dispatch(self, request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        is_admin = request.user.is_superuser or (profile and profile.role in ('admin', 'diretor'))
        if not is_admin:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.get_scoped_object()

    def get_success_url(self):
        next_url = self.request.POST.get("next") or self.request.GET.get("next")
        if next_url and next_url.startswith("/"):
            return next_url
        return get_visit_list_redirect(self.object.directorate)
