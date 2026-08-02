class TvTemplateMixin:
    tv_template_name = None

    def get_template_names(self):
        if self.request.GET.get("tv") == "1" and self.tv_template_name:
            return [self.tv_template_name]
        return super().get_template_names()


class NarrativeReportMixin:
    """Logica compartilhada da tela unica de Relatorio Mensal narrativo
    (visualizacao + historico completo do ano, ver templates/directorates/
    shared/narrative_report.html). Combinar com o *BaseMixin de cada app
    (fornece get_directorate()/is_agente()/is_admin()) e definir `setor` na
    subclasse concreta. A subclasse ainda precisa prover em get_context_data():
    back_url e report_label (nome da diretoria/modulo p/ titulo), alem de
    implementar get_editor_url(month, year).

    Regra de permissao (pedido do usuario): diretor/agente podem CRIAR um
    relatorio novo (periodo ainda sem nada salvo), mas depois de finalizado
    só um admin pode editar -- diretor/agente passam a só visualizar. Admin
    pode excluir (sidebar) pra liberar o periodo de novo.
    """
    setor = None

    def get_editor_url(self, month, year):
        raise NotImplementedError("Subclasse deve implementar get_editor_url(month, year)")

    def get_narrative_context(self, month, year, history_year=None):
        from datetime import date
        from apps.core.utils import extract_report_html
        from apps.directorates.models import MonthlyReport

        directorate = self.get_directorate()
        qs = MonthlyReport.objects.filter(directorate=directorate, setor=self.setor)
        if self.is_agente():
            qs = qs.filter(user_external_id=self.request.user.pk)

        report = qs.filter(year=year, month=month).first()
        history_year = history_year or year
        history = list(qs.filter(year=history_year).order_by("-month"))
        # set() em Python em vez de .distinct() no ORM: o Meta.ordering padrao
        # de MonthlyReport inclui -created_at, e Postgres exige colunas do
        # ORDER BY no SELECT quando ha DISTINCT -- isso faz o .distinct() no
        # values_list("year") nao deduplicar de verdade (linhas com o mesmo
        # ano mas created_at diferente contam como "distintas").
        available_years = sorted(
            set(qs.values_list("year", flat=True)), reverse=True
        )
        if not available_years:
            available_years = [year]

        is_admin = self.is_admin()
        for item in history:
            item.edit_url = self.get_editor_url(item.month, item.year)

        today = date.today()

        return {
            "directorate": directorate,
            "selected_month": month,
            "selected_year": year,
            "history_year": history_year,
            "available_years": available_years,
            "monthly_report": report,
            "report_content_html": extract_report_html(report.content) if report else "",
            "history": history,
            "is_admin": is_admin,
            # Diretor/agente só podem "editar" quando ainda não existe nada
            # salvo pra esse período (ou seja, estão criando, não reabrindo
            # um relatório já finalizado).
            "can_edit": is_admin or report is None,
            "editor_url": self.get_editor_url(month, year),
            # Botão "Novo Relatório" do cabeçalho: sempre aponta pro período
            # ATUAL (hoje), nunca pro período que o usuário só está
            # navegando/vendo no momento -- sem isso, clicar em "Novo" com um
            # relatório antigo selecionado abria o editor pré-preenchido com
            # o conteúdo desse relatório antigo, como se fosse editá-lo.
            "new_report_url": self.get_editor_url(today.month, today.year),
        }


class NarrativeEditorMixin:
    """Logica compartilhada da ferramenta de criacao/edicao (Quill), ver
    templates/directorates/shared/narrative_editor.html. Combinar com o
    *BaseMixin de cada app e definir `setor`.
    """
    setor = None

    def get_view_url(self, month, year):
        raise NotImplementedError("Subclasse deve implementar get_view_url(month, year)")

    def _existing_report(self, month, year):
        from apps.directorates.models import MonthlyReport

        directorate = self.get_directorate()
        return MonthlyReport.objects.filter(
            directorate=directorate, setor=self.setor, year=year, month=month
        ).first()

    def _deny_already_sent(self, request):
        from django.contrib import messages

        messages.warning(
            request,
            "Este relatório já foi enviado. Peça a um administrador para excluí-lo "
            "(no histórico da tela de Relatório Mensal) e liberar um novo envio.",
        )

    def get(self, request, *args, **kwargs):
        from datetime import date
        from django.shortcuts import redirect

        month = int(request.GET.get("month") or date.today().month)
        year = int(request.GET.get("year") or date.today().year)
        if self._existing_report(month, year) and not self.is_admin():
            self._deny_already_sent(request)
            return redirect(self.get_view_url(month, year))
        return super().get(request, *args, **kwargs)

    def get_editor_context(self, month, year):
        from apps.core.utils import extract_report_html

        directorate = self.get_directorate()
        report = self._existing_report(month, year)
        return {
            "directorate": directorate,
            "selected_month": month,
            "selected_year": year,
            "monthly_report": report,
            "report_content_html": extract_report_html(report.content) if report else "",
        }

    def save_narrative(self, request, month, year):
        from apps.core.utils import sanitize_report_html
        from apps.directorates.models import MonthlyReport

        directorate = self.get_directorate()
        if self._existing_report(month, year) and not self.is_admin():
            self._deny_already_sent(request)
            return None
        clean_html = sanitize_report_html(request.POST.get("content_html", ""))
        MonthlyReport.objects.update_or_create(
            directorate=directorate,
            setor=self.setor,
            year=year,
            month=month,
            defaults={
                "content": clean_html,
                "user_external_id": request.user.pk,
                "status": "finalized",
            },
        )
        return directorate
