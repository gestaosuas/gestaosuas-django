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

**Ambiente dev funciona em qualquer rede (2026-07-24)**: o usuário troca de rede com frequência (casa, trabalho, etc.), e o IP local muda a cada uma. `config/settings.py` força `ALLOWED_HOSTS = ["*"]` sempre que `DEBUG=1`, então isso nunca mais precisa ser configurado por rede — acesse por `http://localhost:8001/` (mais simples, nunca muda) ou pelo IP LAN atual da máquina (`ipconfig`/`Get-NetIPAddress`, muda por rede) se for acessar de outro aparelho. `docker-compose.dev.yml` já setava isso explicitamente (`DJANGO_ALLOWED_HOSTS=*`); agora `settings.py` garante o mesmo mesmo fora do Docker (`.env` local).

**Gotcha Windows/Docker Desktop**: nunca use `taskkill` bruto num PID só porque ele aparece "escutando" numa porta do projeto (`netstat -ano`) sem antes confirmar de quem é o processo (`Get-Process -Id <pid>` ou `Get-CimInstance Win32_Process`). Um PID em `0.0.0.0:<porta>` pode ser o proxy de encaminhamento do próprio Docker Desktop para um container publicado nessa porta, não um processo solto — matá-lo à força pode derrubar o backend do Docker inteiro (`com.docker.service`), exigindo reiniciar o Docker Desktop (ou o PC) pra recuperar. Aconteceu nesta sessão.

### VPS Produção

**Sempre use a skill `vps-deploy` (`.claude/skills/vps-deploy/SKILL.md`) para qualquer deploy** ("atualizar a vps", "dar deploy", "subir pra produção") — ela tem o padrão seguro de execução via SSH (saída sempre em arquivo, nunca no console — evita repetir o incidente de container órfão já sofrido nesta sessão) e o checklist de verificação pós-deploy. Não improvise um script SSH novo do zero quando essa skill já existe.

- IP Tailscale: `100.76.30.36` (NAS CasaOS, não é uma VPS tradicional — `$HOME` do usuário SSH é `/DATA`, pertence a `root`, sem escrita direta)
- Projeto Django em: `/DATA/AppData/Gestaosuas-django` (repo git próprio na VPS).
- **Repositório GitHub**: remote `origin` = `https://github.com/gestaosuas/gestaosuas-django.git`, tanto no checkout local quanto na VPS (trocados nesta sessão, 2026-07-13 — as credenciais git não têm permissão de push em `rdssystems/Gestaosuas-django`, só nesse repo `gestaosuas/gestaosuas-django`, que estava vazio e agora tem o histórico completo dos dois lados).
- **Sincronização de código VPS ↔ GitHub (2026-07-13)**: a VPS tinha 3 commits locais nunca enviados ao GitHub (`4e184c8`, `7dba38f`, `8207923` — fixes de bugs críticos/infra, BCryptPasswordHasher, `SECURE_PROXY_SSL_HEADER` para o Tailscale Funnel). Antes de descartar, confirmei que o conteúdo relevante (o fix de SSL) já existia de forma equivalente no repositório local/GitHub. Por pedido do usuário ("pode substituir tudo pelo nosso repositório atual"), criei a tag `backup-vps-antes-sync-2026-07-13` no repo da VPS (aponta pro HEAD antigo, `8207923` — recuperável com `git checkout backup-vps-antes-sync-2026-07-13` se precisar) e rodei `git fetch origin && git reset --hard origin/master`, alinhando a VPS 100% com o GitHub. Depois, `docker compose -f docker-compose.yml up -d --build` (com `DOCKER_CONFIG=/tmp/dockercfg`) recriou só `gestaosuas_app` — `gestaosuas_db` e todos os outros containers da máquina (`gq-app`, `gestao-ong-app-1`, etc.) não foram tocados. App verificado (HTTP 302, logs limpos, migrations aplicadas sem pendência).
- **Banco de dados da VPS NÃO foi mexido nessa sincronização** — `gestaosuas_prod` está mais completo que o backup local feito nesta sessão (tem as 6 tabelas `casa_da_mulher_reports`/`creas_protetivo_reports`/`diversidade_reports`/`monitorings_genericmonitoringreport`/`nucleo_diversidade_reports`/`protecao_especial_reports`, ausentes do dump fresco do Supabase, embora vazias; e tinha 194 `visits` contra 196 do backup local). Usuário optou por não sobrescrever — decisão pendente para uma sessão futura (aplicar só os fixes de schema do `migrate_to_pure_pg.sql` no lugar, sem restaurar por cima, é a opção mais segura já cogitada).
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
- `./atualizar.sh` (raiz do repo) tinha 4 bugs reais que só apareceram ao rodar de verdade (corrigidos em 2026-07-20, commits `246e9c6`/`ce54e21`/`bafcb4e`/`fceede1`): `BACKUP_DIR` usava `$HOME/backups` (`/DATA/backups`, root, sem escrita — sempre falhava no `mkdir`); o passo de `docker compose` não exportava `DOCKER_CONFIG=/tmp/dockercfg` (mesmo gotcha do item acima); o `pg_dump` usava `-U postgres -Fc postgres` fixo, mas a role `postgres` nem existe nesta VPS (banco real é `gestaosuas_prod`/`gestaosuas_user`, agora lido do `.env` do projeto); e o passo de backup no Google Drive originalmente tentava um `rclone remote` que nunca existiu nesta VPS, abortando o script inteiro por causa do `set -e`, antes mesmo do `git pull`/rebuild.
- **Backup no Google Drive**: `atualizar.sh` copia o dump para o diretório apontado por `GDRIVE_DIR` no `.env` do projeto (não versionado — ver `.env.local` na raiz, seção "Backup no Google Drive", para o valor real desta VPS). Não é um `rclone remote` configurado por nós: é uma pasta de uma conta Google já montada localmente pelo próprio CasaOS/ZimaOS (via `rclone.service` do sistema, rodando como root) — o mesmo mecanismo que outro app desta máquina (`Gestao-Profissional`) já usa para o próprio backup, só que numa subpasta irmã. Sem `GDRIVE_DIR` definido no `.env`, o passo é pulado silenciosamente (best-effort, nunca derruba o deploy).
- **Backup diário automático**: `backup_diario.sh` (raiz do repo) roda via `crontab` do usuário `klismanrds` na VPS, `0 2 * * *` (02:00, todo dia — configurado em 2026-07-20). Faz só backup (dump local + `GDRIVE_DIR` se definido), nunca `git pull`/rebuild — script separado do `atualizar.sh` de propósito, pra não reconstruir os containers sem supervisão todo dia. Mantém só os 10 backups mais recentes em cada lugar (local e Drive). Log em `backup_diario.log` (gitignored, mesma pasta do script) já que roda sem terminal. Ver `crontab -l` na VPS para conferir o agendamento (convive com a entrada já existente do `Gestao-Profissional`, que roda `0 12,19 * * *`).
- **Criptografia do backup (2026-07-29)**: `atualizar.sh` e `backup_diario.sh` criptografam o `.dump` (`openssl enc -aes-256-cbc -pbkdf2`) sempre que `BACKUP_ENCRYPTION_PASSPHRASE` estiver definida no `.env` da VPS (não versionada — ver `.env.local`) — vira `.dump.enc`, tanto local quanto no Drive, e o `.dump` sem criptografia é apagado na hora. Sem essa variável definida, o passo é pulado com aviso no log, backup segue sem criptografia (best-effort, igual `GDRIVE_DIR`). Motivo: o dump contém hash de senha de todos os usuários e dados de população vulnerável — achado no levantamento de segurança de 2026-07-29. Para decriptar um backup: `openssl enc -aes-256-cbc -pbkdf2 -d -in gestaosuas_XXXX.dump.enc -out gestaosuas_XXXX.dump -pass env:BACKUP_ENCRYPTION_PASSPHRASE` (com a variável exportada no shell).
- **Nunca rodar `./atualizar.sh` (ou qualquer `docker compose up -d --build`) via um script SSH (ex. paramiko `exec_command`) que pode morrer/crashar no lado do cliente no meio da execução** (aconteceu em 2026-07-25: um `UnicodeEncodeError` ao imprimir a saída no console Windows matou o processo Python local enquanto o `docker compose up -d --build` remoto estava recriando o container — como o canal SSH usava `get_pty=True`, fechar a conexão localmente derrubou o processo remoto no meio do recreate). Resultado: o container antigo (`gestaosuas_app`) ficou "Exited" e um novo container órfão com nome mangled (`<hash>_gestaosuas_app`, artefato do mecanismo de recreate seguro do Compose) ficou "Created" mas nunca foi promovido ao nome final — a app respondia (porta 8080 mapeada nesse container órfão), mas `docker ps`/`docker logs gestaosuas_app` não achavam nada com o nome certo. Corrigido com `docker rm -f <nome_orfao> gestaosuas_app` seguido de `docker compose up -d --build` limpo. Se isso acontecer de novo: sempre gravar a saída do comando remoto num arquivo (nunca `print()` direto pro console) pra evitar esse crash, e depois de qualquer deploy checar `docker ps --filter name=gestaosuas` pra confirmar que o nome do container é exatamente `gestaosuas_app` (não um nome com hash prefixado).

---

## Banco de Dados

| Ambiente | Host | Porta | DB | User | Password |
|---|---|---|---|---|---|
| Dev (Docker) | db (serviço Docker) | 5432 | postgres | postgres | postgres |
| VPS | db (serviço Docker) | 5432 | postgres | postgres | (via env) |

**CRÍTICO — `managed = False`**: Todos os models de negócio têm `managed=False`. O Django não cria nem altera tabelas via migrations. Migrations só existem para tabelas internas do Django (sessions, admin, auth). Nunca rodar `makemigrations` em apps de negócio sem entender essa constraint.

**CRÍTICO — ALTER TABLEs no deploy**: Como `managed=False`, `migrate` não aplica mudanças de schema nas tabelas de negócio. Toda vez que uma `ALTER TABLE` for feita em dev, o SQL deve ser adicionado a `scripts/pending_alters.sql` (idempotente, sempre usa `ADD COLUMN IF NOT EXISTS`). O `atualizar.sh` executa esse arquivo automaticamente após o `git pull` (passo 3.5). **Nunca faça deploy sem atualizar esse arquivo** — senão a VPS quebra com erro 500 de coluna inexistente.

---

## Testes

**Sempre use a skill `django-tests` (`.claude/skills/django-tests/SKILL.md`) antes de rodar a suíte ou escrever testes novos** — cobre os gotchas abaixo em detalhe (multi-app na mesma chamada dá erro, colisão de slug em `Directorate` de teste com nome temático, campos `NOT NULL` reais vs. o que o model sugere) e o procedimento pra descobrir se uma falha é pré-existente antes de tentar corrigi-la.

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

### 5. Tema por diretoria e layout "fit-to-viewport" (`static/css/app.css`)

**Cor da navbar/cabeçalho por diretoria**: cada diretoria tem uma cor fixa (`theme-emerald` CRAS/CEAI, `theme-indigo` NAICA/Proteção Especial/SINE-CP, `theme-blue` Benefícios/Pop Rua, `theme-amber` CREAS Idoso/PCD, `theme-pink` Casa da Mulher; Subvenção/Emendas/Outros usam cor dinâmica via `theme_class` no contexto — ver `get_monitoramento_theme()` em `apps/directorates/views.py`). A cor só é aplicada se o template define `{% block body_class %}...theme-X{% endblock %}` — como cada página de um app (home, form, dados, relatório mensal, histórico) é um arquivo `.html` separado que sobrescreve esse block individualmente, é fácil esquecer de definir em uma página nova e ela cair no azul de fallback do CSS (`--nav-grad-start: #366cb0`, coincidentemente igual ao `theme-blue`, o que mascara o esquecimento nas diretorias que já são azuis). **Ao criar uma página nova para uma diretoria já existente, sempre copiar o `{% block body_class %}` do `home.html`/`dashboard.html` daquele mesmo app.**

**`body.dashboard-fit-vh`**: classe que trava a página em exatamente `100vh` com `overflow: hidden !important` — pensada só para dashboards fixos tipo TV (o próprio `dashboard.html` de cada app, com KPIs/gráficos que devem caber numa tela só, sem rolar). **Nunca usar essa classe em páginas de conteúdo variável** (listagens, relatórios, formulários longos) — se o conteúdo real for mais alto que a tela, ele fica cortado e **não há nenhuma barra de rolagem para alcançá-lo** (bug real encontrado em 2026-07-25 no CEAI: `ceai/dados/` com "Todas as Unidades" tinha ~15000px de conteúdo, mas só os primeiros 900px apareciam, sem nenhuma forma de rolar até as outras unidades). Antes de copiar `dashboard-fit-vh theme-X` de outra página do mesmo app, perguntar: "essa página cabe garantidamente numa tela, sempre, para qualquer quantidade de dados?" — se a resposta for não, usar só `theme-X`.

**`.dashboard-container` precisa de `width: 100%` explícito** (além do `max-width` que já tinha) — sem isso, dentro do layout flex de `.app-shell`, o elemento encolhe pro tamanho mínimo do conteúdo em vez de esticar, e qualquer CSS Grid com `repeat(auto-fill, minmax(...))` dentro dele colapsa silenciosamente pra 1 coluna só (mesmo bug, achado e corrigido em 2026-07-25 — já corrigido na classe global, não deve mais acontecer, mas vale saber se aparecer de novo em outro contexto flex).

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

- **6 tabelas inteiras que existem no Postgres local mas não no Supabase**: `casa_da_mulher_reports`, `diversidade_reports`, `nucleo_diversidade_reports` (app `casamulher`), `creas_protetivo_reports` (app `protecaoespecial`), `monitorings_genericmonitoringreport` (app `monitoramento`) — essas 5 quebram os apps correspondentes até serem recriadas manualmente (managed=False, `migrate` não cria). A sexta, `protecao_especial_reports`, não é referenciada por nenhum model/view atual — resíduo morto, sem impacto.
- **`visits` sem a coluna `visit_time`** (Django exige via `models.TimeField()`, sem `null=True`, e usa no `ordering`) — quebrava toda leitura/escrita de Visita técnica. Corrigido com `ALTER TABLE visits ADD COLUMN visit_time time without time zone` (nullable, igual à definição original).
- **`cras_reports` sem a coluna `rma_url`** (usada em `apps/cras/views.py` para upload/leitura do anexo RMA) — corrigido com `ALTER TABLE cras_reports ADD COLUMN rma_url text`.
- **`visits` ganhou uma coluna nova no Supabase que o Django não conhece**: `work_plan_id` (FK pra `work_plans`) — dado existe no banco, sem campo correspondente no model. Não quebra nada, mas é uma feature (vincular visita a plano de trabalho) presente no banco e não exposta na aplicação. Não mexido.

**Atualização (2026-07-13, mais tarde — erros reais reportados em produção local)**: ao usar o app, apareceram os erros previstos acima: `/monitoramento/emendas-e-fundos/` (relation "monitorings_genericmonitoringreport" does not exist) e `/beneficios/painel/` (operator does not exist: text = uuid, em `beneficios_reports.directorate_id`). Esse segundo é um **bug de origem do próprio schema Supabase** (confirmado também na VPS — `directorate_id` é `text` lá também, sem FK, diferente de todas as outras tabelas de relatório), não um drift local. Corrigido:
- As 5 tabelas ativas (`casa_da_mulher_reports`, `diversidade_reports`, `nucleo_diversidade_reports`, `creas_protetivo_reports`, `monitorings_genericmonitoringreport`) foram recriadas no dev local com o DDL exato puxado da VPS (`\d <tabela>` na VPS, onde elas já existiam). FK de `user_id` apontada direto para `accounts_user` (não `auth.users` — esse schema nem existe mais no dev local).
- `beneficios_reports.directorate_id` (text → uuid, com FK para `directorates`) virou **Passo 9** do `scripts/migrate_to_pure_pg.sql` (idempotente, com checagem de órfãos) — aplicado tanto no dev local quanto na VPS.
- **`visits.visit_time` e `cras_reports.rma_url` também foram adicionadas na VPS** (mesmo `ALTER TABLE` do dev) — a VPS nunca teve essas colunas e o código atual (sincronizado lá nesta mesma sessão) as exige, o que causava 500 em `/monitoramento/...` na VPS também.

**Lição para o cutover real da VPS**: repetir esse mesmo processo de comparação de schema (dump antigo vs. dump novo do Supabase) antes de ir para produção, para não descobrir esses gaps só quando um usuário real bater neles. Comando usado para comparar: restaurar os dois dumps em bancos separados e comparar `information_schema.columns` via `comm` (Postgres não suporta cross-database query direto).

### Passo 7 e Passo 9B aplicados direto no `gestaosuas_prod` da VPS (2026-07-20)

Sem esperar pelo cutover de banco limpo (ainda não aconteceu — ver nota acima), a feature de múltiplos planos de trabalho com Objeto/Objetivos/Metas/Atividades em Emendas e Fundos (`Visit.work_plan` FK + colunas `work_plans.objeto/objetivos/metas/atividades`) precisava ir para produção. Rodado direto contra o banco de produção existente (`gestaosuas_prod`), não um banco limpo:

- Backup manual (`pg_dump -Fc`) tirado imediatamente antes, independente do backup que o próprio `atualizar.sh` já faz.
- `scripts/migrate_to_pure_pg.sql` inteiro rodado com `psql -v ON_ERROR_STOP=1` — transação commitada sem nenhum erro ou warning de órfãos.
- Isso finalmente aplicou o **Passo 7** (pendente desde 2026-07-13 — ver item #5 da tabela de débito técnico, agora marcado como concluído) e o novo **Passo 9B**. Passo 9 já era no-op (fix anterior).
- Deploy completo feito com `./atualizar.sh` na sequência (depois de corrigidos os bugs do próprio script — ver "Gotchas operacionais da VPS" acima). Container `gestaosuas_app` recriado, logs limpos, `HTTP 302` confirmado na porta 8080.

### Sincronização incremental Supabase → dev local (2026-08-02) — sem reset de banco

Diferente do cutover completo (dump+restore) usado em 2026-07-13, essa rodada sincronizou só os dados que estavam desatualizados, comparando linha a linha em vez de substituir tabelas inteiras — o objetivo era trazer dado real de produção (relatórios mensais, dados por diretoria, visitas técnicas) sem arriscar apagar dado que só existe localmente (testes de desenvolvimento já feitos direto no Django).

**Processo usado** (via `psycopg` conectando direto no pooler do Supabase — ver credenciais em `.env.local` — e no Postgres local em `127.0.0.1:5433`, sem precisar de container Postgres 17 temporário porque não é `pg_dump`/`pg_restore`, só `SELECT`/`INSERT` linha a linha):
1. Backup (`pg_dump -Fc`) do banco de dev local antes de qualquer escrita.
2. Para cada tabela: comparar `SELECT id FROM tabela` dos dois lados (`set` em Python) — nunca confiar só na contagem total (`COUNT(*)` igual não significa dado igual, ver achado do CRAS/CEAI abaixo).
3. Linhas que só existem no Supabase → `INSERT` local (dado novo real).
4. Linhas que só existem local → **investigadas antes de decidir**, nunca apagadas por padrão (ver achados abaixo).
5. Checar FK (`user_id` → `accounts_user`, `directorate_id` → `directorates`) antes de inserir — todas resolveram sem órfãos nesta rodada.
6. Colunas `jsonb`/`json` precisam ser envolvidas em `psycopg.types.json.Jsonb(...)` antes do `INSERT` (senão `psycopg.ProgrammingError: cannot adapt type 'dict'`).

**Achados importantes** (mesma classe do gotcha já documentado em 2026-07-13 — contagem igual pode esconder divergência real):
- `cras_reports`: 49 (Supabase) vs 46 (local) — mesmo tendo IDs diferentes, batiam por acaso quando comparadas por período; a comparação por `id` achou **10 faltando localmente E 7 que só existem localmente** (unidade CAMPO ALEGRE, `created_at` de 2026-07-21 — teste de preenchimento real feito em dev, preservado).
- `naica_reports`: 39 vs 31, 8 faltando localmente, nenhum órfão local.
- `beneficios_reports` e `submissions` (CEAI): mesma contagem nos dois lados escondia 1 registro diferente em cada — `submissions` tinha um **conflito real**: a mesma unidade/mês tinha um envio no Supabase (dado real, autor identificado) e outro só local (números redondos suspeitos, sem autor — claramente teste manual). Resolvido substituindo o registro de teste local pelo real do Supabase.
- `visits`/`oscs`/`work_plans`/`form_delegations`: mesmo padrão — 202/202 visitas escondia 6 faltando + 6 só-locais (visitas reais de teste de features entre 2026-07-25 e 2026-07-27, preservadas). `oscs` e `work_plans` tiveram que ser sincronizados **antes** de `visits` (dependência de FK).
- `monthly_reports`: 19 (Supabase) vs 17 (local) — 2 relatórios narrativos novos (Benefícios e CRAS, julho/2026); os outros 17 já batiam por ID exato.
- Tabelas que só existem localmente e nunca existiram no Supabase (features novas, não migradas): `casa_da_mulher_reports`, `diversidade_reports`, `creas_protetivo_reports`, `nucleo_diversidade_reports` — fora do escopo dessa sincronização, sem fonte no Supabase pra comparar.

**Lição**: `COUNT(*)` igual nunca é suficiente pra concluir que duas tabelas estão sincronizadas — sempre comparar por `id` (ou outra chave estável) antes de decidir se uma tabela "já está em dia".

### Mesma sincronização aplicada na VPS de produção (2026-08-02)

Repetido o processo acima contra `gestaosuas_prod` na VPS (não só o dev local) — mesmo método incremental (`psycopg`, comparação por `id`, nunca `pg_dump`/`pg_restore`), rodando **dentro do container `gestaosuas_app`** via `docker exec` (tem `psycopg` já instalado como dependência real do projeto — `requirements/base.txt` — e acesso de rede tanto ao serviço `db` quanto à internet pro pooler do Supabase; evita expor a porta do Postgres da VPS, que não tem `ports:` mapeado no `docker-compose.yml` base, só no `docker-compose.dev.yml`).

- Backup manual (`pg_dump -Fc`, 10.6 MB) tirado antes de qualquer escrita, independente do backup que o próprio `atualizar.sh` já faz no passo seguinte.
- Script rodado primeiro em `--dry-run` (ROLLBACK no final, só reporta), inspecionado, só depois em `--apply` (COMMIT real).
- Resultado: **52 linhas inseridas em 8 tabelas** (`oscs` +5, `work_plans` +8, `visits` +9, `form_delegations` +4, `monthly_reports` +3, `cras_reports` +12, `naica_reports` +8, `submissions` +1, `creas_idoso_reports` +2), **0 erros**. Segunda rodada em `--dry-run` confirmou `so_supabase=0` em todas as 15 tabelas verificadas — sincronização 100% completa.
- **2 conflitos de chave única** (`(directorate_id, month, year)`) resolvidos com confirmação explícita do usuário antes de agir: `submissions` (CEAI, Jul/2026) e `creas_idoso_reports` (Jan/2026) tinham um registro na VPS com cara de teste (`data: {'units': {}}` vazio, ou números redondos suspeitos — 100/5/10/105/210/525 — em `status='draft'`) colidindo com o registro real do Supabase (autor nomeado, `status='finalized'`, números variados). Ambos os registros de teste na VPS foram criados pelo mesmo `user_id`/`created_by`, na mesma janela de 5 minutos (2026-07-27 19:24–19:29) — padrão de teste manual pós-deploy. Deletados e substituídos pelo dado real do Supabase.
- **Gotcha de conexão**: construir a connection string do Postgres como URL crua (`postgresql://user:senha@host:porta/db`) quebra se a senha tiver caractere `@` — o parser do libpq splita no primeiro `@` errado, tentando resolver um "host" tipo `senha_parcial@db`. Usar sempre `psycopg.connect(host=..., user=..., password=..., dbname=...)` com kwargs nomeados, nunca montar a URL na mão.
- **Gotcha de colunas**: algumas colunas existem só no destino (`visits.visit_time`, `cras_reports.rma_url`, `creas_idoso_reports`/`creas_pcd_reports`/`qualificacao_reports` com colunas novas de estratificação — todas via `ALTER TABLE` aplicado local/VPS mas nunca propagado de volta pro Supabase, que é só leitura agora). O script de sync precisa usar a **interseção** de colunas entre os dois bancos (nunca a lista de colunas de um lado só) — as colunas exclusivas do destino ficam com o default/NULL nas linhas novas, sem travar o `INSERT`.
- Isso finalmente elimina o gap que motivava o "VPS clean-DB plan" (banco de produção agora tem os mesmos dados do Supabase que o dev local já tinha desde 2026-08-02, sem precisar de um cutover completo com reset).
- Deploy do código feito na sequência via `./atualizar.sh` (skill `vps-deploy`) — commit `f2acd44`, containers recriados com nome exato `gestaosuas_app`/`gestaosuas_db`, `HTTP_STATUS=302` confirmado.

---

## Export Excel

Todas as páginas "Ver Dados" têm botão **Exportar Excel** (visível só para admin, verifica `can_delete`).

- **Módulo**: `apps/core/export.py` — função `build_workbook(sheets, filename)` + mixin `ExcelExportMixin`
- **Dependência**: `openpyxl>=3.1` em `requirements/base.txt`
- **Trigger**: `?export=xlsx` na URL (o mixin intercepta no `get()`)
- **Templates**: botão verde `<a href="?{{ request.GET.urlencode }}&export=xlsx" class="btn-excel">`
- **Regra de abas**:
  - Apps com unidades (CRAS, NAICA): 1 aba por unidade (todas seções juntas)
  - Apps sem unidades (demais): 1 aba por seção/tabela
- **Sanitização**: títulos de aba têm caracteres inválidos (`\ / * ? : [ ]`) substituídos por `-`, truncados em 31 chars

---

## Estratificação de Formulários CREAS

A partir de 2026-07-21, os formulários de violação do CREAS foram estratificados:

### Idoso e PCD — por gênero
5 violações × 4 subcampos × 2 gêneros = 40 campos por tabela.
- Labels no form: `f"{suf_label} — Masculino"` / `"Feminino"`
- Exemplo DB: `violencia_fisica_atendidas_anterior_masc`, `violencia_fisica_total_fem`
- Campos computados: `total_masc`, `total_fem`, `total_geral` por violação; `idoso_total_geral_masc`/`fem`

### Protetivo — por gênero + faixa etária
5 violações × 3 subcategorias × 6 gender-age = 90 campos.
- Prefixos: `vf`, `as`, `es`, `ng`, `ti`
- Sufixos: `at` (atendidas anterior), `in` (inseridos), `de` (desligados)
- Gender-age: `m0`, `m7`, `m13`, `f0`, `f7`, `f13` (Masc/Fem × 0-6/7-12/13-17)
- Exemplo DB: `vf_at_m0`, `ng_de_f13`

### Seções vs labels (convenção)
- Título da seção: nome completo (ex: "Pessoas idosas vítimas de violência física ou psicológica")
- Labels dos campos: só o sufixo + gênero (ex: "Mês Anterior — Masculino"), sem repetir o título da seção
- `(PAEFI)` e `(casos novos)` removidos dos labels do PAEFI (redundantes com o título da seção)

---

## Débito Técnico Conhecido

| # | Problema | Impacto | Prioridade |
|---|---|---|---|
| 1 | `managed=False` em todos os models | Migrations não refletem o schema real; drift silencioso | Alta |
| 2 | `ProfileDirectorate.profile` usa `ForeignKey(unique=True)` em vez de `OneToOneField` | Warning Django não-crítico | Baixa |
| 3 | Colunas JSON de `visits` (identificacao, assinaturas, etc.) podem ter dupla codificação UTF-8 | Texto com acentos corrompido em detalhes de visita | Média |
| 4 | `strip_accents` e funções utilitárias duplicadas em `core/utils.py` e `monitoramento/views.py` | Inconsistência | Baixa |
| 5 | **[Corrigido]** Colunas `user_id`/`created_by` de quase todas as tabelas de relatório tinham FK física para o schema Supabase residual `auth.users` em vez de `accounts_user` — achado por testes escritos em 2026-07. `scripts/migrate_to_pure_pg.sql` (Passo 7) repontou todas as 18 tabelas para `accounts_user`; aplicado no banco de dev em 2026-07-13 e **na VPS de produção em 2026-07-20** (rodado direto contra `gestaosuas_prod`, com backup manual antes — ver seção "Migração Supabase → PostgreSQL puro") | ~~Até rodar o script na VPS, qualquer usuário criado lá depois da migração original recebia `IntegrityError` ao salvar relatórios/work plans/OSCs/visitas~~ Resolvido | Concluída |
| 6 | `beneficios_reports.user_id` é setado para `None` no `form_valid()` em vez de `request.user.pk` (diferente do padrão de todas as outras diretorias) | Quem preencheu benefícios não é rastreável | Média |

Achados e corrigidos na mesma sessão (2026-07-13): rota `quick-edit` do NAICA/CRAS inacessível (ordem de URL), `IntegrityError` ao criar relatório novo via quick-edit do CREAS Idoso/PCD (`updated_at` faltando no `get_or_create`), 500 para admin em diretoria inexistente (query desprotegida em 6 List/CreateViews), drift de nullability em `naica_reports.user_id`, `ValidationError` não capturada em `DirectorateSlugConverter.to_url()`, tipo de coluna incompatível em `creas_pop_rua_reports.created_by` (agora `uuid` com FK), e toast de sucesso+erro simultâneo em `UserPermissionsView`. Ver `git log` para detalhes — não repetidos aqui pois já não são débito técnico atual.

Achados e corrigidos em 2026-07-25: navbar não seguia a cor da diretoria fora da página inicial de cada app (faltava `{% block body_class %}` nos templates de form/dados/relatório — ver seção "Arquitetura" item 5), `theme-pink` (Casa da Mulher) nunca tinha sido definido em `app.css`, e no CEAI especificamente: modais de Categorias/Oficinas sem altura máxima/rolagem (ficavam maiores que a tela e sem botão de fechar alcançável), `.dashboard-container` sem `width:100%` colapsando grids de colunas pra 1 coluna só, e `dashboard-fit-vh` aplicado por engano em páginas de conteúdo variável (`ceai/dados/` e `ceai/.../oficinas/`, cortando a maior parte do conteúdo sem nenhuma rolagem possível — ver seção "Arquitetura" item 5). Formulário "Atualizar Dados" do CEAI também virou um wizard por sessão (Movimentação → uma categoria de oficina por passo) e o filtro de categoria em `ceai/dados/` virou multi-seleção (dropdown com checkboxes).

---

## Manutenção de docs/dominio/

Os arquivos em `docs/dominio/` (`00-modelo-de-dados.md`, `01` a `04`) são a fonte de verdade sobre schema e regras de negócio. Regras de atualização:

1. **NUNCA atualize esses arquivos silenciosamente durante uma tarefa de implementação.** Se descobrir uma regra de negócio não documentada durante um ajuste, PARE e pergunte antes de assumir — não escreva no arquivo por conta própria.

2. **Atualize `00-modelo-de-dados.md` automaticamente** (sem pedir permissão) sempre que:
   - Uma `ALTER TABLE` for aplicada em dev ou produção
   - `migrate_to_pure_pg.sql` ganhar um novo Passo
   - Re-rode o `inspectdb` e atualize o arquivo. Registre no Changelog do próprio arquivo (data + o que mudou) — nunca sobrescreva sem histórico.

3. **Atualize `01` a `04` (regras de negócio) SOMENTE quando o usuário confirmar** resposta nova a uma pergunta de alinhamento, ou uma regra mudar por decisão explícita dele. Nunca infira mudança de regra a partir de um bug corrigido — bug corrigido não vira regra nova automaticamente.

4. **Todo arquivo em `docs/dominio/` mantém uma seção final "Changelog"** (data — o que mudou — por quê).

---

## Variáveis de Ambiente — Resumo

| Variável | Obrigatória em prod | Descrição |
|---|---|---|
| `DJANGO_SECRET_KEY` | Sim | Chave secreta Django |
| `DJANGO_DEBUG` | Sim | `1` = dev com runserver, `0` = prod com gunicorn |
| `DJANGO_ALLOWED_HOSTS` | Sim | Lista separada por vírgula. **Ignorada em dev** (`DJANGO_DEBUG=1`) — `config/settings.py` força `ALLOWED_HOSTS = ["*"]` nesse caso, então o dev funciona em qualquer rede (casa, trabalho, etc.) sem precisar atualizar essa variável a cada troca de IP. Só é lida/obrigatória de fato quando `DEBUG=0` (produção) |
| `DB_ENGINE` | Sim | Sempre `django.db.backends.postgresql` |
| `DB_NAME` | Sim | Nome do banco (padrão: `postgres`) |
| `DB_USER` | Sim | Usuário do banco |
| `DB_PASSWORD` | Sim | Senha do banco |
| `DB_HOST` | Sim | Host do banco |
| `DB_PORT` | Sim | Porta do banco (5432) |
| `CSRF_TRUSTED_ORIGINS` | Sim (prod) | Domínios confiáveis para CSRF |
