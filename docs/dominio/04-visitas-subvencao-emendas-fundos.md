# 04 — Visitas, Subvenção, Emendas e Fundos (Módulo Monitoramento)

> **Área**: Módulo de Subvenções/OSCs/Visitas Técnicas/Planos de Trabalho. Cobre as diretorias "Subvenção", "Emendas e Fundos" e "Outros" dentro do app `monitoramento`.

---

## A) Mapeamento Técnico

### A.1 Entidades principais

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│Directorate│────▶│   Osc    │────▶│ WorkPlan │
│          │     │          │     │          │
│ (1)      │     │ (N)      │     │ (N por   │
│          │     │          │     │  OSC)    │
└──────────┘     └────┬─────┘     └────┬─────┘
                      │               │
                      │               │ visit.work_plan (FK nullable)
                      ▼               │
                 ┌──────────┐         │
                 │  Visit   │◄────────┘
                 │          │
                 │ (N por   │
                 │  OSC)    │
                 └────┬─────┘
                      │
                      │ (1:N)
                      ▼
              ┌───────────────┐
              │FormDelegation │
              │ (delega visita│
              │  para agente) │
              └───────────────┘
```

### A.2 Models envolvidos

| Model | Tabela | App | Função |
|-------|--------|-----|--------|
| `Osc` | `oscs` | directorates | Organização da Sociedade Civil |
| `WorkPlan` | `work_plans` | directorates | Plano de trabalho vinculado a OSC |
| `Visit` | `visits` | directorates | Visita técnica a uma OSC |
| `FormDelegation` | `form_delegations` | directorates | Delegação de formulário de visita para agente |
| `GenericMonitoringReport` | `monitorings_genericmonitoringreport` | monitoramento | Relatório genérico de diretoria (usa `form_definition`) |
| `Directorate` | `directorates` | directorates | Contém `form_definition` (JSONB) que define os campos dinâmicos |

### A.3 Relações e FKs

```
Osc ──────────── directorate  (directorate_id → directorates.id)
Osc ──────────── user         (user_id → accounts_user.id)
WorkPlan ─────── osc          (osc_id → oscs.id)
WorkPlan ─────── user         (user_id → accounts_user.id)
WorkPlan ──?─── directorate   (directorate_id é UUID, MAS NÃO TEM FK constraint no banco!)
Visit ────────── osc          (osc_id → oscs.id)
Visit ────────── work_plan    (work_plan_id → work_plans.id, NULLABLE)
Visit ────────── directorate  (directorate_id → directorates.id)
Visit ────────── user         (user_id → accounts_user.id)
FormDelegation ─ visit        (visit_id → visits.id)
FormDelegation ─ user         (user_id → profiles.id)
FormDelegation ─ delegated_by (delegated_by → profiles.id)
FormDelegation ─ directorate  (directorate_id → directorates.id)
```

### A.4 Status de Visit

```python
STATUS_CHOICES = [
    ("draft", "Rascunho"),
    ("scheduled", "Agendada"),
    ("completed", "Concluida"),
]
```

O código lê `status` para estatísticas (`finalizationRate` conta visits com status `completed` ou `finalized` — mas `finalized` não está no `STATUS_CHOICES` do model).

### A.5 Fluxo de Visita Técnica e Relatórios (CONFIRMADO pelo usuário em 2026-07-21)

```
ETAPA 1: NOVA VISITA
  Usuário preenche dados da visita (OSC, data/hora, identificação, atendimento, etc.)
  Salva como RASCUNHO → pode editar e salvar quantas vezes quiser
  Ou FINALIZA → BLOQUEIA a visita (não pode mais editar — tem assinaturas)
  
  ⬇ (ao finalizar a Nova Visita, habilita a Etapa 2)

ETAPA 2: RELATÓRIO DE VISITA
  Herda os 4 itens do Plano de Trabalho (objeto, objetivos, metas, atividades)
  Salva como RASCUNHO → pode editar
  Ou FINALIZA → BLOQUEIA
  
  ⬇ (ao finalizar Etapa 1 E Etapa 2, na guia "Relatórios e Pareceres")

ETAPA 3: RELATÓRIO FINAL + PARECER CONCLUSIVO
  Aparecem cards de cada OSC/visita já finalizada
  Dois relatórios adicionais por visita:
    - Relatório Final
    - Parecer Conclusivo
  Ambos seguem o mesmo padrão: rascunho → editar → finalizar → bloqueado
```

**Regras do ciclo**:
- **Rascunho (draft)**: pode ser editado e salvo repetidamente. Não bloqueia.
- **Finalizado**: BLOQUEIA permanentemente. Não pode mais ser editado (contém assinaturas e documentos oficiais).
- O fluxo é sequencial: Etapa 2 só habilita após Etapa 1 finalizada. Etapa 3 só aparece após ambas as etapas anteriores finalizadas.
- Cada etapa é um formulário/aba diferente, mas todos fazem parte do mesmo registro `Visit` no banco (campos JSONB diferentes).

**Campos do model Visit usados em cada etapa**:

| Etapa | Campos preenchidos |
|-------|-------------------|
| Nova Visita | `osc`, `visit_date`, `visit_time`, `status`, `identificacao`, `atendimento`, `forma_acesso`, `rh_data`, `observacoes`, `recomendacoes`, `assinaturas`, `notificacoes` |
| Relatório de Visita | Herda `work_plan.objeto/objetivos/metas/atividades` + preenche `documents` |
| Relatório Final | `relatorio_final` (JSONB) |
| Parecer Conclusivo | `parecer_conclusivo` (JSONB) |
| Parecer Técnico | `parecer_tecnico` (JSONB) |

### A.6 Permissões de Visita por Perfil (CONFIRMADO pelo usuário em 2026-07-21)

| Ação | Admin | Diretor | Agente |
|------|-------|---------|--------|
| Ver visitas da diretoria | Todas | Todas (visualização) | **Apenas as próprias** |
| Criar Nova Visita | Sim | Sim | Sim |
| Editar visita (rascunho) | Sim | **Não** (só visualiza) | **Sim** (só as próprias) |
| Finalizar visita | Sim | **Não** | **Sim** (só as próprias) |
| Preencher Relatório de Visita | Sim | **Não** | **Sim** (só as próprias) |
| Relatório Final / Parecer | Sim | **Não** | **Sim** (só as próprias) |
| Excluir visita | Sim | Não | Não |

**Resumo**: Somente o agente que criou a visita pode editá-la e finalizá-la. O diretor vê tudo mas não edita nada — é um perfil de supervisão/consulta. Admin tem acesso total.

### A.6 Views do módulo monitoramento

| View | Template | Responsabilidade |
|------|----------|-----------------|
| `MonitoramentoHomeView` | `monitoramento/home.html` | Dashboard que detecta se é Subvenção/Emendas/Outros e renderiza OSCs + visitas + gráficos |
| `MonitoramentoFormView` | `monitoramento/shared/form.html` | Formulário dinâmico baseado em `directorate.form_definition` |
| `MonitoramentoDataView` | `monitoramento/shared/data.html` | Tabela de dados de 12 meses |
| `MonitoramentoDeleteMonthView` | — | POST para excluir mês |

Views de OSC/Visita/WorkPlan estão em `apps/directorates/views.py` (linhas 489-1927).

### A.7 Views de OSC/Visita/WorkPlan (directorates)

As views usam mixins de escopo local definidos em `views.py`: `DirectorateScopedMixin`, `OscScopedMixin`, `VisitScopedMixin`, `WorkPlanScopedMixin`.

| View | Template | Métodos |
|------|----------|---------|
| `OscListView` | `directorates/monitoring/osc_list.html` | GET (lista de OSCs) |
| `OscCreateView` / `OscUpdateView` | `directorates/monitoring/osc_form.html` | GET/POST (criar/editar OSC) |
| `OscDeleteView` | — | POST (excluir OSC) |
| `VisitListView` | `directorates/monitoring/visit_list.html` | GET (lista de visitas, com filtros) |
| `VisitCreateView` / `VisitUpdateView` | `directorates/monitoring/visit_form.html` | GET/POST |
| `VisitDetailView` | `directorates/monitoring/visit_instrumental.html` | GET (detalhes da visita) |
| `VisitDocumentView` | `directorates/monitoring/visit_document.html` | GET/POST (documentos da visita) |
| `VisitDeleteView` | — | POST |
| `WorkPlanListView` | `directorates/monitoring/plan_list.html` | GET |
| `WorkPlanCreateView` / `WorkPlanUpdateView` | `directorates/monitoring/plan_form.html` | GET/POST |
| `WorkPlanDocumentView` | `directorates/monitoring/work_plan_document.html` | GET/POST |
| `WorkPlanDeleteView` | — | POST |

### A.8 `form_definition` — campos dinâmicos (CONFIRMADO 2026-07-21)

O `directorate.form_definition` (JSONB) define quais campos aparecem no `MonitoramentoFormView` e no dashboard. A estrutura suporta `sections` com `fields` do tipo `number`, cada um com `name`, `label`, `icon`, `color`.

**Regra confirmada**: Esta configuração é gerenciada por desenvolvedores. O admin do sistema não edita isso em runtime. Mudanças nos campos são feitas via código/deploy, a pedido do usuário. Ninguém acessa o banco diretamente para alterar.

### A.9 Estrutura do WorkPlan

Além dos campos JSONB `content` (lista genérica), o `WorkPlan` tem campos textuais dedicados:
- `objeto`
- `objetivos`
- `metas`
- `atividades`

Estes são herdados pelo relatório de visita (`Visit`) quando a visita tem `work_plan` associado.

---

## B) Regras de Negócio Inferidas do Código

### B.1 Detecção de tema por nome da diretoria

**Regra explícita**: `MonitoramentoHomeView.get_context_data()` faz:

```python
ascii_name = strip_accents(directorate.name.lower())
is_subvencao = "subvencao" in ascii_name or "emendas" in ascii_name or "fundos" in ascii_name
```

Se o nome contém "subvencao" → tema verde (emerald). Se contém "emendas" → tema âmbar. Se contém "fundos" → tema indigo. Se contém "outros" → tema **rosa** (rose). Caso contrário → verde (default).

**Inferência**: Esses são os 4 tipos de diretoria que usam `GenericMonitoringReport`. Cada uma pode ter `form_definition` diferente para definir campos customizados.

### B.2 Visitas por bimestre

**Regra explícita**: O dashboard agrupa visitas por bimestre. Por padrão, mostra o bimestre atual. O bimestre é persistido na sessão.

```python
bimestre = math.ceil(datetime.now().month / 2)  # bimestre atual
```

### B.3 Filtro de visitas por perfil (CONFIRMADO 2026-07-21)

**Regra confirmada**: No dashboard de visitas:
- **Admin**: vê e edita todas as visitas da diretoria
- **Diretor**: vê todas as visitas da sua diretoria, mas **não edita** — somente visualização
- **Agente**: vê e edita **apenas as visitas que ele mesmo criou** OU que foram delegadas para ele (`FormDelegation`)

Código correspondente:

```python
if profile.role == "diretor":
    is_primary = str(profile.primary_directorate_id) == str(directorate.pk)
    is_linked = ProfileDirectorate.objects.filter(profile=profile, directorate=directorate).exists()
    if not (is_primary or is_linked):
        dashboard_visits_qs = dashboard_visits_qs.none()
else:
    delegated_visit_ids = FormDelegation.objects.filter(user_id=request.user.id).values_list("visit_id", flat=True)
    dashboard_visits_qs = dashboard_visits_qs.filter(Q(user_id=request.user.id) | Q(id__in=delegated_visit_ids))
```

### B.4 WorkPlan → Visit (objeto/objetivos/metas/atividades)

**Inferência**: Quando uma visita é vinculada a um `WorkPlan`, os campos `objeto`, `objetivos`, `metas`, `atividades` do WorkPlan são herdados pelo relatório de visita (provavelmente renderizados no template `visit_instrumental.html` ou `visit_document.html`). O campo `work_plan_id` na tabela `visits` é a FK que faz esse vínculo.

### B.5 GenericMonitoringReport — formulário dinâmico

**Regra explícita**: `MonitoramentoFormView` usa `directorate.form_definition` para construir o formulário dinamicamente. Os dados são salvos como `payload` (JSONB) no `GenericMonitoringReport`.

**Bloqueio**: Mesmo padrão dos outros apps — se já existe relatório para `(directorate, reference, month, year)`, bloqueia re-preenchimento.

### B.6 Delegação de formulário (FormDelegation)

**Inferência**: Um diretor/admin pode delegar uma visita específica para um agente preencher. A delegação é registrada na tabela `form_delegations` com `visit_id` + `user_id` (agente) + `delegated_by` (quem delegou). O agente então vê a visita no seu dashboard.

---

## C) Perguntas de Alinhamento

### C.1 Visitas e Status (CONFIRMADO 2026-07-21)
1. **Ciclo de vida completo da visita**:
   - **Resposta**: ✅ Etapa 1 (Nova Visita) → Etapa 2 (Relatório de Visita, herda WorkPlan) → Etapa 3 (Relatório Final + Parecer Conclusivo). Cada etapa: rascunho (editável) → finalizado (bloqueado). Ver seção A.5 para o fluxo completo.
2. **Quem pode transicionar o status?**
   - **Resposta**: ✅ Somente o agente que criou a visita pode editá-la e finalizá-la. Admin também pode. Diretor só visualiza.
3. **Status `finalized` vs `completed`**: O código atual tem `STATUS_CHOICES = [draft, scheduled, completed]` no model.
   - **Resposta (2026-07-21)**: ✅ Confirmado: somente 2 status: **Rascunho** (editável) e **Finalizada** (bloqueada). Os status `scheduled` e `completed` devem ser removidos.
   - **AÇÃO**: Atualizar `Visit.STATUS_CHOICES` para `[("draft", "Rascunho"), ("finalized", "Finalizada")]` e ajustar queries que referenciam `scheduled`/`completed`.

### C.2 WorkPlan e Visit
3. **WorkPlan é obrigatório para criar uma visita?**
   - **Resposta (2026-07-21)**: ✅ **NÃO**. WorkPlan não é obrigatório para visita.
4. **Uma OSC pode ter múltiplos WorkPlans?**
   - **Resposta (2026-07-21)**: ✅ **SIM**, geralmente em Emendas e Fundos que tem mais de 1 plano de trabalho.
5. **Os campos `objeto/objetivos/metas/atividades` existem tanto em `oscs` quanto em `work_plans`. Qual a diferença?**
   - **Resposta (2026-07-21)**: Esses campos são preenchidos no **Relatório de Visita** (segundo passo após "Nova Visita"). Os valores vêm do WorkPlan vinculado à visita — o relatório de visita exibe os 4 itens do plano de trabalho selecionado.

### C.3 Delegação (FormDelegation)
6. **Uma visita delegada a um agente — o agente vê o formulário completo ou só partes?** O código não mostra restrição de campos na view de edição.
7. **Depois que o agente preenche, o diretor revisa e aprova?** Ou a delegação é só para preenchimento e o status vai direto para completed?
8. **Um agente pode delegar para outro agente?** Ou só admin/diretor delegam?

### C.4 GenericMonitoringReport
9. **O `form_definition` é editável em runtime?** Se sim, mudar os campos depois que já existem registros no banco gera inconsistência (dados no `payload` JSONB que não correspondem mais aos campos atuais).
10. **As diretorias "Subvenção", "Emendas e Fundos" e "Outros" usam o mesmo `GenericMonitoringReport` — os campos são diferentes?** O formulário é definido dinamicamente por `form_definition`, mas a tabela é a mesma para todas as diretorias. Isso significa que dados de naturezas diferentes convivem na mesma tabela, diferenciados por `reference`.
11. **Quem define os campos que aparecem nos formulários de monitoramento?** (ex.: Emendas e Fundos)
    - **Resposta (2026-07-21)**: ✅ A configuração (`form_definition`) é gerenciada por desenvolvedores. Ninguém mexe no banco diretamente. O usuário dita as regras de como deve funcionar e o dev implementa no código. Só muda via deploy.

### C.5 OSC e múltiplas diretorias
11. **Uma OSC pertence a uma única diretoria (FK `directorate_id`). Isso é sempre verdade ou uma OSC pode atender múltiplas diretorias?**
12. **O campo `activity_type` da OSC é um select fixo no formulário (`OscForm`). Se um novo tipo de atividade surgir, precisa de deploy?**

### C.6 Documentos e Notificações
13. **Os campos `documents` e `notificacoes` (JSONB em `visits`) armazenam metadados de arquivos?** Ou são listas de objetos com URLs, status, etc.?
14. **Existe upload de arquivos para visitas?** Ou só referências externas (URLs)?

---

## D) Esboço de Cenários Given-When-Then

### D.1 Criação de OSC
> **Status**: Regra explícita — confirmada.

```
Dado que o usuário é admin ou diretor da diretoria "Subvenção"
Quando o usuário acessa o formulário de criação de OSC
E preenche nome, endereço, tipo de atividade e quantidade de subsidiados
Então uma nova OSC é criada vinculada à diretoria
E a OSC aparece na lista de OSCs do dashboard
```

### D.2 Agendamento de visita
> **Status**: Regra explícita — confirmada.

```
Dado que existe uma OSC "Instituto X" na diretoria "Subvenção"
Quando o admin agenda uma visita para 2026-08-15 às 14:00 com status "scheduled"
Então uma Visit é criada vinculada à OSC e à diretoria
E a visita aparece no dashboard com status "Agendada"
```

### D.3 Delegação de visita para agente
> **Status**: Regra explícita — confirmada.

```
Dado que existe uma visita com status "scheduled"
E o agente "Maria" tem vínculo com a diretoria
Quando o diretor delega a visita para Maria
Então uma FormDelegation é criada (visit_id=X, user_id=Maria, delegated_by=Diretor)
E Maria vê a visita no seu dashboard
```

### D.4 Agente preenche visita delegada
> **Status**: Parcialmente inferido — depende de C.2.

```
Dado que Maria tem uma visita delegada (FormDelegation)
Quando Maria acessa o formulário da visita e preenche os dados
Então os dados são salvos nos campos JSONB da visita
```

### D.5 Ciclo de vida completo da visita
> **Status**: Confirmado pelo usuário em 2026-07-21.

```
Dado que o agente "João" cria uma Nova Visita para a OSC "Instituto X"
E preenche os dados e salva como rascunho (status=draft)
Quando João reabre a visita e edita os dados
Então ele pode salvar como rascunho novamente (continua editável)

Dado que a visita está como rascunho
Quando João clica em "Finalizar"
Então o status muda para finalized
E a visita fica BLOQUEADA (não pode mais ser editada)
E a Etapa 2 (Relatório de Visita) é habilitada

Dado que a Etapa 1 está finalizada
E João preenche o Relatório de Visita (herda objeto/objetivos/metas/atividades do WorkPlan)
Quando João finaliza o Relatório de Visita
Então a Etapa 2 fica bloqueada
E na guia "Relatórios e Pareceres" aparecem os cards de Relatório Final e Parecer Conclusivo

Dado que Etapa 1 e Etapa 2 estão finalizadas
Quando João preenche e finaliza o Relatório Final E o Parecer Conclusivo
Então todos os relatórios da visita estão concluídos e bloqueados
```

### D.6 Permissões de edição de visita
> **Status**: Confirmado pelo usuário em 2026-07-21.

```
Dado que o agente "João" criou a visita #123
E a visita está como rascunho
Quando João tenta editar a visita
Então ele consegue abrir o formulário e salvar alterações

Dado que o diretor "Maria" é da mesma diretoria de João
Quando Maria tenta editar a visita #123
Então ela NÃO consegue editar (somente visualização)

Dado que o agente "Pedro" é da mesma diretoria mas NÃO criou a visita #123
Quando Pedro tenta acessar a visita #123
Então ele NÃO vê a visita no seu dashboard (só vê as próprias)

Dado que o admin "Carlos" acessa a diretoria
Quando Carlos tenta editar qualquer visita
Então ele consegue (acesso total)
```

### D.6 WorkPlan múltiplos por OSC
> **Status**: Confirmado via resposta C.2 (2026-07-21).

```
Dado que a OSC "Instituto X" já tem um WorkPlan "Plano 2026"
Quando o admin cria um segundo WorkPlan "Plano Aditivo 2026" para a mesma OSC
Então a OSC passa a ter 2 WorkPlans
E ao criar uma nova visita, o admin pode escolher qual WorkPlan vincular
```

### D.7 Visita sem WorkPlan
> **Status**: Confirmado via resposta C.2 (2026-07-21).

```
Dado que o admin está criando uma nova visita para a OSC "Instituto X"
Quando o admin NÃO seleciona nenhum WorkPlan
Então a visita é criada sem vínculo com WorkPlan (work_plan_id = NULL)
E a visita é válida e funcional
```

---

## Changelog

| Data | Mudança | Motivo |
|------|---------|--------|
| 2026-07-21 | Criação do arquivo | Mapeamento do módulo de visitas, subvenção, emendas e fundos |
| 2026-07-21 | Respostas Q3, Q4, Q5 confirmadas | WorkPlan não obrigatório, OSC pode ter múltiplos WorkPlans, campos herdados no relatório |
| 2026-07-21 | D.5, D.6, D.7 convertidos para confirmados | Ciclo de vida completo, permissões por perfil, WorkPlan múltiplos |
| 2026-07-21 | Fluxo A.5 reescrito com pipeline completo | Usuário confirmou: Etapa 1 (Nova Visita) → Etapa 2 (Relatório de Visita) → Etapa 3 (Relatório Final + Parecer Conclusivo) |
| 2026-07-21 | Permissões A.6 confirmadas | Agente edita só as próprias visitas, diretor só visualiza, admin acesso total |
| 2026-07-21 | C.1 STATUS_CHOICES divergente identificado | Model usa [draft, scheduled, completed]; fluxo real usa [draft, finalized] |
| 2026-07-21 | Resposta Q11 confirmada | form_definition gerenciado por devs, não editável em runtime pelo usuário |
| 2026-07-24 | B.1 corrigido: "outros" → rosa (não azul) | Texto desatualizado — código (`apps/monitoramento/views.py`) já usava tema rosa desde o commit 17ca164 ("rose theme for Outros"), doc não tinha sido atualizado. Achado durante verificação geral de alinhamento entre `.md`s |
