# Gestaosuas-django — Contexto para IA

## O que é este projeto

Sistema de **Vigilância Socioassistencial** da Secretaria Municipal de Desenvolvimento Social de Uberlândia-MG. Coleta, consolida e visualiza dados de atendimento das unidades SUAS (CRAS, CREAS, NAICA, CEAI, SINE/CP, Pop Rua, Casa da Mulher, etc.).

Origem: port de uma aplicação Next.js + Supabase para Django puro. O banco PostgreSQL foi migrado para um container Docker standalone, sem dependência do Supabase. O Django se conecta diretamente ao PostgreSQL sem gerenciar o schema.

---

## Stack

| Componente | Tecnologia |
|---|---|
| Backend | Django 5.2.1 / Python 3.12 |
| Banco | PostgreSQL 15 Alpine em container Docker |
| Auth | Django ModelBackend (autenticação nativa) |
| Static files | WhiteNoise (produção) / Django dev server (dev) |
| WSGI | Gunicorn (produção) |
| Container | Docker Compose |
| Frontend | Django Templates + HTML/CSS/JS vanilla |

---

## Ambientes

### Dev local (porta 8001)
```sh
# Subir (⚠️ NÃO tem hot-reload de código — ver nota abaixo)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Parar
docker compose -f docker-compose.yml -f docker-compose.dev.yml down

# Logs em tempo real
docker logs gestaosuas_app_dev -f

# Shell Django
docker exec -it gestaosuas_app_dev python manage.py shell

# Gerenciar sem Docker (usa .env local + .deps/ vendorizado, porta 8001 para não conflitar)
python manage.py runserver 8001
```

URL dev: **http://127.0.0.1:8001/**

O container dev usa PostgreSQL 15 Alpine no serviço `db` do Docker Compose (porta 5432 interna, exposta em **5433** no host só em dev — permite `manage.py` rodar fora do Docker apontando `DB_HOST=127.0.0.1 DB_PORT=5433`).
Outro projeto (`gq-app`) já ocupa a porta 8000 — nunca use 8000 para este projeto localmente.

**`docker-compose.dev.yml` NÃO monta o código-fonte como volume** (só `static_volume`/`media_volume`, herdados do compose base) — o comentário "hot-reload automático" que existia aqui antes era enganoso. `DEBUG=1` liga o autoreload do `runserver`, mas ele só vê os arquivos que já estão *dentro da imagem* (copiados no build). Qualquer edição no host só chega ao container depois de `up -d --build` de novo. Para iterar rápido sem rebuildar, rode `python manage.py runserver 8001` direto no host (usa `.env` + `.deps/` vendorizado, ver seção Testes).

Além disso, como o compose faz merge por concatenação de listas, o serviço `app` do dev herda a porta `8080:8000` do compose base (mapeada para o serviço de produção) **e** adiciona `8001:8000` — ou seja, o container `gestaosuas_app_dev` também ocupa a porta 8080 localmente. Não é um problema em uso normal (só um container de app roda por vez localmente), mas explica confusão se algum dia tentar subir o compose de produção (`docker-compose.yml` sozinho) em paralelo ao dev na mesma máquina — vai dar conflito de porta 8080.

### VPS Produção

- IP Tailscale: `100.76.30.36` (NAS CasaOS, não é uma VPS tradicional — `$HOME` do usuário SSH é `/DATA`, pertence a `root`, sem escrita direta)
- Projeto Django em: `/DATA/AppData/Gestaosuas-django` (repo git próprio na VPS — remote de lá ainda não confirmado/atualizado nesta sessão) — deploys são feitos copiando arquivos via SFTP + commit local na VPS, não via `git pull`.
- **Repositório GitHub (checkout local deste projeto)**: remote `origin` = `https://github.com/gestaosuas/gestaosuas-django.git` (trocado nesta sessão, 2026-07-13 — as credenciais git configuradas localmente não têm permissão de push em `rdssystems/Gestaosuas-django`, só nesse repo `gestaosuas/gestaosuas-django`, que estava vazio e agora tem o histórico completo). Se o remote da VPS ainda apontar para `rdssystems`, provavelmente tem o mesmo problema de permissão — verificar antes de tentar `git push`/`git pull` de lá.
- URL pública (Tailscale Funnel): **https://servidor-qualificacao.tailbeb7d5.ts.net:8443** → proxy para `127.0.0.1:8080` (container `gestaosuas_app`)
- Outro app roda na raiz do mesmo domínio (porta 443 → `127.0.0.1:8000`, container `gq-app`, projeto Gestao-Profissional) — **não mexer nessa rota ao alterar a do gestaosuas**
- Banco: container `gestaosuas_db` (postgres:15-alpine), dados no volume nomeado `postgres_data` (reaproveitado entre rebuilds — não recriar/renomear o compose project ou perde o volume)
- Credenciais (SSH, banco, Supabase): ver `.env.local` na raiz deste repo (gitignored, nunca commitado)

**Gotchas operacionais da VPS:**
- `docker` do usuário `klismanrds` dá erro `permission denied` ao ler `/DATA/.docker/config.json` (pertence a root). Rodar sempre com `DOCKER_CONFIG=/tmp/dockercfg` (criar o dir antes) para o subcomando `docker compose` funcionar — sem isso, `docker compose` nem é reconhecido.
- `tailscale serve`/`tailscale funnel` rodando sem a flag `--bg`: a rota fica "foreground", atrelada à conexão SSH que criou — some assim que a sessão/canal fecha. **Sempre usar `--bg`** para persistir.
- Um `tailscale serve reset` limpa TODAS as rotas configuradas (inclusive as de outros apps expostos no mesmo domínio/Tailscale). Nunca rodar reset sem re-aplicar imediatamente todas as rotas existentes (checar `tailscale serve status` antes).
- Reiniciar o container `tailscale` (`docker restart tailscale`) derruba a própria conectividade Tailscale por alguns segundos — inclusive a sessão SSH em uso, se ela também passar pelo Tailscale.
- Depois de reset/restart do tailscale, as rotas voltam como "tailnet only" — é preciso reabilitar o Funnel (acesso público) explicitamente com `tailscale funnel --bg --https=<porta> http://127.0.0.1:<porta-local>`.

---

## Banco de Dados

| Ambiente | Host | Porta | DB | User | Password |
|---|---|---|---|---|---|
| Dev (Docker) | db (serviço Docker) | 5432 | postgres | postgres | postgres |
| VPS | db (serviço Docker) | 5432 | postgres | postgres | (via env) |

**CRÍTICO — `managed = False`**: Todos os models de negócio têm `managed=False`. O Django não cria nem altera tabelas via migrations. Migrations só existem para tabelas internas do Django (sessions, admin, auth). Nunca rodar `makemigrations` em apps de negócio sem entender essa constraint.

---

## Testes

Antes desta sessão não havia nenhum teste real no projeto (só o boilerplate padrão em `apps/ceai/tests.py`).

**Por que `manage.py test` sozinho não funciona**: por padrão o test runner do Django cria um banco de testes vazio e roda as migrations nele. Como os models de negócio são `managed=False`, as migrations desses apps não emitem `CREATE TABLE` (são só "state") — então o banco de testes vazio nunca teria as tabelas de negócio, e qualquer teste que toque nesses models falha com `relation "..." does not exist`.

**Solução aplicada** em `config/settings.py`: `DATABASES["default"]["TEST"] = {"NAME": os.getenv("DB_NAME", "postgres")}`, ou seja, aponta o "banco de testes" para o próprio banco (com schema real). Combinado com a flag `--keepdb`, o Django não tenta criar/destruir um banco novo — reusa o banco existente como está. Isso é seguro porque `TestCase` (não `TransactionTestCase`) envolve cada teste numa transação com rollback automático: nada é persistido de fato, mesmo rodando contra o banco com dados reais.

```sh
# Rodar testes de um app específico
DB_HOST=127.0.0.1 DB_PORT=5433 python manage.py test apps.<app> --keepdb -v 2

# Rodar toda a suíte
DB_HOST=127.0.0.1 DB_PORT=5433 python manage.py test --keepdb
```

Rodar local (fora do Docker, ver nota de hot-reload acima) é mais rápido para iterar — dentro do container `gestaosuas_app_dev` funcionaria igual, mas exige rebuild a cada mudança de código.

Regras para escrever testes neste projeto:
- Use `django.test.TestCase`, nunca `TransactionTestCase`, para manter o isolamento via rollback contra o banco real.
- Não crie/edite/apague linhas de tabelas "singleton" compartilhadas (`directorates`, `settings`) — prefira ler registros existentes (`Directorate.objects.first()` etc.) ou criar registros novos com identificadores únicos por teste.
- Nunca rodar com `--keepdb` omitido, e nunca sem confirmar que `DB_HOST`/`DB_PORT` apontam para o banco de **dev** (nunca para produção).

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

### 4. Autenticação
- `ModelBackend` (Django nativo) — único backend ativo
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
        managed = False           # SEMPRE — schema gerenciado manualmente no PostgreSQL
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
docker exec -it gestaosuas_db psql -U postgres -d postgres

# Build e subir dev
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Ver logs
docker logs gestaosuas_app_dev -f --tail 50
```

---

## Migração Supabase → PostgreSQL puro (status)

Script: `scripts/migrate_to_pure_pg.sql` (idempotente, projetado para rodar "no banco do VPS e no banco de dev local" — reaproveitável). Pré-requisito: `python manage.py migrate` já ter rodado (cria `accounts_user`). Fazer backup (`pg_dump -Fc`) antes de rodar.

- **Concluído e aplicado na VPS** (banco `gestaosuas_prod`): dump fresco puxado direto do Supabase de produção (projeto `xvyaaavcbxskmunmhwcg`) e restaurado, depois script de migração rodado em cima dele. Resultado: usuários copiados de `auth.users` → `accounts_user` (50/50, sem órfãos), FKs para `auth.users` removidas, RLS desabilitado, políticas RLS removidas, funções `auth.*`/`is_admin()` dropadas, constraint UNIQUE de `sine_reports`/`qualificacao_reports` corrigida para incluir `directorate_id`. App verificado funcionando (HTTP 200, login, 50 usuários Django).
- **Como puxar um dump novo do Supabase de produção** (se precisar repetir):
  - Conexão direta (`db.<ref>.supabase.co:5432`) só resolve em **IPv6** — não roteável a partir da VPS ("Network unreachable"). Usar o **connection pooler** (modal "Connect" no painel Supabase → aba "Session pooler", porta **5432**, não a Transaction/6543). Host confirmado para este projeto: `aws-0-us-west-2.pooler.supabase.com`, user `postgres.xvyaaavcbxskmunmhwcg` (ver `.env.local`).
  - Servidor Supabase é **PostgreSQL 17.6** — `pg_dump`/`pg_restore` do container `gestaosuas_db` (postgres:15-alpine) são incompatíveis (erro "server version mismatch" / "unsupported version in file header"). Usar um container temporário `postgres:17-alpine` (`docker run --rm --network gestaosuas-django_default -v /DATA/AppData/Gestaosuas-django:/out ...`) para dump E restore.
  - Restaurar com `pg_restore --clean --if-exists --no-owner --no-privileges` — dá ~70 erros esperados de `CREATE POLICY ... TO authenticated` (role Supabase que não existe aqui); ignorar, o script de migração dropa as políticas de qualquer forma depois.
  - Depois de restaurar, **sempre re-rodar `migrate_to_pure_pg.sql`** — o restore recria o schema original do Supabase (RLS habilitado, FKs, policies), desfazendo a limpeza anterior.
- **Banco ainda NÃO está fisicamente limpo**: os schemas de origem Supabase seguem no banco da VPS como resíduo inerte (não usados pela app): `auth`, `storage`, `realtime`, `extensions`, `supabase_functions`, `graphql`, `graphql_public`, `vault`, `pgbouncer`, `supabase_migrations`, `_realtime`. Dropar com `DROP SCHEMA <nome> CASCADE` quando quiser fazer a limpeza definitiva (nenhuma urgência — são inertes).
- `restaurar-banco.sh` existente tem `DB_NAME`/`DB_USER` hardcoded como `postgres`/`postgres` — o banco real é `gestaosuas_prod`/`gestaosuas_user` (`.env`). Ajustar antes de usar esse script.
- Correções feitas no script original (bugs de sintaxe, não eram assim antes desta sessão): `RAISE NOTICE` solto fora de bloco `DO $$...$$` não é válido em SQL puro (só em PL/pgSQL) — precisou envolver em `DO $$ BEGIN ... END $$;`; `constraint_name` ambíguo no JOIN do Passo 6 — precisou qualificar como `tc.constraint_name`.
- Também sincronizadas migrations Django que já existiam aplicadas na VPS mas não commitadas no repo: `apps/directorates/migrations/0002_alter_formdelegation_options.py`, `apps/naica/migrations/0001_initial.py`, `apps/sinecp/migrations/0001_initial.py`.
- Backups de segurança ficam em `/DATA/AppData/Gestaosuas-django/*.dump` na VPS (não versionados).

### Dump fresco puxado e restaurado no dev local (2026-07-13) — drift de schema encontrado

Repetiu-se o processo acima, mas contra o banco de **dev local** (`gestaosuas_db`), como teste antes de decidir o cutover real da VPS (que ainda não aconteceu — combinado com o usuário fazer isso "outro momento", começando com banco limpo). Backup de segurança do estado anterior salvo em `pre_supabase_restore_backup.dump` (gitignored, na raiz do repo).

Descoberta importante: **o Postgres local vinha recebendo alterações manuais de schema que nunca foram propagadas de volta pro Supabase.** Ao restaurar um dump 100% fresco do Supabase (depois de derrubar TODOS os schemas residuais — `auth`, `storage`, `realtime`, `vault`, `graphql`, `graphql_public`, `extensions`, `supabase_migrations`, `pgbouncer` — com `DROP SCHEMA ... CASCADE`, o que elimina os ~300+ erros de "already exists" que aparecem se restaurar em cima de resíduo antigo), várias divergências apareceram:

- **6 tabelas inteiras que existem no Postgres local mas não no Supabase**: `casa_da_mulher_reports`, `diversidade_reports`, `nucleo_diversidade_reports` (app `casamulher`), `creas_protetivo_reports` (app `protecaoespecial`), `monitorings_genericmonitoringreport` (app `monitoramento`) — essas 5 quebram os apps correspondentes até serem recriadas manualmente (managed=False, `migrate` não cria). A sexta, `protecao_especial_reports`, não é referenciada por nenhum model/view atual — resíduo morto, sem impacto. Ficou pendente recriar as 5 tabelas ativas (usuário optou por "deixar ausente por enquanto").
- **`visits` sem a coluna `visit_time`** (Django exige via `models.TimeField()`, sem `null=True`, e usa no `ordering`) — quebrava toda leitura/escrita de Visita técnica. Corrigido no dev com `ALTER TABLE visits ADD COLUMN visit_time time without time zone` (nullable, igual à definição original).
- **`cras_reports` sem a coluna `rma_url`** (usada em `apps/cras/views.py` para upload/leitura do anexo RMA) — corrigido com `ALTER TABLE cras_reports ADD COLUMN rma_url text`.
- **`visits` ganhou uma coluna nova no Supabase que o Django não conhece**: `work_plan_id` (FK pra `work_plans`) — dado existe no banco, sem campo correspondente no model. Não quebra nada, mas é uma feature (vincular visita a plano de trabalho) presente no banco e não exposta na aplicação. Não mexido.

**Lição para o cutover real da VPS**: repetir esse mesmo processo de comparação de schema (dump antigo vs. dump novo do Supabase) antes de ir para produção, para não descobrir esses gaps só quando um usuário real bater neles. Comando usado para comparar: restaurar os dois dumps em bancos separados e comparar `information_schema.columns` via `comm` (Postgres não suporta cross-database query direto).

---

## Débito Técnico Conhecido

| # | Problema | Impacto | Prioridade |
|---|---|---|---|
| 1 | `managed=False` em todos os models | Migrations não refletem o schema real; drift silencioso | Alta |
| 2 | `ProfileDirectorate.profile` usa `ForeignKey(unique=True)` em vez de `OneToOneField` | Warning Django não-crítico | Baixa |
| 3 | Colunas JSON de `visits` (identificacao, assinaturas, etc.) podem ter dupla codificação UTF-8 | Texto com acentos corrompido em detalhes de visita | Média |
| 4 | `strip_accents` e funções utilitárias duplicadas em `core/utils.py` e `monitoramento/views.py` | Inconsistência | Baixa |
| 5 | **[Parcialmente corrigido]** Colunas `user_id`/`created_by` de quase todas as tabelas de relatório tinham FK física para o schema Supabase residual `auth.users` em vez de `accounts_user` — achado por testes escritos em 2026-07. `scripts/migrate_to_pure_pg.sql` (Passo 7) repontou todas as 18 tabelas para `accounts_user`; **aplicado no banco de dev**, ainda **pendente aplicar na VPS de produção** | Até rodar o script na VPS, qualquer usuário criado lá depois da migração original recebe `IntegrityError` ao salvar relatórios/work plans/OSCs/visitas | **Alta — aplicar na VPS** |

Achados e corrigidos na mesma sessão (2026-07-13): rota `quick-edit` do NAICA/CRAS inacessível (ordem de URL), `IntegrityError` ao criar relatório novo via quick-edit do CREAS Idoso/PCD (`updated_at` faltando no `get_or_create`), 500 para admin em diretoria inexistente (query desprotegida em 6 List/CreateViews), drift de nullability em `naica_reports.user_id`, `ValidationError` não capturada em `DirectorateSlugConverter.to_url()`, tipo de coluna incompatível em `creas_pop_rua_reports.created_by` (agora `uuid` com FK), e toast de sucesso+erro simultâneo em `UserPermissionsView`. Ver `git log` para detalhes — não repetidos aqui pois já não são débito técnico atual.

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
| `DB_PORT` | Sim | Porta do banco (5432) |
| `CSRF_TRUSTED_ORIGINS` | Sim (prod) | Domínios confiáveis para CSRF |
