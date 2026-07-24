# Gestaosuas Django

Sistema de Vigilância Socioassistencial da Secretaria Municipal de Desenvolvimento Social de Uberlândia-MG, em Django puro, conectado a um container PostgreSQL 15 Alpine standalone (Docker) — sem dependência do Supabase.

> Este README é uma introdução rápida. Para contexto completo (ambientes, deploy na VPS, convenções de código, débito técnico, etc.), ver [`CLAUDE.md`](CLAUDE.md). Para schema e regras de negócio, ver [`docs/dominio/`](docs/dominio/).

## Estrutura

| App | Responsabilidade |
|-----|-----------------|
| `apps/core/` | Layout, dashboard base, mapas, configuracoes, utilities compartilhadas |
| `apps/accounts/` | Autenticacao nativa Django (ModelBackend), perfis, permissoes |
| `apps/directorates/` | Diretorias, OSCs, visitas tecnicas, planos de trabalho, delegacoes |
| `apps/monitoramento/` | Subvencao, Emendas, Fundos e Outros (generico com OSCs/visitas) |
| `apps/beneficios/` | Beneficios Socioassistenciais |
| `apps/sinecp/` | Qualificacao Profissional e SINE |
| `apps/cras/` | CRAS (13 unidades) |
| `apps/ceai/` | CEAI (Centro de Educacao e Assistencia Infantil) |
| `apps/naica/` | NAICAs (11 unidades) |
| `apps/creasidoso/` | CREAS Idoso e Pessoa com Deficiencia |
| `apps/poprua/` | Populacao de Rua e Migrantes |
| `apps/protecaoespecial/` | Protecao Especial a Crianca e Adolescente |
| `apps/casamulher/` | Casa da Mulher / Diversidade |

`poprua` e `casamulher` estão em desenvolvimento; os demais estão completos (ver "Mapa de Apps" em `CLAUDE.md` para o status atualizado).

## Banco de dados

Banco unico: **PostgreSQL 15 Alpine em container Docker**. A maioria dos models de negócio usa `managed=False` — o schema é gerenciado manualmente no PostgreSQL, não por migrations do Django (ver `CLAUDE.md`, seção "Banco de Dados").

Configuracao em `.env` (dev fora do Docker — ver `CLAUDE.md` para os valores usados dentro do container e na VPS):
```
DB_ENGINE=django.db.backends.postgresql
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5433
```

## Como rodar

Via Docker (recomendado — ver `CLAUDE.md` para detalhes, inclusive a nota sobre hot-reload):
```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```
Acesse em **http://127.0.0.1:8001/** (porta 8000 é usada por outro projeto nesta máquina — nunca usar 8000 aqui).

Sem Docker, direto no host (mais rápido para iterar, usa `.env` local):
```powershell
cd "C:\Users\Klisman rDs\Documents\Gestaosuas-django"
python manage.py migrate
python manage.py runserver 8001
```
