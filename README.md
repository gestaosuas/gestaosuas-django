# Gestaosuas Django

Recriacao do Sistema de Vigilancia Socioassistencial em Django, conectado ao banco PostgreSQL do Supabase Docker.

## Estrutura

| App | Responsabilidade |
|-----|-----------------|
| `apps/core/` | Layout, dashboard base, mapas, configuracoes, utilities compartilhadas |
| `apps/accounts/` | Autenticacao via Supabase Auth, perfis, permissoes |
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

## Banco de dados

Banco unico: **PostgreSQL do Supabase Docker** (`127.0.0.1:54322`).

Configuracao em `.env`:
```
DB_ENGINE=django.db.backends.postgresql
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=127.0.0.1
DB_PORT=54322
```

## Como rodar

```powershell
cd C:\Users\Klisman rDs\Documents\Gestaosuas\Gestaosuas-django
python manage.py migrate
python manage.py runserver
```

## Migracao de dados do Next.js

Os dados do Next.js estao na tabela legada `submissions` (JSONB). Para migrar para as tabelas especializadas:

```powershell
python manage.py migrate_submissions
```

Este comando le a tabela `submissions` e copia os dados para as tabelas especializadas de cada diretoria (`cras_reports`, `beneficios_reports`, `creas_idoso_reports`, etc.).
