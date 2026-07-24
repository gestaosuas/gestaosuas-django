# 00 — Modelo de Dados (Schema Real)

> **Fonte**: `docker exec gestaosuas_app_dev python manage.py inspectdb` + `information_schema.columns` + `information_schema.table_constraints FOREIGN KEY`.
> **Gerado em**: 2026-07-21
> **Ambiente**: Dev local (container `gestaosuas_db`, PostgreSQL 15 Alpine)

---

## 1. Tabelas de negócio (ignora auth_*, django_*, sessions, admin_log, migrations)

| # | Tabela | App Django | Model | managed | FKs reais |
|---|--------|-----------|-------|---------|-----------|
| 1 | `activity_logs` | core | `ActivityLog` | False | `directorate_id` → `directorates.id` |
| 2 | `beneficios_reports` | beneficios | `BeneficiosReport` | False | `directorate_id` → `directorates.id`, `user_id` → `accounts_user.id` |
| 3 | `casa_da_mulher_reports` | casamulher | `CasaDaMulherReport` | False | `directorate_id` → `directorates.id`, `user_id` → `accounts_user.id` |
| 4 | `ceai_categorias` | ceai | `CeaiCategory` | False | — (referenciada por `ceai_oficinas.category_id`) |
| 5 | `ceai_oficinas` | ceai | `CeaiOficina` | False | `category_id` → `ceai_categorias.id` |
| 6 | `cras_reports` | cras | `CrasReport` | False | `directorate_id` → `directorates.id`, `user_id` → `accounts_user.id` |
| 7 | `creas_idoso_reports` | creasidoso | `CreasIdosoReport` | False | `directorate_id` → `directorates.id`, `created_by` → `accounts_user.id` |
| 8 | `creas_pcd_reports` | creasidoso | `CreasPcdReport` | False | `directorate_id` → `directorates.id`, `created_by` → `accounts_user.id` |
| 9 | `creas_pop_rua_reports` | poprua | `PopRuaReport` | False | `directorate_id` → `directorates.id`, `created_by` → `accounts_user.id` |
| 10 | `creas_protetivo_reports` | protecaoespecial | `CreasProtetivoReport` | False | `directorate_id` → `directorates.id`, `user_id` → `accounts_user.id` |
| 11 | `creas_socioeducativo_reports` | protecaoespecial | `CreasSocioeducativoReport` | False | `directorate_id` → `directorates.id`, `user_id` → `accounts_user.id` |
| 12 | `daily_reports` | directorates | `DailyReport` | False | `directorate_id` → `directorates.id`, `user_id` → `accounts_user.id` |
| 13 | `directorates` | directorates | `Directorate` | False | — (pai de quase tudo) |
| 14 | `diversidade_reports` | casamulher | `DiversidadeReport` | False | `directorate_id` → `directorates.id`, `user_id` → `accounts_user.id` |
| 15 | `form_delegations` | directorates | `FormDelegation` | False | `visit_id` → `visits.id`, `user_id` → `profiles.id`, `delegated_by` → `profiles.id`, `directorate_id` → `directorates.id` |
| 16 | `map_categories` | core | `MapCategory` | False | — |
| 17 | `map_units` | core | `MapUnit` | False | `category_id` → `map_categories.id` |
| 18 | `monitorings_genericmonitoringreport` | monitoramento | `GenericMonitoringReport` | False | `directorate_id` → `directorates.id`, `user_id` → `accounts_user.id` |
| 19 | `monthly_reports` | directorates | `MonthlyReport` | False | `directorate_id` → `directorates.id`, `user_id` → `accounts_user.id` |
| 20 | `naica_reports` | naica | `NaicaReport` | False | `directorate_id` → `directorates.id`, `user_id` → `accounts_user.id` |
| 21 | `nucleo_diversidade_reports` | casamulher | `NucleoDiversidadeReport` | False | `directorate_id` → `directorates.id`, `user_id` → `accounts_user.id` |
| 22 | `oscs` | directorates | `Osc` | False | `directorate_id` → `directorates.id`, `user_id` → `accounts_user.id` |
| 23 | `profile_directorates` | accounts | `ProfileDirectorate` | False | `profile_id` → `profiles.id`, `directorate_id` → `directorates.id` |
| 24 | `profiles` | accounts | `Profile` | False | `directorate_id` → `directorates.id` |
| 25 | `qualificacao_reports` | sinecp | `QualificacaoReport` | False | `directorate_id` → `directorates.id`, `user_id` → `accounts_user.id` |
| 26 | `settings` | core | `SystemSetting` | False | — |
| 27 | `sine_reports` | sinecp | `SineReport` | False | `directorate_id` → `directorates.id`, `user_id` → `accounts_user.id` |
| 28 | `submissions` | directorates/ceai | `MonthlySubmission` / `Submission` | False | `directorate_id` → `directorates.id`, `user_id` → `accounts_user.id` |
| 29 | `visits` | directorates | `Visit` | False | `osc_id` → `oscs.id`, `directorate_id` → `directorates.id`, `user_id` → `accounts_user.id`, `work_plan_id` → `work_plans.id` |
| 30 | `work_plans` | directorates | `WorkPlan` | False | `osc_id` → `oscs.id`, `user_id` → `accounts_user.id` |

**Totais**: 30 tabelas de negócio, todas com FK para `accounts_user` ou `profiles` (exceto `activity_logs` que tem FK só pra `directorates`).

---

## 2. Divergências model vs. schema real

### 2.1 FK existente no banco sem campo correspondente no model

| Tabela | Coluna FK | Model | Campo no model |
|--------|----------|-------|---------------|
| `visits` | `work_plan_id` → `work_plans.id` | `Visit` | **TEM** (`work_plan = ForeignKey(WorkPlan, ...)`) — OK, model atualizado no commit de 2026-07-20 |
| `creas_pop_rua_reports` | `created_by` → `accounts_user.id` | `PopRuaReport` | `created_by = UUIDField(...)` — model declara como UUIDField, mas o banco tem FK real para accounts_user ✔ |

### 2.2 Campo no model sem FK onde o banco tem FK

| Model | Campo | Tipo no model | Tipo real no banco | FK real |
|-------|-------|--------------|-------------------|---------|
| `BeneficiosReport` | `user_id` (via `user_external_id`) | `UUIDField(null=True)` | `user_id uuid` com FK para `accounts_user.id` | ✔ FK existe |
| `CrasReport` | `user_id` (via `user_external_id`) | `UUIDField(null=True)` | `user_id uuid` com FK para `accounts_user.id` | ✔ FK existe |
| `MonthlyReport` | `user_id` (via `user_external_id`) | `UUIDField(null=True)` | `user_id uuid` com FK para `accounts_user.id` | ✔ FK existe |
| `CreasIdosoReport` | `created_by` | `UUIDField(null=True)` | `created_by uuid` com FK para `accounts_user.id` | ✔ FK existe |
| `CreasPcdReport` | `created_by` | `UUIDField(null=True)` | `created_by uuid` com FK para `accounts_user.id` | ✔ FK existe |
| `PopRuaReport` | `created_by` | `UUIDField(null=True)` | `created_by uuid` com FK para `accounts_user.id` | ✔ FK existe |

**Padrão encontrado**: modelos recentes (casamulher, protecaoespecial) usam `user_id` como `UUIDField` sem `ForeignKey` Django, mas a FK física já existe no banco (migrate_to_pure_pg.sql Passo 7). Os modelos mais antigos (creasidoso) declaram `created_by = UUIDField(null=True, blank=True)` — não modelam a FK no ORM do Django, mas a FK existe no banco.

### 2.3 Tipos divergentes

| Tabela | Coluna | Tipo no banco | Tipo no model Django |
|--------|--------|--------------|---------------------|
| `cras_reports` | `unique_together` | `(unit_name, month, year)` (banco NÃO inclui directorate_id) | Model declara `(directorate, unit_name, month, year)` |
| `beneficios_reports` | `directorate_id` | `uuid NOT NULL` (sem FK no schema original do Supabase — corrigido no Passo 9) | `ForeignKey(Directorate, null=True, blank=True)` |
| `creas_idoso_reports` | `created_at` | `timestamp with time zone NOT NULL DEFAULT now()` | `DateTimeField(null=True, blank=True)` |
| `creas_idoso_reports` | `updated_at` | `timestamp with time zone NOT NULL DEFAULT now()` | `DateTimeField(null=True, blank=True)` |
| `creas_pcd_reports` | `created_at` | `timestamp with time zone NOT NULL DEFAULT now()` | `DateTimeField(null=True, blank=True)` |
| `creas_pcd_reports` | `updated_at` | `timestamp with time zone NOT NULL DEFAULT now()` | `DateTimeField(null=True, blank=True)` |
| `qualificacao_reports` | `created_at` / `updated_at` | `NOT NULL DEFAULT now()` | Model declara sem `null=True` (correto) |
| `sine_reports` | `created_at` / `updated_at` | `NOT NULL DEFAULT now()` | Model declara sem `null=True` (correto) |
| `map_units` | `latitude` / `longitude` | `numeric` (decimal real) | `DecimalField(max_digits=10, decimal_places=7)` |

### 2.4 Nullability divergente

| Model | Campo | Model (nullable) | Banco (nullable) |
|-------|-------|-----------------|-----------------|
| `CreasIdosoReport` | `created_at` | `null=True` | `NOT NULL` |
| `CreasPcdReport` | `created_at` | `null=True` | `NOT NULL` |
| `CreasIdosoReport` | `updated_at` | `null=True` | `NOT NULL` |
| `CreasPcdReport` | `updated_at` | `null=True` | `NOT NULL` |
| `CrasReport` | `directorate` | `null=True, blank=True` | O banco permite NULL (coluna nullable), mas o unique_together do banco não inclui directorate |
| `BeneficiosReport` | `directorate` | `null=True, blank=True` | O banco tem `directorate_id` NOT NULL (após correção do Passo 9) |
| `NaicaReport` | `created_by` | `TextField` (NOT NULL implícito) | `text NOT NULL` ✔ |

### 2.5 Model sem campo que existe no banco

| Tabela | Coluna extra no banco | Model | Situação |
|--------|----------------------|-------|----------|
| `ceai_oficinas` | `classes_count` (int) | `CeaiOficina` | **Campo existe no banco, ausente no model** — `inspectdb` detectou, o model não declara |
| `beneficios_reports` | `user_id` (FK → accounts_user) | `BeneficiosReport` | Model usa `user_external_id` como db_column apelido, OK |
| `cras_reports` | `user_id` (FK → accounts_user) | `CrasReport` | Model usa `user_external_id` como db_column apelido, OK |
| `monthly_reports` | `user_id` (FK → accounts_user) | `MonthlyReport` | Model usa `user_external_id` como db_column apelido, OK |
| `oscs` | `user_id` (FK → accounts_user) | `Osc` | Model usa `user_id = UUIDField(...)` sem FK, banco tem FK ✔ |
| `work_plans` | `directorate_id` (UUID, sem FK no banco!) | `WorkPlan` | `directorate = ForeignKey(...)` — model declara FK, mas **banco NÃO tem FK constraint** sobre `directorate_id` |

### 2.6 Tabela sem model correspondente

| Tabela | Situação |
|--------|----------|
| `submissions` | Usada por 2 models: `apps.directorates.models.MonthlySubmission` e `apps.ceai.models.Submission`. Ambos apontam para `db_table = "submissions"`. Compartilhamento intencional entre apps. |
| Nenhuma outra órfã | — |

### 2.7 Model sem tabela

Nenhum caso — todos os models declarados em `apps/*/models.py` têm tabela correspondente no banco.

---

## 3. Constraints UNIQUE (unique_together)

| Tabela | Colunas | Source |
|--------|---------|--------|
| `beneficios_reports` | `(directorate_id, month, year)` | model + banco ✔ |
| `casa_da_mulher_reports` | `(directorate_id, month, year)` | model + banco ✔ |
| `cras_reports` | `(unit_name, month, year)` | **banco** — model declara `(directorate, unit_name, month, year)` ❌ |
| `creas_idoso_reports` | `(directorate_id, month, year)` | model + banco ✔ |
| `creas_pcd_reports` | `(directorate_id, month, year)` | model + banco ✔ |
| `creas_pop_rua_reports` | `(directorate_id, month, year)` | model + banco ✔ |
| `creas_protetivo_reports` | `(directorate_id, month, year)` | model + banco ✔ |
| `creas_socioeducativo_reports` | `(directorate_id, month, year)` | model + banco ✔ |
| `diversidade_reports` | `(directorate_id, month, year)` | model + banco ✔ |
| `monitorings_genericmonitoringreport` | `(directorate_id, reference, month, year)` | model + banco ✔ |
| `monthly_reports` | `(directorate_id, setor, month, year)` | model + banco ✔ |
| `naica_reports` | `(directorate_id, unit_name, month, year)` | model + banco ✔ |
| `nucleo_diversidade_reports` | `(directorate_id, month, year)` | model + banco ✔ |
| `qualificacao_reports` | `(directorate_id, month, year)` | model + banco ✔ |
| `sine_reports` | `(directorate_id, month, year)` | model + banco ✔ |
| `submissions` | `(directorate_id, month, year)` | model + banco ✔ |
| `form_delegations` | `(visit_id, user_id)` | model + banco ✔ |

**Divergência crítica**: `cras_reports` no banco tem unique em `(unit_name, month, year)` — sem `directorate_id`. O model Django declara `(directorate, unit_name, month, year)`. Se dois diretores de CRAS diferentes cadastrassem a mesma unidade no mesmo mês/ano, o banco rejeitaria o segundo registro, mas o Django esperaria permitir. Na prática, como só existe uma diretoria de CRAS, isso não causa bug.

---

## 4. Estrutura de `visits` — colunas JSON

| Coluna | Tipo | Conteúdo típico |
|--------|------|----------------|
| `identificacao` | `jsonb` | `{osc_name, address, registered_by_name, ...}` |
| `atendimento` | `jsonb` | `{subsidized_count, activity_types, ...}` |
| `forma_acesso` | `jsonb` | `{funding_source, ...}` |
| `rh_data` | `jsonb` | Dados de recursos humanos |
| `assinaturas` | `jsonb` | `{tecnico1_nome, tecnico2_nome, ...}` |
| `parecer_tecnico` | `jsonb` | `{status, data, ...}` |
| `parecer_conclusivo` | `jsonb` | `{status, data, ...}` |
| `relatorio_final` | `jsonb` | `{status, data, ...}` |
| `notificacoes` | `jsonb` | `[]` (lista de notificações) |
| `documents` | `jsonb` | `[]` (lista de documentos anexados) |

---

## 5. Estrutura de `directorate.form_definition`

Define dinamicamente os campos do `GenericMonitoringReport`. Exemplo de estrutura:

```json
[
  {
    "title": "Atendimentos",
    "fields": [
      {"name": "total_atendimentos", "label": "Total de Atendimentos", "type": "number", "icon": "users", "color": "#3b82f6"},
      ...
    ]
  }
]
```

Diretorias como "Subvenção", "Emendas e Fundos" usam `form_definition` para criar formulários dinâmicos sem models específicos. Os dados são armazenados em `monitorings_genericmonitoringreport.payload` (JSONB genérico).

---

## 6. Notas de migração

- **Passo 7 de `migrate_to_pure_pg.sql`**: repontou FKs de `user_id`/`created_by` de 18+ tabelas de `auth.users` → `accounts_user`. Aplicado na VPS em 2026-07-20. Um `ALTER TABLE` futuro que adicione novas tabelas deve seguir o mesmo padrão (FK → `accounts_user`, nunca `auth.users`).
- **Passo 9**: corrigiu `beneficios_reports.directorate_id` de `text` para `uuid` com FK para `directorates`. Já aplicado.
- **`work_plans.directorate_id`**: o banco NÃO tem FK constraint sobre `directorate_id` (é só um campo UUID). O model Django declara `ForeignKey` — o ORM funciona, mas integridade referencial não é garantida pelo banco.
- **`oscs.user_id`**: FK existe no banco (`user_id → accounts_user.id`), mas o model Django declara `user_id = UUIDField(null=True, blank=True)`, sem relacionamento ForeignKey no ORM.

---

## Changelog

| Data | Mudança | Motivo |
|------|---------|--------|
| 2026-07-21 | Criação do arquivo | Primeira introspecção completa do banco dev local via inspectdb + information_schema |
| 2026-07-21 | `creas_pcd_reports` reestruturada | Estratificação por gênero: 5 violações × 4 campos × 2 gêneros = 40 campos. Removidas 20 colunas antigas, adicionadas 42 novas (inclui totais gerais) |
| 2026-07-21 | `creas_idoso_reports` reestruturada | Estratificação por gênero: 5 violações × 4 campos × 2 gêneros = 40 campos + 5 totais gerais. PAEFI: removido `paefi_novos_casos`, adicionado `paefi_total_acompanhamento` |
| 2026-07-21 | `creas_protetivo_reports` reestruturada | Estratificação por gênero + faixa etária: 5 violações × 3 subcategorias × 6 gender-age = 90 campos. Removidas 14 colunas antigas (viol_*, atend_*) |
| 2026-07-21 | Export Excel implementado | Função `build_workbook()` + mixin `ExcelExportMixin` em `apps/core/export.py`. Botão verde em todas as páginas "Ver Dados" (admin only). `openpyxl` adicionado às dependências |
| 2026-07-21 | Navbar: badge de cargo colorido | Context processor `user_profile_context` injeta perfil. Cores: admin=vermelho, diretor=âmbar, agente=verde |
| 2026-07-21 | Tema rosa para "Outros" | Novo `body.theme-rose` + `.header-rose` no CSS |
| 2026-07-21 | Tabelas de dados compactadas | `.table-monitoring` reduzido: padding 20→10px, fonte 10→9px(header)/14→13px(células), espaçamento 16→6px |
| 2026-07-21 | Células vazias mostram "0" | 9 templates de "Ver Dados" alterados: branco → `0` |
| 2026-07-24 | Corrigido typo `CreaIdosoReport`/`CreaspcdReport` → `CreasIdosoReport`/`CreasPcdReport` na seção 2.4 | Nomes de model errados, achado durante verificação geral de alinhamento entre `.md`s |
