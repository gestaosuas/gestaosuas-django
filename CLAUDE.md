# Gestaosuas-django — Contexto para IA

## O que é este projeto

Sistema de **Vigilância Socioassistencial** da Secretaria Municipal de Desenvolvimento Social de Uberlândia-MG. Coleta, consolida e visualiza dados de atendimento das unidades SUAS (CRAS, CREAS, NAICA, CEAI, SINE/CP, Pop Rua, Casa da Mulher, etc.).

Origem: port de uma aplicação Next.js + Supabase para Django puro. O banco PostgreSQL foi criado pelo Supabase e continua sendo usado; o Django se conecta a ele sem gerenciar o schema.

---

## Stack

| Componente | Tecnologia |
|---|---|
| Backend | Django 5.2.1 / Python 3.12 |
| Banco | PostgreSQL via Supabase (local) ou container Docker (VPS) |
| Auth | Supabase Auth + Django ModelBackend (fallback) |
| Static files | WhiteNoise (produção) / Django dev server (dev) |
| WSGI | Gunicorn (produção) |
| Container | Docker Compose |
| Frontend | Django Templates + HTML/CSS/JS vanilla |

---

## Ambientes

### Dev local (porta 8001)
```sh
# Subir com hot-reload automático
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Parar
docker compose -f docker-compose.yml -f docker-compose.dev.yml down

# Logs em tempo real
docker logs gestaosuas_app_dev -f

# Shell Django
docker exec -it gestaosuas_app_dev python manage.py shell

# Gerenciar sem Docker (usa .env local, porta 8001 para não conflitar)
python manage.py runserver 8001
```

URL dev: **http://127.0.0.1:8001/**

O container dev conecta ao Supabase local via `host.docker.internal:54322`.
Outro projeto (`gq-app`) já ocupa a porta 8000 — nunca use 8000 para este projeto localmente.

### VPS Produção
- IP: `100.76.30.36` (ZimaOS NAS, acesso via Tailscale)
- URL pública: **https://servidor-qualificacao.tailbeb7d5.ts.net:8443**
- Banco: container `gestaosuas_db` no Docker do VPS

---

## Banco de Dados

| Ambiente | Host | Porta | DB | User | Password |
|---|---|---|---|---|---|
| Dev local | 127.0.0.1 | 54322 | postgres | postgres | postgres |
| Dev (Docker) | host.docker.internal | 54322 | postgres | postgres | postgres |
| VPS | db (serviço Docker) | 5432 | postgres | postgres | (via env) |

**CRÍTICO — `managed = False`**: Todos os models de negócio têm `managed=False`. O Django não cria nem altera tabelas via migrations. Migrations só existem para tabelas internas do Django (sessions, admin, auth). Nunca rodar `makemigrations` em apps de negócio sem entender essa constraint.

---

## Arquitetura — Decisões que afetam todo o código

### 1. UUID como Primary Key
Todos os models usam UUID:
```python
id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
```
Nunca usar `AutoField` ou `BigAutoField` nos models de negócio.

### 2. DirectorateSlugConverter (`apps/core/converters.py`)
Converter customizado registrado como `dir_slug` em `config/urls.py`. Converte slug amigável da URL (ex: `subvencao`) para UUID da `Directorate` correspondente, normalizando o campo `name` (remove acentos NFD, lowercase, hifens). Usado em TODAS as URLs que referenciam uma Directorate.

```python
# Exemplo de uso em urls.py de qualquer app
path("<dir_slug:pk>/", MinhaView.as_view(), name="home")
```

Se o nome de uma Directorate no banco estiver corrompido (encoding errado), o converter falha silenciosamente e retorna a string bruta, causando 500 no `filter(pk=...)`. Sempre verificar encoding de `directorates.name` ao depurar 500s em rotas de diretoria.

### 3. Context Processors globais
- `apps.core.context_processors.system_context` → injeta `system_name`, `system_reference_year`, `logo_url` em todos os templates
- `apps.directorates.context_processors.directorates_processor` → injeta lista de diretorias para a navbar

### 4. Autenticação dual
- `SupabaseAuthBackend` (ativo apenas se `SUPABASE_URL` estiver configurado no env)
- `ModelBackend` (fallback — único ativo no VPS e no dev sem Supabase)
- Roles de usuário: `admin`, `diretor`, `agente`, `user` (em `Profile.role`, tabela `profiles`)

---

## Mapa de Apps

| App | Prefixo URL | Finalidade |
|---|---|---|
| `core` | `/` e `/mapas/` | Mapa interativo, TV dashboard, configurações do sistema |
| `accounts` | `/accounts/` | Login por email, logout, listagem e permissões de usuários |
| `directorates` | `/directorias/` | OSCs, visitas técnicas, planos de trabalho, relatórios mensais |
| `cras` | `/cras/` | Relatórios mensais por unidade CRAS |
| `beneficios` | `/beneficios/` | Relatórios de benefícios sociais (CadÚnico, BPC, DMAE...) |
| `sinecp` | `/sine-cp/` | SINE e Qualificação Profissional (dois sub-módulos) |
| `naica` | `/naica/` | Relatórios NAICA por unidade |
| `ceai` | `/ceai/` | Gestão de oficinas e categorias do CEAI |
| `monitoramento` | `/monitoramento/` | Monitoramento genérico + Subvenções/OSCs/Visitas |
| `creasidoso` | `/creasidoso/` | CREAS Idoso e PCD |
| `poprua` | `/poprua/` | População em Situação de Rua |
| `protecaoespecial` | `/protecao-especial/` | CREAS Protetivo e Socioeducativo |
| `casamulher` | `/casa-mulher/` | Casa da Mulher, Diversidade e Núcleo de Diversidade |

**Status dos módulos:**
- Completos: `core`, `accounts`, `directorates`, `cras`, `beneficios`, `sinecp`, `naica`, `ceai`, `monitoramento`, `creasidoso`, `protecaoespecial`
- Em desenvolvimento: `poprua`, `casamulher`

---

## Convenções de Código

### Views — sempre CBV
```python
# CORRETO
class MinhaView(LoginRequiredMixin, TemplateView):
    template_name = "app/pagina.html"

# ERRADO — não usar function-based views
def minha_view(request):
    ...
```

Mixins de permissão por ordem de precedência:
1. `LoginRequiredMixin` — obrigatório em toda view
2. `AdminRequiredMixin` (definido em `apps/accounts/views.py`) — para ações administrativas
3. `MonitoramentoBaseMixin` — para views de módulo que precisam de diretoria via `self.kwargs["pk"]`

### Models
```python
class MeuReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    directorate = models.ForeignKey("directorates.Directorate", on_delete=models.CASCADE)
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=[
        ("draft", "Rascunho"),
        ("finalized", "Finalizado"),
        ("submitted", "Enviado"),
    ], default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False           # SEMPRE — schema pertence ao Supabase
        db_table = "nome_exato_da_tabela_no_banco"
        unique_together = [("directorate", "month", "year")]
```

### URLs
```python
# Namespace obrigatório em cada apps.py e urls.py
app_name = "meu_app"

urlpatterns = [
    path("<dir_slug:pk>/", MinhaHomeView.as_view(), name="home"),
    path("<dir_slug:pk>/preencher/", MinhaFormView.as_view(), name="form"),
    path("quick-edit/", MinhaQuickEditView.as_view(), name="quick_edit"),
]

# Referência em templates/views
reverse("meu_app:home", kwargs={"pk": directorate.pk})
```

### Templates
Estrutura de diretórios (sempre na raiz `templates/`, nunca dentro do app):
```
templates/
  base.html
  <app_name>/
    home.html
    _partial.html        # partials começam com _
    shared/
      form.html
```

### Formulários — campos numéricos de relatório
```python
class MeuReportForm(forms.ModelForm):
    campo_numerico = forms.IntegerField(
        min_value=0,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-input", "min": "0"}),
    )
```

### Relatórios mensais — padrão `get_or_create`
```python
report, created = MeuReport.objects.get_or_create(
    directorate=directorate,
    month=month,
    year=year,
    defaults={"status": "draft"},
)
```

---

## Estrutura de Arquivos por App

Cada app deve ter exatamente estes arquivos (adicionar apenas o que for necessário):
```
apps/
  meu_app/
    __init__.py
    apps.py          # define app_name
    models.py        # managed=False, UUID PK
    views.py         # CBVs com LoginRequiredMixin
    urls.py          # com app_name = "meu_app"
    forms.py         # ModelForms
    admin.py         # registro no admin (pode ficar vazio)
```

Arquivos opcionais (criar só se necessário):
```
    mixins.py        # mixins reutilizáveis do app
    context_processors.py   # somente core e directorates têm
    converters.py    # somente core tem
    utils.py         # somente core tem (funções globais)
    constants.py     # somente ceai tem
```

---

## Comandos úteis

```sh
# Rodar migrations (apenas tabelas Django internas)
docker exec -it gestaosuas_app_dev python manage.py migrate

# Criar superuser
docker exec -it gestaosuas_app_dev python manage.py createsuperuser

# Coletar static files
docker exec -it gestaosuas_app_dev python manage.py collectstatic --noinput

# Checar erros no projeto
docker exec -it gestaosuas_app_dev python manage.py check

# Acessar banco diretamente (dev)
psql -h 127.0.0.1 -p 54322 -U postgres -d postgres

# Build e subir dev
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Ver logs
docker logs gestaosuas_app_dev -f --tail 50
```

---

## Débito Técnico Conhecido

| # | Problema | Impacto | Prioridade |
|---|---|---|---|
| 1 | `managed=False` em todos os models | Migrations não refletem o schema real; drift silencioso | Alta |
| 2 | `ProfileDirectorate.profile` usa `ForeignKey(unique=True)` em vez de `OneToOneField` | Warning Django não-crítico | Baixa |
| 3 | Colunas JSON de `visits` (identificacao, assinaturas, etc.) podem ter dupla codificação UTF-8 | Texto com acentos corrompido em detalhes de visita | Média |
| 4 | `strip_accents` e funções utilitárias duplicadas em `core/utils.py` e `monitoramento/views.py` | Inconsistência | Baixa |

---

## Variáveis de Ambiente — Resumo

| Variável | Obrigatória em prod | Descrição |
|---|---|---|
| `DJANGO_SECRET_KEY` | Sim | Chave secreta Django |
| `DJANGO_DEBUG` | Sim | `1` = dev com runserver, `0` = prod com gunicorn |
| `DJANGO_ALLOWED_HOSTS` | Sim | Lista separada por vírgula |
| `DB_ENGINE` | Sim | Sempre `django.db.backends.postgresql` |
| `DB_NAME` | Sim | Nome do banco (padrão: `postgres`) |
| `DB_USER` | Sim | Usuário do banco |
| `DB_PASSWORD` | Sim | Senha do banco |
| `DB_HOST` | Sim | Host do banco |
| `DB_PORT` | Sim | Porta do banco (54322 dev / 5432 prod) |
| `SUPABASE_URL` | Não | Se ausente, auth Supabase fica desativado |
| `SUPABASE_ANON_KEY` | Não | Chave pública Supabase |
| `CSRF_TRUSTED_ORIGINS` | Sim (prod) | Domínios confiáveis para CSRF |
