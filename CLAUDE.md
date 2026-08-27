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
- **Cloudflare Tunnel (segunda forma de acesso público, além do Tailscale Funnel acima), descoberto/estendido em 2026-08-17**: já existia na VPS/NAS um container `cloudflared-tunnel` (`docker run` avulso, não gerenciado pelo compose deste projeto), túnel `gestao-tunnel` (ID `09a0b5cd-6a4a-455d-a851-13861540672d`), config em `/DATA/AppData/cloudflared/config.yml` (fora do repo git — infra da máquina, não do projeto). Já roteava `app.gestaoqualificacao.com.br` → `http://localhost:8000` (gq-app) e `suas.gestaoqualificacao.com.br` → `http://localhost:8080` (este app). Nesta sessão, o domínio **`gestaosuasuberlandia.com.br`** (migrado de nameservers Vercel para Cloudflare, mesma conta Cloudflare do `gestaoqualificacao.com.br`) foi adicionado ao mesmo túnel: `gestaosuasuberlandia.com.br` e `www.gestaosuasuberlandia.com.br` → `http://localhost:8080`, mesmo destino de `suas.gestaoqualificacao.com.br`. `DJANGO_ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` no `.env` da VPS ganharam os dois novos hosts (e, de brinde, `CSRF_TRUSTED_ORIGINS` recebeu `suas.gestaoqualificacao.com.br`, que já estava em `ALLOWED_HOSTS`/recebendo tráfego real mas faltava no CSRF — POSTs, como login, provavelmente falhavam nesse domínio antes desse fix).
  - **Gotcha real encontrado**: `cloudflared tunnel route dns <tunnel> <hostname>` cria o registro CNAME automaticamente na Cloudflare, mas só funciona se o `cert.pem` do túnel tiver autoridade sobre a **zona** (domínio raiz) do hostname pedido. O `cert.pem` deste túnel é escopado só para `gestaoqualificacao.com.br` — mesmo estando na mesma conta Cloudflare, rodar o comando para `gestaosuasuberlandia.com.br` **não falha com erro claro**: cria silenciosamente um CNAME errado/inerte dentro da zona `gestaoqualificacao.com.br` (ex.: `gestaosuasuberlandia.com.br.gestaoqualificacao.com.br`), não na zona certa. Para adicionar uma nova zona a este túnel, os CNAMEs têm que ser criados **manualmente no dashboard Cloudflare**, na zona certa: nome `@`/raiz e nome `www`, ambos apontando para `<tunnel-id>.cfargotunnel.com`, com proxy (nuvem laranja) ligado.
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

## PWA (instalar como app)

Adicionado em 2026-08-17. Botão "Instalar Aplicativo" na tela de login (`templates/accounts/login.html`, `#pwaInstallBtn`) — só aparece se o navegador disparar `beforeinstallprompt` (Chrome/Edge/Android que julgam o site instalável; **não existe no iOS Safari**, sem API de instalação programática lá — no iPhone a instalação é manual via Compartilhar → Adicionar à Tela de Início, sem botão possível).

- **Manifest** (`/manifest.json`, `ManifestView` em `apps/core/views.py`): view, não arquivo estático — assim `name` acompanha `SystemSetting.system_name` (mesmo texto do navbar/login) sem precisar rebuild pra mudar. Ícones: `static/img/icon-192.png` (gerado via PIL a partir de `logo.png`, único arquivo novo commitado) e `static/img/favicon-512x512.png` (já existia).
- **Service worker** (`/sw.js`, `ServiceWorkerView`): mínimo de propósito — só tem os listeners `install`/`activate`/`fetch` exigidos pelo critério de instalabilidade do Chrome (sem esse SW registrado com handler de `fetch`, `beforeinstallprompt` nunca dispara). **Sem cache/offline de propósito** — os dados do sistema (visitas, relatórios) precisam sempre vir atualizados do servidor; cachear páginas aqui seria perigoso.
- Ambos servidos via `View` do Django (não `staticfiles`/WhiteNoise) porque precisam ficar exatamente em `/manifest.json` e `/sw.js` na raiz — o escopo do service worker é o diretório do próprio script, então só cobre o site inteiro (`/`) servido dali. Rotas em `apps/core/urls.py` (já montado na raiz via `config/urls.py`), sem `LoginRequiredMixin` (o navegador busca isso antes do login, na própria tela de login).
- `templates/base.html`: `<link rel="manifest">` + `<meta name="theme-color" content="#0a1128">` no `<head>`, registro do SW num `<script>` antes do `lucide.createIcons()`.
- **Testado**: `manifest.json`/`sw.js` retornam 200 com content-type correto (test client); no navegador real (browser-automation), o service worker registra e ativa (`state: "activated"`, scope `/`) e o manifest é válido/buscável, sem erro de console. `beforeinstallprompt` **não disparou no Chromium headless** — limitação conhecida do modo headless (heurística de instalabilidade do Chrome depende de sinais de engajamento real que uma sessão automatizada fresca não tem), não indica bug — os pré-requisitos (manifest válido, SW registrado, ícones) estão todos satisfeitos. Confirmação final do prompt em si precisa ser feita num Chrome/Edge real.

**Bug real achado pelo usuário testando em produção — `visit_time` sempre 09:00 (2026-08-17)**: `VisitCreateView.post()` (`apps/directorates/views.py`) tinha `visit_time="09:00"` **hardcoded** — não é campo real do formulário "Nova Visita" (só existe "Data da Visita" + "Turno" Manhã/Tarde, nunca um horário específico), então o valor fixo servia só pra satisfazer a constraint `NOT NULL` do banco (`Visit.visit_time = models.TimeField()`, sem `null=True`). Toda visita criada por qualquer usuário, desde sempre, tinha exatamente esse valor. Só ficou visível/notado agora porque os cards novos de "Instrumental de Visita" (ver seção acima) mostram `visit_date · visit_time` com destaque no cabeçalho do card — antes o campo existia mas não aparecia em lugar nenhum tão em evidência. Corrigido pra `visit_time=datetime.now().time()` (mesmo padrão já usado no fallback de `visit_date` na linha de cima) — confirmado que `datetime.now()` já retorna hora local do Brasil corretamente aqui (checado contra `timezone.localtime()` no container, batem no segundo, apesar do `date` do SO mostrar UTC) então não introduz bug de fuso. Testado via Django test client: visita nova criada agora tem `visit_time` batendo com o horário real da criação.

**Confirmado, não é bug — botão "Reverter para Rascunho" só aparece em visita já finalizada**: mesma sessão, usuário reportou o botão "sumido" dos cards novos. Investigado e reproduzido via test client: o botão renderiza corretamente pra visita com `status='finalized'`/`'completed'` e corretamente NÃO renderiza pra `status='draft'` (nada a reverter) — comportamento idêntico ao da tabela antiga, sem regressão. As 3 visitas reais que o usuário tinha acabado de criar pra testar os cards estavam todas em rascunho, por isso o botão não aparecia pra nenhuma delas — não uma remoção acidental do botão.

**Layout de tablet do formulário "Nova Visita"/"Editar Visita" reconfigurado (2026-08-17)**: `templates/directorates/monitoring/visit_instrumental.html` (Subvenção e Emendas e Fundos) tinha **duas** regras `@media (max-width: 1024px)` em pontos diferentes do arquivo, brigando pela mesma classe — a que vinha depois no arquivo sempre vencia a cascata, e ela achatava quase tudo (`.visit-top-actions`, `.signature-grid`, `.visit-grid-two/-three`, `.attendance-top-grid`, `.visit-check-grid`, `.attendance-present-grid`, `.visit-evidence-grid`) pra 1 coluna só, mesmo quando a primeira regra pedia 2 ou 3. Consolidado num único bloco, com colunas específicas por seção (pedido explícito do usuário, olhando telas de tablet real):
- **Botões do topo**: "Voltar" numa linha sozinho, os outros 4 (Plano de Trabalho, Imprimir Relatório, Salvar Rascunho, Finalizar Visita) em 2x2.
- **Identificação**: HTML reestruturado (não só CSS) — "Endereço" virou campo próprio de linha inteira; "Telefone" e "Plano de Trabalho vinculado" (antes cada um sozinho num grid de 2 colunas, desperdiçando metade do espaço) agora dividem o mesmo grid de 2 colunas. Isso muda a organização em qualquer largura de tela, não só tablet — é reagrupamento de campo, não response responsivo.
- **Dados da visita**: Data da Visita + Turno em 2 colunas (o botão condicional "Adicionar Visita", quando aparece, cai numa 2ª linha).
- **Atendimento**: Horário Início/Fim pareados, Total/Mês + Subvencionados pareados (Tipo de Horário, 1º campo do grid, ocupa a linha toda via `:first-child { grid-column: 1/-1 }` — sem precisar duplicar HTML).
- **Usuários presentes**: Manhã/Tarde/Lista de Espera/Total em 4 colunas — achado um bug real na QA visual: o campo oculto "Quant. Espera" (`#attendanceWaitingQuantityField`) usava só `visibility:hidden`, que ainda reserva célula de grid mesmo invisível, empurrando "Total" pra uma 2ª linha sozinho. Corrigido combinando com `display:none` (tanto no HTML server-renderizado quanto na função JS `updateWaitingListQuantityVisibility()` que alterna o campo ao vivo) — testado nos dois sentidos (Sim→Não e volta) via browser real, sem sobra de espaço.
- **Forma de Acesso**: os 4 checkboxes em 2x2 ("Quem encaminha?" já ficava fora desse grid, continua aparecendo abaixo).
- **Colaboradores**: fonte um pouco menor (`.visit-rh-table th` e `.visit-table-input`) só no tablet.
- **PSE Qualitativos**: `.pse-qualitative-table` ganhou `min-width` reduzido (900px→760px, específico pra ela, não afeta a tabela Quantitativos ao lado) + padding/fonte menores nos inputs.
- **Fotos/Evidências**: Abrir Câmera + Selecionar da Galeria em 2 colunas (existe em duplicado no arquivo — uma versão pra `is_subvencao_visit`, outra pra as demais — mas ambas usam a mesma classe `.visit-evidence-grid`, um fix cobriu as duas).
- **Assinaturas**: Técnico 1 + Técnico 2 em 2 colunas, Representante da OSC (3º bloco) ocupando a linha inteira abaixo via `:nth-child(3) { grid-column: 1/-1 }`.
- **Botões de baixo** (`.visit-footer-actions-inner`, "Salvar rascunho"/"Finalizar e bloquear"): viraram 2 colunas + cor igualada à dos botões de cima — "Finalizar e bloquear" usava um verde diferente (`#059669`/`#10b981`) do azul do botão "Finalizar Visita" do topo (`#1d4ed8`/`#1e40af`); agora usa o mesmo gradiente azul.
- Testado via Django test client (renderização sem erro em modo criar/editar, com PSE habilitado) e depois com navegador real em 820×1180 (tablet retrato) e 1024×800 (paisagem) — 11 itens confirmados visualmente, 0 erro de console.

**Campo Data da tabela PSE Qualitativos virou `type="date"` (2026-08-17)**: era `type="text"` (texto livre) nos 3 pontos onde a linha é criada em `visit_instrumental.html` (2 no HTML server-side — linha existente e as 4 linhas em branco padrão — e 1 no JS `addPseQualRow()`). Registros antigos com texto que não bate no formato `AAAA-MM-DD` (ex.: "01/01" sem ano) ficam em branco no seletor — o valor continua salvo no banco, só não aparece até alguém preencher de novo.

**Cabeçalho do PDF (logo/instituição/título) repetia em toda página — corrigido pra só aparecer na 1ª (2026-08-17)**: `SystemDocTemplate` (`apps/core/pdf.py`) tinha um único `PageTemplate` com `onPage` desenhando cabeçalho+rodapé em toda página gerada — pedido do usuário pra documentos de mais de 1 página (todos os PDFs do sistema passam por esse módulo único: `pdf_response()`, usado por Relatório Mensal Narrativo, Plano de Trabalho, Instrumental de Visita e os 3 tipos de Relatório/Parecer — nenhum outro lugar do código usa ReportLab). Reescrito com **2** `PageTemplate`s (`"first"` com cabeçalho+rodapé, `"later"` só com rodapé) trocados via `NextPageTemplate("later")` inserido como primeiro item da story em `pdf_response()` — padrão-idiomático do ReportLab pra "timbrado só na 1ª página" (a troca só faz efeito a partir da 2ª página, a 1ª sempre usa o template registrado primeiro). Página 2+ também ganhou margem superior menor (`LATER_PAGE_TOP_MARGIN = 16mm` em vez dos `TOP_MARGIN = 31mm` da 1ª), já que não precisa mais reservar espaço pro cabeçalho que não é mais desenhado ali. O rodapé (número de página + "Gerado em") continua em todas as páginas, sem mudança. Testado com `PyMuPDF` (`fitz`, já instalado) extraindo texto por página de um Relatório Final real de 9 páginas — página 1 tem a linha institucional, páginas 2-9 não têm, rodapé com numeração correta em todas.

**Logo do cabeçalho do PDF aumentada (2026-08-17)**: `_draw_header()` em `apps/core/pdf.py`, de 13mm pra 18mm (`text_x` ajustado de +16mm pra +21mm pra acompanhar). Confirmado visualmente renderizando a página 1 como imagem via PyMuPDF antes/depois — sem sobrepor a linha divisória abaixo do subtítulo.

**Página "Documento" da visita (`visit_document.html`) — logo reduzida e selo "Finalizado" movido pra fora do card (2026-08-17)**: pedido do usuário olhando a página renderizada (essa é a view HTML pra visualizar/imprimir o Instrumental de uma visita finalizada, `?export=pdf` nela chama um PDF ReportLab **separado** — não usa `SystemDocTemplate`/`apps/core/pdf.py`, então o ajuste de logo do item acima não afeta essa página). `.visit-document-logo` (o `logo_url` de `SystemSetting`, formato retangular tipo navbar) tava com `max-width:250px`, competindo por espaço com o título de 2 linhas — reduzido pra `170px`. O selo verde "Documento Finalizado e Autenticado" tinha `position:absolute` **dentro** de `.visit-document-page` (o card branco que representa a folha), sobrepondo visualmente a área do cabeçalho — movido pra fora do card, como uma linha própria (`.visit-document-status-row`, alinhada à direita) entre a toolbar e o card, e ganhou `no-print` (não é algo que deveria aparecer numa impressão/PDF real do documento, só é um indicador de UI da tela). Confirmado com navegador real: selo com espaço visível acima do card, sem sobreposição; logo proporcional ao título.

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

## Excluir usuário (admin-only, soft-delete) — 2026-08-20

Pedido explícito do usuário: opção de remover um usuário, restrita a admin, com alerta de confirmação de exclusão via o modal do próprio sistema (não `confirm()` nativo do navegador). Antes de implementar, o usuário confirmou explicitamente que a exclusão deve ser **soft-delete** (desativar), não hard-delete — a maioria das tabelas de relatório/visita (`visits.user_id`, `cras_reports.user_id`, `form_delegations.delegated_by`, etc.) referencia o usuário como `UUIDField` solto, sem FK (`managed=False`), então apagar o `User` de vez faria toda autoria histórica virar "Desconhecido" pra sempre, sem poder reverter.

- **`UserDeactivateView`/`UserReactivateView`** (`apps/accounts/views.py`, `AdminRequiredMixin`, só POST): setam `User.is_active = False`/`True`. O `ModelBackend` nativo do Django já bloqueia login de usuário inativo em `authenticate()` — nenhuma mudança extra precisou ser feita no fluxo de login. Auto-exclusão bloqueada no servidor (`str(profile.user_id) == str(request.user.id)` → `messages.error`, sem tocar no banco) — é a checagem autoritativa; o botão "Excluir" também some da própria linha do admin logado no template (`{% if profile.pk != request.user.profile.pk %}`), mas só como UX, não como segurança (se `request.user.profile` não existir por algum motivo, o `{% if %}` falha aberto/mostra o botão, mas o POST ainda seria bloqueado no servidor).
- **`apps/core/notifications.py`**: `ACTION_VERBS` ganhou `"deactivated": "excluiu"` e `"reactivated": "reativou"` (antes só existiam `created`/`updated`/`finalized`) — sem isso, o sino de notificação mostraria "Fulano **editou** Usuário Ciclana" pra uma exclusão, o que lia mal.
- **`templates/accounts/user_list.html`**: nova coluna "Status" (badge verde "Ativo" / cinza "Excluído"), botão "Excluir" (vermelho, ícone `user-x`) que abre um modal de confirmação com o nome do usuário interpolado via JS (mesmo padrão `openXModal(url, nome)` já usado no modal "Delegar Visita" de monitoramento), e botão "Reativar" (sem confirmação — ação reversível, não destrutiva) pra quem já está excluído. O par `.modal-overlay`/`.modal-content` é definido localmente no `<style>` da própria página (replicando o padrão de `beneficios/form.html`/`cras/form.html`, 2026-08-13) — **não** existe global em `app.css`, então não copiar essas classes achando que já existem em algum outro lugar sem checar (foi exatamente esse tipo de suposição que causou o bug do modal "Delegar Visita" usando classes Tailwind inexistentes em 2026-08-17).
- Testado via Django test client (`apps/accounts/tests.py::UserDeactivateReactivateViewTests`: admin-only, bloqueia auto-exclusão, usuário desativado não loga mais, reativação restaura login, notificação gerada, badge/botão certos no HTML) **e** com navegador real (login como admin temporário, abrir modal, confirmar exclusão, checar badge "Excluído" + botão "Reativar" aparecendo, reativar, checar volta pra "Ativo", captura de tela confirmando estilo do modal idêntico ao padrão do sistema, botão "Excluir" ausente na própria linha do admin logado) — contas de teste criadas e removidas do banco de dev na mesma sessão, sem deixar resíduo.

---

## Aviso de sucesso/falha ao delegar visita — 2026-08-24

Pedido explícito do usuário, testado em Emendas e Fundos (a view é compartilhada por Subvenção/Emendas/Outros, então o fix vale pra qualquer uma): "quando eu clicar como admin delegar e selecionar um usuário, ele deve dizer se foi delegado com sucesso ou se deu falha". `VisitDelegateView.post()` (`apps/directorates/views.py`) nunca dava nenhum feedback antes — só um `redirect` silencioso após deletar+recriar os `FormDelegation` — então um admin não tinha como saber se a delegação realmente funcionou (gap já identificado na investigação do bug de 2026-08-20, mas fora de escopo naquele momento).

- Os IDs marcados no modal agora são validados contra `Profile` de verdade antes de gravar (`Profile.objects.filter(pk__in=submitted_ids)`) — protege contra um POST adulterado com um UUID que não corresponde a ninguém; se nenhum dos IDs enviados for válido, a view nem chega a apagar as delegações existentes, só reporta erro (`messages.error`) e retorna.
- O delete+recreate roda dentro de `transaction.atomic()` — se a recriação falhar no meio (`DatabaseError`), a visita nunca fica sem NENHUMA delegação por causa de uma falha parcial; o erro é logado (`logger.exception`) e reportado via `messages.error`.
- Sucesso mostra quem recebeu a delegação pelo nome (`"Visita delegada com sucesso para: {nomes}."`); enviar o formulário sem nenhum técnico marcado é o jeito já existente de **limpar** as delegações de uma visita (comportamento pré-existente, não é falha) — vira uma mensagem de sucesso distinta ("Delegações removidas desta visita.").
- Nenhuma mudança de template/JS foi necessária — `messages.success`/`messages.error` já renderizam como toast global em qualquer página via `templates/base.html` (`#globalToastStack`), então o aviso aparece automaticamente após o redirect que a view já fazia.
- Testado via Django test client (`apps/directorates/tests.py::VisitDelegateViewTests` — sucesso com nome do delegado, limpar delegações mostra mensagem de remoção, UUID inexistente reporta erro e não cria `FormDelegation` fantasma) e com navegador real numa diretoria "Emendas e Fundos" de verdade (login admin temporário, abrir "Instrumental de Visita", clicar no ícone "Delegar" de um card, marcar um técnico, salvar, capturar o toast verde "Sucesso — Visita delegada com sucesso para: ..." na tela) — dados de teste (visita/OSC/usuários) criados e removidos do banco de dev na mesma sessão.

## Modal "Delegar" pré-marca quem já está habilitado + ícone de "Delegada" no card — 2026-08-24

Dois pedidos explícitos do usuário na mesma leva: "ao delegar, a lista de delegar [deve] mostrar quem está habilitado, para ao desmarcar, revogar o acesso de quem está marcado" e "crie no card algum ícone pequeno indicando que aquela visita está delegada a alguém".

- `VisitDelegateView.post()` já suportava revogar (o delete+recreate a partir do que estiver marcado no POST já removia quem for desmarcado) — o que faltava era o modal **mostrar** o estado atual antes de editar. `openDelegateModal(visitId, oscName, delegatedIdsStr)` (JS, nos 3 templates com o modal) ganhou um 3º parâmetro: uma string de UUIDs separados por vírgula, usada pra pré-marcar os checkboxes certos depois do `.reset()` — evita colchetes/aspas duplas dentro de um atributo `onclick` (que já usa aspas duplas), então optou por vírgula + `.split(',')` em vez de tentar embutir um array JSON.
- Novo helper `build_delegation_map(visits)` (`apps/directorates/views.py`, mesmo padrão de `build_registered_by_map`) — uma query `FormDelegation.objects.filter(visit_id__in=...)` pra todas as visitas da página de uma vez, evitando N+1. Alimenta `visit.delegated_user_ids_str` (pro JS) e `visit.is_delegated` (pro template) nos 3 pontos que renderizam cards de visita: `VisitListView`, `MonitoringReportListView` (`apps/directorates/views.py`) e `MonitoramentoHomeView` (`apps/monitoramento/views.py`, precisou importar o helper novo).
- Indicador visual: pill pequena "DELEGADA" (ícone `users-round`, cor índigo `#4338ca`) — em `visit_list.html` fica ao lado do "registrado por" (reaproveita o padrão de pill já usado ali); em `_tab_content.html`/`report_list.html` vira mais uma linha `.visit-meta-row`/`.report-tech-row` (reaproveita o padrão de ícone+texto já usado pra data/plano/técnicos), com a classe nova `.visit-meta-delegated` sobrepondo a cor cinza padrão. **Decisão de layout**: cheguei a tentar um badge circular `position:absolute` no canto superior direito do card, mas descartei antes de subir pro navegador — nomes de OSC longos (2 linhas, `-webkit-line-clamp:2`) podiam ficar por baixo do badge fixo; a pill inline evita esse risco de sobreposição.
- `visit.osc.name` nos 3 `onclick="openDelegateModal(...)"` ganhou `|escapejs` (não tinha antes) — um nome de OSC com aspas simples (ex. "Instituto D'Ávila") quebraria o JS inline; achado ao mexer nessa mesma linha, não uma regressão nova.
- Testado via Django test client (`apps/directorates/tests.py::VisitDelegationContextDataTests` — contexto marca/não marca `is_delegated` corretamente, `delegated_user_ids_str` lista múltiplos IDs, e desmarcar de fato revoga) e com navegador real em "Emendas e Fundos": delegar → recarregar lista → pill "DELEGADA" aparece no card → reabrir modal → checkbox já vem marcado → desmarcar e salvar → mensagem "removidas" → pill some do card de novo. Screenshot confirmou o visual da pill.

---

## Bug real de navbar corrigido — "tela trêmula" em tablets (2026-08-24)

Usuário reportou, na mesma leva de pedidos acima: "no modo tablet, quando entro em emendas e fundos e Instrumental de visitas, a tela acima da div da lista das visitas fica toda trêmula, aparentemente bugada... isso é só em tablet, e testei em 2 na produção".

**Investigação** (não assumi nada por leitura de CSS só — medi de verdade num navegador com viewport de tablet real, `browser-automation` skill): a suspeita inicial (jank de `backdrop-filter`) foi descartada (`.subvention-top-tabs` já neutraliza `backdrop-filter`/`box-shadow` em telas de tablet, confirmado via `getComputedStyle` ao vivo). A causa real, achada varrendo `document.documentElement.scrollWidth` em vários larguras: **em QUALQUER viewport entre 1025px e ~1904px, a página tinha 700-800px de overflow horizontal** — o menu desktop (`.nav-main`, `partials/navbar.html`) é um item flex (`flex:1`) sem `min-width:0`, então o navegador nunca encolhe ele de verdade; ele simplesmente vaza pra fora da tela em vez de encolher. Esse intervalo (1025-1904px) cobre **exatamente** paisagem de tablet — iPad landscape (~1024-1194px), a maioria dos Android landscape (1080-1200px) — batendo com "só em tablet" e "testei em 2 tablets". Já existia uma nota antiga (CLAUDE.md, 2026-08-17) mencionando esse overflow só a 1440px e marcada "fora de escopo, não mexido" — a extensão real do bug (toda a faixa 1025-1904px, não só 1440px) nunca tinha sido medida antes.

**Decisão consultada com o usuário** (2 caminhos possíveis, ambos com trade-off): estender o breakpoint do menu mobile/hambúrguer (já existe e funciona, mas muda a navbar em notebooks/desktops menores que 1920px também) vs. fazer o menu desktop encolher de verdade (não muda notebooks, mas exige mais trabalho/teste de CSS). Usuário escolheu **estender o menu mobile**.

- `partials/navbar.html`: os 2 breakpoints irmãos que ligam/desligam o modo mobile-vs-desktop (`@media (max-width: 1024px)` → menu hambúrguer, `@media (min-width: 1025px)` → esconde o botão hambúrguer e troca a navbar pro modo transparente/`position:absolute` que flutua sobre o banner colorido) foram movidos juntos pra **1919px/1920px**. Eram exatamente o mesmo tipo de bug já documentado nesse arquivo (duas regras pro mesmo breakpoint divergindo com o tempo) — só que dessa vez, se eu tivesse movido só uma das duas, o botão de menu inteiro teria sumido na faixa 1025-1919px (confirmado ao vivo antes de corrigir: `.mobile-toggle` ficava `display:none` mesmo com `.nav-main` já escondido, deixando a navbar sem NENHUMA forma de abrir o menu).
- **`app.css`** (1 ocorrência) e **18 arquivos de template** tinham `@media (min-width: 1025px) { .dashboard-main / .locked-month-warning / .benefits-shell { padding-top / margin-top ... } }` — essa compensação só faz sentido enquanto a navbar realmente estiver no modo `position:absolute` (removida do fluxo normal do documento); todas movidas pra 1920px junto, senão páginas nessa faixa ganhariam ~80-96px de espaço em branco extra em cima de uma navbar que já é `sticky` (ocupa o próprio espaço no fluxo) nesse intervalo. Lista completa: `accounts/user_create.html`, `accounts/user_list.html`, `accounts/user_permissions.html`, `core/settings.html`, `core/notifications.html`, `core/map_management.html`, `beneficios/form.html`, `casamulher/form.html`, `ceai/data_list.html`, `ceai/update_data.html`, `creasidoso/form.html`, `cras/form.html`, `monitoramento/shared/form.html`, `naica/form.html`, `poprua/data_list.html`, `poprua/form.html`, `protecaoespecial/form.html`, `sinecp/shared/form.html`.
- **Não mexido de propósito**: outras ~6 ocorrências de `@media (max-width: 1024px)` (`monitoramento/home.html` grid de planos, `directorates/detail.html`, `directorates/monitoring/report_list.html`/`osc_form.html`/`visit_instrumental.html`, `accounts/user_permissions.html` grid de formulário) são breakpoints de layout de COMPONENTE (colunas de grid, largura de container) independentes do liga/desliga da navbar — não têm o mesmo risco de conteúdo escondido/sobreposto, só uma proporção visual um pouco diferente nessa faixa, então não foram tocadas pra não inflar o escopo dessa correção além do que foi pedido/confirmado.
- Testado ao vivo (não só lendo CSS) em várias larguras (1024/1080/1200/1440/1700/1900/1920/2000px) e em várias páginas (Emendas e Fundos, `accounts/user_list.html` sem banner próprio): overflow horizontal = 0 em todas; botão hambúrguer aparece e o menu realmente abre (testado clicando de verdade, 6 links renderizados) na faixa 1025-1919px; navbar desktop tradicional continua idêntica a partir de 1920px; título/conteúdo de páginas sem banner (`user_list.html`) não fica escondido atrás da navbar. Screenshots confirmaram visualmente os 3 modos (tablet/hambúrguer aberto, tablet/fechado, desktop 1920px).

---

## Ícone "Descrição do plano" no Plano de Trabalho (Subvenção e Emendas e Fundos) — 2026-08-24

Pedido explícito do usuário: um ícone/botão associado a cada plano de trabalho que abre um modal "Descrição do plano de trabalho" com 4 campos de texto (Objeto, Objetivos, Metas estabelecidas, Atividades) — os mesmos 4 itens que já aparecem pré-preenchidos no "Relatório de Visita" (etapa habilitada ao finalizar o Instrumental de Visita), puxados por OSC/plano.

**Descoberta ao investigar**: o backend inteiro já existia e já funcionava — `WorkPlan.objeto/objetivos/metas/atividades` (campos reais no model desde 2026-07), `WorkPlanObjectivesView` (salva os 4 campos, sem nenhum branch por diretoria), `get_visit_report_texts()` e `VisitReportView` (herdam do plano vinculado à visita, com fallback pros textos da OSC — também sem branch por diretoria). O que faltava era só a **UI** para Subvenção: Emendas e Fundos já tinha um ícone "Objeto e descrição dos objetivos" no Plano de Trabalho desde 2026-07, mas Subvenção nunca ganhou o equivalente.

- Pedido inicial era só "Somente em Subvenção" — implementado um modal novo (`templates/directorates/monitoring/partials/work_plan_description_modal.html`) com o texto exato pedido (título "Descrição do plano de trabalho", campos "Objeto"/"Objetivos"/"Metas estabelecidas"/"Atividades", sem os prefixos legais "A)/B)/C)" que o texto de Emendas usava), reaproveitando 100% a `WorkPlanObjectivesView` existente (endpoint `directorates:plan-objectives`) — zero mudança de backend.
- **No meio da implementação, o usuário reportou**: "já existe um botão lá [Emendas], mas não abre essas opções" — pediu pra estender o recurso pra Emendas e Fundos também. Investigação ao vivo (não só leitura de código): o modal antigo de Emendas (`plan_objectives_modal.html`, JS `openPlanObjectives()`) **abriu normalmente** num plano novo/vazio criado pra teste — não foi possível reproduzir a causa raiz do "não abre" relatado em produção com dados de teste simples (suspeita não confirmada: algum caractere especial num plano real quebrando o `data-*` attribute, ou alguma condição de estado específica da produção). Em vez de caçar um bug não-reproduzível, a decisão foi **unificar**: o botão de Emendas passou a abrir o MESMO modal novo (`openWorkPlanDescription()`), e o modal antigo (`plan_objectives_modal.html`) foi **removido do projeto** — não sobrou nenhum código morto/duplicado, e o texto do modal ficou padronizado entre as duas diretorias (perdendo os prefixos "A)/B)/C)" que só Emendas tinha).
- Implementado em **4 lugares** (as duas superfícies que listam Plano de Trabalho, cada uma com Subvenção+Emendas): `templates/directorates/monitoring/plan_list.html` (página avulsa) e `templates/monitoramento/_tab_content.html` (aba "Plano de Trabalho" do dashboard `monitoramento:home?tab=plans`) — cada uma tinha sua própria estrutura HTML pro branch Emendas (múltiplos planos por OSC, `{% for plan in osc.work_plans.all %}`) vs. Subvenção (só o `latest_plan`), então o ícone novo precisou ser adicionado nos dois branches, nas duas páginas.
- **CSS auto-contido no partial** — mesma lição já aprendida nesta sessão duas vezes antes (bug do Tailwind no modal Delegar, 2026-08-17): as classes `.plan-objectives-*` usadas pelo modal só existiam dentro do `<style>` local de `plan_objectives_modal.html`, nunca em `app.css`. Copiadas pro novo partial antes de qualquer teste, evitando reintroduzir o mesmo tipo de bug (modal sem estilo nenhum).
- Testado via Django test client (`apps/directorates/tests.py::WorkPlanDescriptionSubvencaoTests` — botão aparece com o texto certo em Subvenção E Emendas, `WorkPlanObjectivesView` salva os 4 campos pras duas, e o fluxo completo "preencher a descrição do plano → abrir Relatório de Visita → ver os 4 textos pré-preenchidos" foi confirmado ponta a ponta pras duas diretorias) e com navegador real nas 4 superfícies (`plan_list.html`/`_tab_content.html` × Subvenção/Emendas): ícone, título do modal, rótulos dos 4 campos, salvar, reabrir com os valores persistidos, e — o mais importante — o texto salvo realmente aparecendo pré-preenchido no formulário real do "Relatório de Visita" (`report_form.html`, campos `#pt-objeto-relatorio` etc.) de uma visita vinculada àquele plano. Zero erros de console em todas as combinações.

---

## Três correções em Monitoramento (Subvenção/Emendas e Fundos) — 2026-08-27

Leva de 3 pedidos do usuário na mesma sessão:

**1. Indicador de diretoria de quem registrou a visita, admin-only**: nos cards de "Instrumental de Visita" (`visit_list.html` e a aba inline de `monitoramento:home?tab=visits`), pedido explícito: "dizer de qual diretoria é a pessoa que enviou aquela visita... isso vai servir só para controle de quem é administrador". Novo helper `build_registered_by_directorate_map(visits)` (`apps/directorates/views.py`, mesmo padrão de `build_registered_by_map`/`build_delegation_map` — uma query em lote via `Profile.objects.filter(user_id__in=...).select_related("primary_directorate")`, evita N+1) alimenta `visit.registered_by_directorate` (nome da `primary_directorate` do perfil de quem criou a visita, ou `None` se não tiver — mostrado como "Sem diretoria"). **Importante**: é a diretoria PRIMÁRIA DO PERFIL de quem registrou, não a diretoria da própria visita — podem divergir (ex.: um técnico vinculado a mais de uma diretoria, ou uma visita antiga cujo autor mudou de diretoria depois). Pill nova (ícone `building-2`, cor âmbar `#b45309`) gated por `{% if is_admin_user %}` nos dois templates — diretor/agente nunca veem. Gotcha achado escrevendo o teste: `assertNotContains(response, "registered-by-directorate-pill")` dava falso positivo porque o NOME da classe CSS aparece sempre no `<style>` da página (`.registered-by-directorate-pill { ... }`), independente do gate — o teste certo verifica o VALOR renderizado (nome da diretoria), não a classe.

**2. Quantidade de "Lista de Espera" sumia do documento/PDF finalizado**: bug real reportado pelo usuário (Emendas e Fundos, mas a view/template são compartilhados com Subvenção) — o campo `atendimento.lista_espera_quantidade` aparecia no formulário enquanto rascunho, mas nunca tinha sido adicionado nem em `visit_document.html` (view HTML do documento finalizado) nem em `pdf_documents.py` (export `?export=pdf`, ReportLab separado, não usa `SystemDocTemplate`). Adicionado um card/linha condicional "Lista de Espera: N pessoas" em ambos, só quando `atendimento.lista_espera == 'sim'` — mesma condição já usada no formulário de edição pra mostrar o campo de quantidade. Testado com `PyMuPDF` (`fitz`, já instalado) extraindo texto do PDF real gerado, confirmando o texto aparece no arquivo binário, não só no HTML.

**3. Bug real corrigido: reverter visita não resetava o Relatório de Visita**: usuário relatou que ao reverter o Instrumental (`VisitRevertView`) pra rascunho e finalizar de novo, o Relatório de Visita (`parecer_tecnico`) reaparecia direto como finalizado (estado antigo preservado) em vez de voltar como rascunho — "preciso que configure que ao reverter, ele tornará os 2 relatórios como rascunho, e o de visita só liberado quando finalizar o primeiro seguindo a regra normalmente". Causa raiz: `VisitRevertView.post()` só resetava `visit.status`, nunca `visit.parecer_tecnico['status']`. Corrigido com o mesmo padrão já usado por `RevertReportView` (pra `relatorio_final`/`parecer_conclusivo`) — só troca a chave `status` pra `'draft'`, preserva todo o conteúdo já digitado no parecer_tecnico. A regra "só libera o Relatório de Visita quando o Instrumental for finalizado" já era garantida pela UI (`visit.status != 'finalized'` esconde o link do Relatório de Visita nos cards, mostrando só "Editar Instrumental") — não precisou de nenhuma mudança adicional de gate, só o reset de estado. Testado com Django test client e confirmado com um clique real no botão "Reverter para Rascunho" via navegador — checado direto no banco que as duas colunas (`status` e `parecer_tecnico.status`) voltaram pra `draft` juntas.

Testado via Django test client (`apps/directorates/tests.py`: `VisitCardRegisteredByDirectorateTests`, `VisitDocumentWaitingListTests`, `VisitRevertViewTests`) e com navegador real numa visita de Emendas e Fundos criada por um agente com diretoria primária diferente (Benefícios) — confirmado visualmente: pill "BENEFÍCIOS SOCIOASSISTENCIAIS" no card, card "LISTA DE ESPERA — 9 pessoas" no documento finalizado (screenshot), e o revert real resetando os 2 status no banco.

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

Ajustes em 2026-08-13 (Benefícios, SINE/CP, CRAS): confirm() nativo do navegador no envio do formulário trocado por modal no estilo do sistema (mesmo padrão `.modal-overlay`/`.modal-content` do CEAI) em `beneficios/form.html` e `cras/form.html` — o formulário de SINE/CP (`sinecp/shared/form.html`) já usava um modal próprio, não precisou de mudança. `beneficios/form.html` ganhou também um modal de seleção de mês/ano de referência ao entrar no formulário, e teve a classe `dashboard-fit-vh` removida (mesmo bug de página sem rolagem já documentado no CEAI — o formulário tem 26+ campos, mais alto que 100vh). Dois campos calculados passaram a ser recomputados automaticamente (ao vivo via JS + sempre reforçado no `clean()` do form no servidor, ignorando qualquer valor adulterado vindo do cliente): `beneficios_reports.total_visitas` (soma de 5 campos de visita) e `qualificacao_reports.resumo_taxa_ocupacao` (vagas ocupadas ÷ vagas oferecidas × 100 — fórmula confirmada com o usuário, documentada em `docs/dominio/02-tabelas-por-diretoria.md` seção B.7).

**RMA sumindo em "Ver Dados" na VPS (2026-08-13) — resolvido e já deployado**: causa raiz era `CrasDataView.get_context_data()` montando `rma_data` numa segunda passagem independente da queryset (last-write-wins) divergindo do dict `reports` (first-write-wins) sempre que existe linha duplicada por unidade/mês normalizados — achado um caso real na VPS (CAMPO ALEGRE/jul-2026: resíduo Title Case da era Supabase sem `rma_url` coexistindo com a linha atual em CAIXA ALTA com o PDF certo). Checada a tabela `cras_reports` inteira na VPS — era o único caso, não é um problema espalhado. Corrigido fazendo `rma_data` derivar do `reports` já deduplicado (commit `de15ba1`, deploy confirmado: badge aparece e PDF baixa, HTTP 200).

**Anexar RMA direto em "Ver Dados" (2026-08-13)**: além do formulário mensal, admins agora conseguem anexar/substituir o PDF do RMA direto na tabela "Ver Dados" do CRAS (mesmo padrão de quick-edit inline já existente para os campos numéricos). Novo endpoint `CrasQuickEditRmaView` (`cras:quick-edit-rma`, `allowed_roles=["admin"]`) reaproveita a mesma lógica de upload de `CrasCreateUpdateView.form_valid()` (mesmo esquema de path `rma/<directorate_pk>/<unit_name>/<year>_<month>_<uuid8>.ext` em `default_storage`), valida extensão `.pdf` no servidor (o formulário principal não validava isso, só tinha o `accept=".pdf"` do HTML), e faz `get_or_create` do relatório se ainda não existir um para aquele mês/unidade. Célula da tabela (`templates/cras/data.html`) ganhou um botão de upload/substituir ao lado do link do PDF, só visível pra admin.

**Página de Notificações + dropdown "Dashboard" na navbar (2026-08-13)**: o item "Dashboard Diretorias" da navbar (link direto) virou um `nav-group` com seta (mesmo padrão hover/`chevron-down` de "Diretorias"/"Monitoramento"/"Mapas"), com dois itens: "Dashboard Diretorias" (TV, inalterado) e "Notificações" (novo). A nova página (`core:notifications-list`, `NotificationsListView` em `apps/core/views.py`, `templates/core/notifications.html`) reaproveita o mesmo `ActivityLog`/`ACTION_VERBS` do sininho (`apps/core/notifications.py`), mas mostra o histórico completo dos últimos 30 dias (não só as não lidas) **agrupado por dia** (`itertools.groupby` sobre a queryset já ordenada por `-created_at` — funciona porque dias consecutivos ficam contíguos numa ordenação decrescente de timestamp), com rótulo "Hoje"/"Ontem" ou data por extenso pros dias mais antigos. Mesmo gate de admin do sininho (`RoleRequiredMixin`, `allowed_roles=["admin"]`), mas como página cheia (403), não JSON. Sem paginação/filtro de data ainda — se a janela de 30 dias precisar ser ajustável no futuro, é só expor `window_days` como query param.

**Leva grande de correções em Visita/PSE/Plano de Trabalho/Relatório Final — Subvenção e Emendas e Fundos (2026-08-16)**: usuário mandou uma lista de ~17 itens (bugs + features) pro módulo de monitoramento (`apps/directorates`); mapeado tudo no código antes de mexer (Explore agent + leitura manual), item por item confirmado/organizado com o usuário antes de implementar. Mudanças:
- **Colaboradores/RH no relatório finalizado** (`visit_document.html`, `pdf_documents.py`): linhas em branco não aparecem mais (mesmo padrão de filtro já usado no PSE Qualitativos); tabela agora mostra as colunas reais do formulário (Terceirizado/Outros/Subvenção/Nomes-Observações) em vez de uma coluna "Voluntário" que nunca existiu no schema e nunca mostrava os nomes.
- **PSE Qualitativos** (`report_form.html`, `parecer_tecnico`): virou de tabela fixa de 4 linhas pra add/remove dinâmico (`addQualRow`/`removeQualRow`, JS lê o DOM em vez de índice fixo `qual-data-0..3`); padding no servidor (`views.py`) mudou de "exatamente 4" pra "pelo menos 1".
- **PSE Quantitativos no relatório finalizado**: antes não aparecia em lugar nenhum (nem HTML nem PDF) — adicionado em `visit_document.html` e `pdf_documents.py` (`_atendimento_quant_table`).
- **PSE Quantitativos — tabela central por OSC**: `Osc.pse_quantitativos` (JSONField novo, `pending_alters.sql`) guarda os dados acumulados; `merge_osc_pse_quantitativos()` sobrepõe a central na visita ao carregar (existente via `get_object()`, nova via `json_script` + JS `updatePseQuantitativos()` no `change` do select de OSC — não dá pra usar contexto de servidor porque a OSC só é escolhida no cliente); `write_back_osc_pse_quantitativos()` grava de volta (merge por mês/indicador, nunca overwrite cego) toda vez que a visita salva. Regra combinada com o usuário: por enquanto qualquer visita pode editar qualquer mês (sem trava); se precisar travar meses de visitas já finalizadas no futuro, é uma regra nova a adicionar em cima disso.
- **Cabeçalho institucional + logo dinâmica no PDF** (`apps/core/pdf.py`): `SystemDocTemplate` ganhou uma linha institucional ("PREFEITURA DE UBERLÂNDIA - SECRETARIA...") acima do título; logo trocou de `static/img/logo.png` fixo pra `SystemSetting.logo_url` (mesma fonte que a navbar usa), resolvido uma vez por documento em `_resolve_logo_reader()` (aceita path estático ou URL externa).
- **Relatório Final — "1. Dados da Parceria"**: label do valor autorizado agora é dinâmico ("...para o exercício de {ano}", lendo `system_reference_year`); campo "Anotações" novo (só aparece no relatório finalizado se preenchido). Item "4." renomeado e reorganizado: a) Objetivos, b) Metas (sem o sub-campo "Quantitativas", removido), **c) Das atividades (novo campo)**, d) Resultados (renumerado de c), e) Execução financeira (label encurtado). Mudado em HTML, JS de coleta e PDF juntos.
- **Bug real achado e corrigido na impressão do Relatório Final**: uma imagem de assinatura corrompida/truncada derrubava o PDF inteiro com 500 — `_decode_data_url_image()` só validava o header da imagem (`ImageReader.getSize()`), não os pixels; o erro real só estourava depois, dentro de `doc.build()`, fora de qualquer try/except. Corrigido forçando decodificação completa via PIL (`Image.open(...).load()`) dentro do bloco protegido — imagem quebrada agora vira "sem assinatura" em vez de derrubar o PDF. Pillow virou dependência explícita (`requirements/base.txt`; já vinha transitivo do reportlab).
- **Turno da visita**: opção "Integral" removida do select (Subvenção + Emendas e Fundos, template compartilhado — um fix resolveu os dois).
- **Total/Mês vs. Total automático**: bug real — digitar a quantidade da manhã também recalculava o campo "Total/Mês" (que devia ser texto livre). Corrigido nos dois lados: `normalize_visit_attendance()` (`views.py`) não escreve mais em `atendimento.total_mes`, só em `atendimento.presentes.total` (novo); JS (`updateAttendanceTotal()`) idem, e o total exibido ganhou um `<input type="hidden">` de verdade (`presentes.total`) pra ser persistido — antes só existia como texto de exibição (`<strong>`), nunca era salvo.
- **Plano de Trabalho estendido pra Subvenção**: já existia (desde 2026-07-20) só pra Emendas e Fundos por causa da flag `is_emendas_directorate`. A flag `is_subvencao_directorate()` já cobre Subvenção+Emendas (nome meio enganoso, mas é assim desde sempre) — trocando as checagens de `is_emendas_visit`/`is_emendas_directorate` por `is_subvencao_visit`/`is_subvencao_directorate` nos pontos certos (`views.py` e `visit_instrumental.html`) estendeu o recurso inteiro (dropdown + herança de Objeto/Objetivos/Metas/Atividades) sem duplicar lógica.
- **PDF de anexo em Relatórios e Pareceres dando erro**: mesma causa raiz do bug do RMA do CRAS (corrigido em 13/08) — `VisitUploadNotificationView` usava URL crua `/media/notifications/...`, que só funciona com `DEBUG=True`. Trocado pra `default_storage` + `core:protected-media`.
- **Nome do técnico em maiúsculas nas assinaturas**: reforçado no servidor em 3 pontos (`VisitReportView.post()` pro JSON de parecer/relatório, e os dois parsers de `assinaturas[...]` em `VisitCreateView`/`VisitInstrumentalView`) — qualquer chave terminada em `_nome` vira maiúscula ao salvar, não só via JS. `signature_block()` (`apps/core/pdf.py`, compartilhada por todos os PDFs) também força maiúsculo na hora de desenhar, cobrindo dados antigos já salvos em minúsculo/misto.

Testado com um fluxo completo via Django test client (criar visita → finalizar → ver documento → exportar PDF → preencher parecer técnico → preencher e finalizar relatório final com assinatura de verdade → exportar PDF) e com navegador real pros pedaços mais JS-pesados (add/remove linha, total/mês, dropdown de plano). Ver `docs/dominio/02-tabelas-por-diretoria.md` pra detalhe da regra da tabela central de PSE.

**Item extra achado depois (mesma leva, 2026-08-16)**: a tabela de Qualitativos do PSE existe em DOIS lugares — no Parecer Técnico (`report_form.html`, já corrigido acima) e também no próprio formulário de preencher a visita (`visit_instrumental.html`, seção "Dados PSE"), que também estava fixo em 4 linhas (`{% for row in "1234" %}`). Corrigido do mesmo jeito (`addPseQualRow`/`removePseQualRow`, `pseQualTableBody`) — mas aqui os inputs já usavam `name="atendimento[pse_qualitativos][N][campo]"` direto (parseado genericamente por índice em `views.py`), então nem precisou de um array JS espelho como no Parecer Técnico, só anexar `<tr>` novo com o próximo índice.

**Botão "Sair" do Relatório Final/Parecer Conclusivo voltando pro lugar errado (2026-08-16)**: `VisitReportView.get_context_data()` usava `get_visit_list_redirect(directorate)` como fallback de `return_url` pros 3 tipos de relatório igual — isso manda pra aba "Instrumental de Visita" (ou "overview" pra admin) da `monitoramento:home`, não pra aba de onde normalmente se abre esses relatórios. Corrigido: quando `report_type` é `relatorio_final` ou `parecer_conclusivo` **e** a diretoria é Subvenção/Emendas e Fundos (`is_subvencao_directorate`), o fallback vira `monitoramento:home?tab=reports` ("Relatórios e Pareceres"). `parecer_tecnico` continua voltando pra "Instrumental de Visita" (não foi pedido, e faz sentido diferente — é um documento de trabalho, não um dos "Relatórios e Pareceres" finais). "Outros" não tem aba de Relatórios e Pareceres, então não é afetado (`is_subvencao_directorate` já exclui esse caso).

**Gotcha adicional descoberto ao criar a página**: `partials/navbar.html` tem uma regra `.dashboard-main { padding-top: 0 !important; }` (desktop, `>=1025px`) pensada só pra páginas com banner colorido próprio que já compensam a navbar (`position:absolute` no desktop) por conta própria — CRAS, Benefícios, SINE-CP. Qualquer página nova com `<main class="dashboard-main">` "puro" (sem banner) precisa **reafirmar** `padding-top: 80px !important` no próprio `<style>` da página (mesmo padrão já usado em `accounts/user_list.html`) — senão o título fica escondido atrás da navbar, exatamente como aconteceu na primeira versão de `core/notifications.html` (corrigido antes do deploy).

**Permissões de visita em Monitoramento verificadas (2026-08-16)**: usuário suspeitava que diretor/agente estavam vendo todas as visitas por causa de dados migrados órfãos de `user_id`. Investigado a fundo (leitura de código + simulação de login real via `Client.force_login` + 2 visitas de teste criadas na hora) — hipótese **falsa**: zero visitas com `user_id` nulo/órfão em Subvenção ou Emendas e Fundos, e a filtragem já implementada em `VisitListView`/`MonitoramentoHomeView` já faz exatamente o esperado (diretor vê 100% da própria diretoria; agente vê só o que é seu ou o que foi delegado; admin vê tudo). Nenhuma mudança de código nessa parte — só confirmação. Ver `docs/dominio/04-visitas-subvencao-emendas-fundos.md` A.6/B.6/B.3 (regra já documentada desde 2026-07-25).

**Bug real encontrado e corrigido no mesmo levantamento — modal "Delegar" completamente quebrado**: `templates/directorates/monitoring/visit_list.html` (checkbox de técnicos no modal "Delegar Visita") usava `value="{{ profile.id }}"`, mas o model `Profile` não tem campo `id` — a PK se chama `user` (`db_column="id"`, mas o atributo Python é `user`/`pk`, nunca `id`). O template renderizava esse valor como string vazia silenciosamente, e ao clicar "Salvar Delegações" a view (`VisitDelegateView.post()`) primeiro apaga as delegações existentes da visita e só depois tenta recriar — com `user_id=""` isso sempre resultava em **erro 500** (`ValidationError: "" não é um UUID válido`), então clicar em "Salvar" numa visita que já tinha delegação **apagava a antiga e travava sem salvar a nova**. Reproduzido de ponta a ponta via Django test client antes e depois da correção. Corrigido trocando pra `value="{{ profile.pk }}"` (mesmo padrão já usado em `accounts/user_list.html`). As 41 linhas de `form_delegations` que já existiam no banco (algumas em Subvenção/Emendas, datadas de junho/julho de 2026) são resíduo do sistema antigo (Next.js/Supabase, sincronizado no dump) — nunca foram criadas por esse modal no Django, que provavelmente nunca funcionou desde o rewrite. Nota separada: `directorate_id` em `form_delegations` é sempre `NULL` (a view nunca seta esse campo na criação) — inofensivo, porque nenhuma checagem de permissão filtra por ele (só por `visit_id`+`user_id`), mas é dado morto/enganoso se alguém for depurar olhando essa coluna.

**Delegar/Reverter viram exclusivos de admin + coluna "Ações" reorganizada (2026-08-16)**: pedido explícito do usuário — diretor e agente nunca deviam ter tido acesso a delegar visitas nem a reverter relatórios/instrumental (mesmo sendo dono da própria visita, que antes era uma exceção permitida). Mudanças:
- **Backend** (`apps/directorates/views.py`): `VisitDelegateView.dispatch()` (delegar), `VisitRevertView.dispatch()` (reverter o Instrumental inteiro pra rascunho, URL `visit-revert`) e `RevertReportView.dispatch()` (reverter `relatorio_final`/`parecer_conclusivo`, URL `visit-report-revert`) agora checam `is_superuser or role == "admin"` explicitamente — nenhuma exceção de "dono da visita" mais. `VisitRevertView` e `RevertReportView` trocaram a base de `VisitAccessMixin` (que tinha a lógica de dono) pra `VisitScopedMixin` (só escopo de diretoria) + guarda de admin manual, mesmo padrão que `VisitDelegateView` já usava.
- **Coluna "Ações"** (delegar/reverter/excluir) virou **allowlist de admin** — só renderiza pra quem tem `is_admin_user`/`can_delete`, tanto o `<th>` quanto o `<td>` de cada linha. Diretor e agente perdem a coluna inteira nas 2 tabelas de "Instrumental de Visita" (`templates/directorates/monitoring/visit_list.html`, standalone, e `templates/monitoramento/_tab_content.html`, aba inline de `monitoramento:home`) — continuam vendo Data/OSC, Plano de Trabalho, Técnicos, Status e Documentos (acesso ao próprio instrumental/relatório continua ali, só não editam/deletam/delegam/revertem mais pela lista). Colspan da linha "nenhuma visita" em ambas as tabelas passou a ser calculado no backend (`context["visit_table_colspan"]`, `VisitListView`/`MonitoramentoHomeView`) em vez de hardcoded no template, já contando a coluna condicional.
- **Botão "Delegar" (pessoas) adicionado em 3 lugares que não tinham** — pedido explícito ("são 2 botões de delegar... também ter um botão de delegar em cada card"): nos cards de "Relatórios e Pareceres" tanto na aba inline (`_tab_content.html`) quanto na página avulsa (`templates/directorates/monitoring/report_list.html`), e na tabela "Instrumental de Visita" inline de `_tab_content.html` (só a página avulsa `visit_list.html` já tinha). Todos com o mesmo modal "Delegar Visita" (checkbox de técnicos, reaproveitando `context["profiles"]`), gate `{% if is_admin_user %}`. `MonitoringReportListView.get_context_data()` ganhou `is_admin_user`/`profiles` (não existiam antes). Botão "Reverter para Rascunho" que já existia em `report_list.html` também virou admin-only (não tinha nenhum gate de role antes).
- **Bug pego só na QA visual, não no test client**: o modal "Delegar Visita" copiado pra `_tab_content.html`/`report_list.html` abria **sem nenhum estilo** (raw content no fim da página, sem overlay) — o CSS (`.modal-premium`/`.modal-premium-content`/`.modal-premium-header`/`.close-modal`) só existia num `<style>` local de `visit_list.html`, nunca em `static/css/app.css`. Django test client (`resp.content`) não pega isso porque é puro CSS, sem afetar HTML/lógica — só apareceu no agente de browser-automation. Corrigido movendo essas 4 regras pra `app.css` (compartilhado) e removendo a cópia local de `visit_list.html`. Nota: `templates/sinecp/shared/form.html` também define `.modal-premium-content`/`.modal-premium-header` (nomes de classe coincidentes, mas visual bem diferente — é outro modal, de confirmação de mês/ano) — como o `<style>` daquela página carrega depois do `app.css` e tem a mesma especificidade, a definição local dela continua vencendo ali (sem regressão), mas é um nome de classe compartilhado por acidente entre dois módulos diferentes — vale lembrar se mexer em qualquer um dos dois de novo.
- Testado com Django test client (matriz completa: admin/diretor/agente × 4 páginas × delegar/reverter/excluir, checando tanto se o botão renderiza no HTML quanto se o POST direto no endpoint dá 403 pra não-admin) e depois com navegador real (modal abre com nomes reais, sem erro de console, estilo correto nas 4 páginas after o fix de CSS).

**Diretor não deve ver visitas criadas por admin, mesmo dentro da própria diretoria (2026-08-17)**: achado real do usuário testando em produção — criou uma visita logado como admin (`klismanrds@gmail.com`, sem `primary_directorate` nem `ProfileDirectorate` nenhuma) em Subvenção, e um diretor vinculado a Subvenção (`klismanrds90@gmail.com`) enxergou essa visita numa outra sessão. Isso era o comportamento **já confirmado e testado** em 2026-08-16 ("diretor vê todas as visitas da própria diretoria") — mas o usuário esclareceu que a regra original ("visitas feitas pelos seus agentes da mesma diretoria") nunca quis dizer "todas, incluindo as do admin" — admin não é "agente". Refinamento, não reversão:
- Novo helper `get_admin_user_ids()` (`apps/directorates/views.py`) — `User.objects.filter(Q(is_superuser=True) | Q(profile__role="admin"))`, reutilizado nos 4 pontos abaixo.
- `VisitListView.get_queryset()`, `MonitoringReportListView.get_queryset()` (`apps/directorates/views.py`) e `MonitoramentoHomeView.get_context_data()` (`apps/monitoramento/views.py`): no ramo `diretor`, depois de confirmar `is_primary or is_linked`, agora faz `.exclude(user_id__in=get_admin_user_ids())` — diretor continua vendo 100% da própria diretoria, **exceto** visitas cujo criador é admin.
- `VisitAccessMixin.dispatch()`: fechado o mesmo buraco pro acesso direto por URL (não só a lista) — se `profile.role == "diretor"` e a visita foi criada por um admin (`visit.user_id` em `get_admin_user_ids()`) e o diretor não é o dono (nunca é, nesse caso), `403 Forbidden` mesmo em GET — antes diretor podia sempre visualizar (só não editar) qualquer visita da própria diretoria.
- Agente já não via essas visitas antes (seu filtro sempre foi só dono+delegado, nunca "toda a diretoria") — nenhuma mudança necessária nesse ramo.
- Testado via Django test client: visita criada por admin some da lista/dashboard/relatórios do diretor e dá 403 no acesso direto por URL; visita criada por um agente de verdade continua aparecendo normalmente pro mesmo diretor (a exclusão é só pra admin, não pra qualquer terceiro).

**Modal "Delegar Visita" reconstruído — usava classes Tailwind que não existem no projeto (2026-08-17)**: usuário mandou print mostrando o modal com ~55 checkboxes (um por perfil de usuário do sistema inteiro, incluindo contas de departamento tipo "CREAS RUA"/"BENEFICIOS") todos sem estilo, quebrando linha e vazando pra fora do card, sem caixa de busca. Causa raiz: o markup inteiro do corpo do modal (`p-6`, `space-y-4`, `max-h-40`, `overflow-y-auto`, `form-group`, `premium-label`, `text-xs`, `font-medium` etc.) usava nomenclatura estilo Tailwind, mas **este projeto nunca teve Tailwind** (sem CDN, sem build) — nenhuma dessas classes tinha definição em lugar nenhum, então o corpo do modal sempre renderizou com estilo zero do navegador. Só ficou visualmente óbvio agora porque a lista de perfis cresceu bastante desde que o modal foi feito originalmente. Reescrito com classes reais (`.delegate-modal-body`, `.delegate-search-wrap`, `.delegate-search-input`, `.delegate-tech-list` com `max-height:260px`/`overflow-y:auto` de verdade, `.delegate-tech-item`, `.delegate-tech-empty`, `.delegate-modal-footer`) adicionadas em `static/css/app.css`, aplicado de forma idêntica nos 3 templates que têm o modal (`visit_list.html`, `_tab_content.html`, `report_list.html`). Adicionado também um campo de busca por nome (`#delegateSearchInput`, JS `filterDelegateTechs()`) que filtra a lista ao vivo (case-insensitive, substring) e mostra "Nenhum técnico encontrado" quando zera — pedido explícito do usuário. `openDelegateModal()` agora também dá `.reset()` no form e reaplica o filtro (limpo) toda vez que abre, pra não carregar busca/checkboxes de uma visita anterior. Testado com navegador real: lista com scroll de verdade (`scrollHeight` bem maior que `clientHeight`), busca "kl" filtrou 56→3 nomes corretamente, sem erro de console.

**"Instrumental de Visita" (Subvenção/Emendas e Fundos) virou grade de cards — pedido explícito do usuário (2026-08-17)**: as duas superfícies que listam visitas (`templates/monitoramento/_tab_content.html`, aba inline de `monitoramento:home?tab=visits`, e `templates/directorates/monitoring/visit_list.html`, página avulsa) usavam `<table>` com `min-width` fixo (1040px e implícito via colunas rígidas) — em telas de tablet isso forçava rolagem horizontal (`.inline-visits-scroll { overflow-x:auto }`) ou escondia colunas inteiras via `.no-tablet { display:none }`, perdendo informação. Substituído por grid responsivo (`.visit-cards-grid { grid-template-columns: repeat(auto-fill, minmax(280-300px,1fr)) }`, mesma família visual de `.report-card` já usada em "Relatórios e Pareceres") — cada visita vira um `.visit-card` com todos os campos que já existiam (OSC, data, identificador, plano de trabalho, técnicos, status, documentos, ações), texto configurado pra quebrar linha (`overflow-wrap:break-word`, OSC com `-webkit-line-clamp:2`) em vez de truncar ou vazar. CSS novo em `templates/monitoramento/home.html` (compartilhado entre full-load e fragmento trocado via AJAX) e num `<style>` local de `visit_list.html`. Tabela antiga e todo CSS exclusivo dela removidos (`.inline-visit-table`, `.inline-visits-scroll`, `.table-monitoring`, `.no-tablet`, hack de "linha vira cartão" via `data-label::before` no mobile — ver commit anterior de 2026-08-13/f42d4b1, agora obsoleto) — `.inline-osc-table` (fora de escopo) não foi tocada. JS de busca (`#inline-visit-search` em `_tab_content.html`, `#osc-filter` em `visit_list.html` — esse último **nunca tinha JS ligado**, achado e corrigido de brinde) reescrito pra filtrar `.visit-card[data-osc]` em vez de linhas de tabela, mesmo padrão já usado pros cards de "Relatórios e Pareceres". Context var `visit_table_colspan` (não mais necessária sem `<table>`) removida de `VisitListView`/`MonitoramentoHomeView`.

**Bug achado só na QA visual (não no test client) durante essa rodada**: `.visit-header-actions { min-width: 760px }` na página avulsa (`visit_list.html`) forçava a barra de filtros a ficar larga demais em telas de tablet/mobile, causando rolagem horizontal *na página inteira* mesmo com os cards já responsivos — nada a ver com a grade em si. Corrigido com override dentro do `@media (max-width: 1366px)` já existente (`min-width:0; width:100%; flex-wrap:wrap`). Confirmado sem overflow em 390/820/1440px depois do fix. **Achado mas fora de escopo, não mexido**: `?tab=visits` do dashboard (`monitoramento:home`) tem overflow horizontal a 1440px causado pelo `<nav class="navbar">` em si (largo demais pro viewport) — pré-existente, afeta o navbar do app inteiro, não específico dessa página nem introduzido por essa mudança.

**Formulário "Nova Visita"/"Editar Visita" de Emendas e Fundos restaurado ao design original — regressão real do refactor de 16/08 (2026-08-17)**: usuário mandou prints + texto completo do formulário "correto" que Emendas e Fundos deveria ter, pedindo pra restaurar (**Subvenção não foi tocada**). Comparando com o código, a causa raiz ficou clara: o refactor de 2026-08-16 que estendeu "Plano de Trabalho" de Emendas pra Subvenção (ver entrada acima) trocou várias checagens de `is_emendas_visit` por `is_subvencao_visit` — mas como `is_subvencao_directorate()` sempre tratou Subvenção e Emendas como a mesma coisa (`"subvencao" in nome or "emenda" in nome or "fundo" in nome`), isso fez Emendas herdar por engano várias seções que eram só de Subvenção, e perder o bloco de campos que sempre foi só dela (o `{% else %}` de uma cadeia `{% if is_outros_visit %}...{% elif is_subvencao_visit %}...{% else %}...{% endif %}` virou código morto pra Emendas, nunca mais executado). Corrigido em `templates/directorates/monitoring/visit_instrumental.html` acrescentando `is_emendas_visit` (true só pra Emendas/Fundos, nunca pra Subvenção) nos pontos certos:
- **Seção Atendimento**: o bloco de 2 textareas "Tipos de atividades desenvolvidas"/"Atividades em execução" (só Subvenção) e o bloco original de 4 textareas ("Aplicação do Recurso...", "Resultados...", "Itens Identificados...", "Itens Não Identificados...", só Emendas) agora são mutuamente exclusivos de verdade; "Observações"/"Recomendações" embutidas no Atendimento voltaram a aparecer pra Emendas (ficavam escondidas pelo mesmo bug).
- **Balanço Financeiro** (upload de PDF) voltou a aparecer só pra Emendas (nunca existiu pra Subvenção, então nada mudou lá).
- **PSE (Habilitar PSE), "III. Forma de Acesso dos Usuários", "IV. Colaboradores" e a seção solta "V. Observações e Recomendações"** somem pra Emendas (essas nunca fizeram parte do design original dela) — continuam normalmente pra Subvenção. A seção "Fotos / Evidências" (que estava no mesmo bloco condicional do PSE) foi desacoplada num `{% if %}` próprio pra continuar aparecendo nas duas.
- **Campo "Identificador"** (texto livre, ex: "2024.001") virou editável na Identificação — esse campo já existia no modelo de dados e já era **exibido** nos cards de visita (`visit_list.html`/`_tab_content.html`, `identificacao.identifier`) desde antes, mas nunca tinha um `<input>` no formulário pra preenchê-lo (sempre aparecia "Sem identificador"). Como o parsing de `identificacao[...]` já é genérico (qualquer chave nesse formato cai automaticamente no JSON), só precisou do campo no HTML — zero mudança em `views.py`.
- **"Plano de Trabalho vinculado" virou botão condicional só pra Emendas**: antes era um `<select>` sempre visível (herdado do refactor de Subvenção). Agora, só aparece alguma coisa quando a OSC selecionada tem **2 ou mais** planos cadastrados — nesse caso surge um botão "Vincular Plano de Trabalho" que, ao clicar, revela o `<select>` no lugar (`revealWorkPlanSelect()`, JS). Com 0 ou 1 plano, nada aparece (o backend já resolve sozinho via `resolve_visit_work_plan()`, comportamento pré-existente). Pra Subvenção nada mudou — continua com o `<select>` sempre visível, mesmo código de antes. Coberto um caso de borda: se a visita já existe e não tinha plano vinculado mas a OSC hoje só tem 1 plano, um `<input type="hidden" name="work_plan" value="">` garante que o fallback de auto-vínculo do backend ainda seja acionado ao salvar (senão o campo simplesmente não seria enviado).
- **"Imprimir Relatório"** (visão de impressão do navegador, `printProfessionalReport()`) também recebeu o mesmo tratamento condicional pros 4 campos de Emendas (antes só sabia mapear os 2 campos de Subvenção — ficaria "Não detalhado" sempre) e a seção "Forma de Acesso do Usuário" some da impressão pra Emendas. De brinde, o loop de sincronização de checkboxes de Forma de Acesso (`syncFormToReport()`) ganhou guarda contra `null` — sem isso, imprimir uma visita de Emendas (ou "Outros", que já tinha esse mesmo problema antes, sem relação com essa mudança) quebraria com `TypeError` ao tentar ler um checkbox que não existe mais no DOM.
- Botão "Adicionar Visita" virou "Adicionar 2ª Visita" só pra Emendas (texto exato pedido pelo usuário); Subvenção mantém "Adicionar Visita".
- Testado com Django test client (renderização de Nova Visita e Editar Visita pras duas diretorias, cobrindo 0/1/2 planos de trabalho vinculados/não vinculados, e um POST real confirmando que `identificacao.identifier` e o vínculo automático de plano gravam certo no banco) e com navegador real (fluxo completo: selecionar OSC, botão de vincular plano aparecendo/revelando o select, preencher Identificador, conferência side-by-side de que Subvenção não mudou nada).

**Agente vê/edita visitas de colegas da mesma diretoria — só em Subvenção/Emendas e Fundos (2026-08-19)**: pedido explícito do usuário, refinando a regra de permissões de visita (ver `docs/dominio/04-visitas-subvencao-emendas-fundos.md` A.6): "somente em monitoramento, no caso em emendas e fundos e subvenção, as visitas criadas por um agente da mesma diretoria, pode ser visto e editado por outros agentes da mesma diretoria (semelhante ao que o Diretor vê)". Antes, um agente só via/editava a própria visita ou uma delegada via `FormDelegation` — visita de outro agente, mesmo na mesma diretoria, dava 403 até no GET. Diferente do Diretor (que só visualiza visita alheia, nunca edita — regra que continua igual), o agente ganha **edição completa** na visita de um colega, não só leitura. "Outros" fica de fora dessa regra nova (continua só próprias/delegadas), porque `is_subvencao_directorate()` (`apps/directorates/views.py`) já não bate com o nome "Outros" — reaproveitado como guarda em vez de checar o nome de novo. Mudança aplicada em 4 pontos, todos com a mesma exclusão de visitas criadas por admin (`get_admin_user_ids()`, já usada pro Diretor — admin não conta como "um agente"):
- `VisitAccessMixin.dispatch()` — acesso direto por URL (GET/POST); agente ganha um terceiro caminho de acesso (`is_directorate_peer`) além de dono/delegado, e como a fórmula de `can_edit` já era `is_admin or is_owner or not (profile.role == "diretor")`, o agente que entra por esse caminho novo já sai com edição completa automaticamente, sem precisar mexer nessa fórmula.
- `VisitListView.get_queryset()` (`directorates:visit-list`) e `MonitoringReportListView.get_queryset()` (`directorates:report-list`) — dentro de Subvenção/Emendas e Fundos, o filtro de agente vira o mesmo `.exclude(user_id__in=get_admin_user_ids())` já usado pro Diretor, em vez do antigo `Q(user_id=...) | Q(id__in=delegated_visit_ids)`.
- `MonitoramentoHomeView.get_context_data()` (`apps/monitoramento/views.py`) — mesmo tratamento em `dashboard_visits_qs` (aba "Instrumental de Visita"/"Relatórios e Pareceres" do dashboard).
- Testado com Django test client: `apps/monitoramento/tests.py` (`MonitoramentoAgentePeerVisibilityTests`, diretorias isoladas criadas na hora) e `apps/directorates/tests.py` (`VisitAccessMixinSubvencaoPeerTests`, contra a diretoria real com mais OSCs do banco de dev, que já é "Subvenção"). Um teste pré-existente (`test_visit_access_denied_for_agente_not_owner_not_delegated`) dependia implicitamente de `self.directorate`/`self.other_directorate` (as 2 diretorias reais com mais OSCs no dev, ambas do grupo Subvenção/Emendas) não terem essa regra — corrigido pra usar uma diretoria de fora do grupo (`self.non_subvencao_directorate`, novo helper em `DirectoratesTestBase`, resolvido dinamicamente via `is_subvencao_directorate()` em vez de nome fixo). As 3 falhas de `VisitDelegateViewTests` que aparecem na mesma suíte são débito técnico pré-existente, não relacionado — confirmado rodando a mesma suíte em `git stash` antes desta mudança. **[Ver correção do bug real que essa mudança introduziu, entrada de 2026-08-20 abaixo]**.

**Bug real reportado pelo usuário em produção — "delegar visita pra um agente parece não funcionar" (2026-08-20)**: causa raiz era uma regressão da mudança acima (2026-08-19). Nos 3 lugares que passaram a usar `.exclude(user_id__in=get_admin_user_ids())` puro pra dar visibilidade de diretoria inteira ao agente em Subvenção/Emendas e Fundos — `VisitListView.get_queryset()`, `MonitoringReportListView.get_queryset()` (`apps/directorates/views.py`), `MonitoramentoHomeView.get_context_data()` (`apps/monitoramento/views.py`) — essa exclusão virou **absoluta**: nem uma `FormDelegation` explícita conseguia furá-la. Isso quebrou justamente o caso de uso mais comum de delegação (um admin cria a visita e delega pra um agente preencher, já que "Cadastrar OSC"/criar visita continua acessível a admin em qualquer diretoria) — a visita ficava permanentemente invisível pro agente delegado em qualquer lista/dashboard, mesmo com o `FormDelegation` salvo corretamente no banco. `VisitAccessMixin.dispatch()` (acesso direto por URL) nunca teve esse bug — `is_delegated` sempre foi checado incondicionalmente ali — mas sem nenhum link/card apontando pra visita em lugar nenhum, o acesso direto era inatingível na prática (ninguém digita UUID de visita na mão). Corrigido trocando `qs.exclude(user_id__in=admin_ids)` por `qs.filter(Q(id__in=delegated_visit_ids) | ~Q(user_id__in=admin_ids))` nos 3 pontos — visita delegada continua visível mesmo quando quem criou foi um admin. Cobertura de teste: `test_agente_sees_admin_created_visit_when_delegated` (`apps/directorates/tests.py`) e `test_agente_sees_admin_created_visit_in_subvencao_when_delegated` (`apps/monitoramento/tests.py`).

Na mesma investigação, achados adicionais (não corrigidos ainda, fora do escopo do bug reportado — avaliar se vale endereçar numa sessão futura):
- `VisitDelegateView.post()` não dá nenhum feedback de sucesso/erro (`messages.success`/`messages.error`) — o admin não tem confirmação nenhuma de que a delegação foi salva além do redirect silencioso.
- O modal "Delegar Visita" (`visit_list.html`/`_tab_content.html`/`report_list.html`) nunca pré-marca os checkboxes de quem já está delegado na visita — `openDelegateModal()` só faz `.reset()` — então reabrir o modal numa visita já delegada mostra a lista vazia, sem indicar o estado atual.
- `context["profiles"]` do modal é `Profile.objects.all()` sem filtrar por diretoria — lista técnicos do sistema inteiro, não só da diretoria da visita.
- `FormDelegation.directorate_id` continua sempre `NULL` (já documentado como inofensivo — ver nota "Bug real achado e corrigido no mesmo levantamento" de 2026-08-16 acima).
- `VisitDelegateViewTests` (3 dos 4 testes) estavam quebrados desde 2026-08-16 (commit `191e915`, que restringiu delegar a admin-only) porque ainda logavam como `role="diretor"` esperando 302 — corrigidos nesta sessão pra usar admin como ator, e o teste de "diretor sem acesso à diretoria" foi trocado por um teste explícito de "diretor não pode mais delegar" (esse cenário de diretoria não se aplica mais, porque admin nunca é bloqueado por diretoria).

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
