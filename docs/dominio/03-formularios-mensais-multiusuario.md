# 03 — Formulários Mensais Multi-Usuário (Fluxo de Preenchimento)

> **Área**: Como múltiplos usuários (agentes, diretores, admins) de uma mesma diretoria preenchem os relatórios mensais.

---

## A) Mapeamento Técnico

### A.1 Views envolvidas no fluxo de preenchimento

Cada app de relatório mensal implementa um padrão quase idêntico:

| View | Método HTTP | Propósito | Roles |
|------|-----------|-----------|-------|
| `*CreateUpdateView` / `*FormView` | GET + POST | Exibe formulário e salva dados | `diretor`, `agente` (admin também) |
| `*QuickEditView` | POST (AJAX) | Edita valor individual inline (tabela de dados) | `admin` apenas |
| `*DeleteMonthView` | POST (AJAX) | Exclui um mês inteiro | `admin` apenas |
| `*DataView` | GET | Exibe tabela com 12 meses | Todos (com filtro de unidade) |
| `*HomeView` | GET | Dashboard com cards/KPIs | Todos |

### A.2 Padrão `get_or_create` no POST

**Todos** os apps seguem este padrão no `form_valid()`:

```python
# apps/cras/views.py - CrasCreateUpdateView.form_valid()
report, _ = CrasReport.objects.get_or_create(
    directorate=directorate, month=month_val, year=year_val, unit_name=unit_name
)
for field_name, value in form.cleaned_data.items():
    setattr(report, field_name, value)
report.updated_at = datetime.now()
report.save()
```

**Variações:**
- `CrasCreateUpdateView` NÃO usa `get_or_create` — usa `CrasReport.objects.get()` dentro de try/except. Se existir, atualiza; se não, cria. Mas o `post()` bloqueia se já existir, então `get_or_create` nunca criaria duplicata.
- `CreasIdosoFormView` / `CreasPcdFormView` usam `try/except DoesNotExist` → cria novo com `created_by=request.user.id`.
- `MonitoramentoFormView` usa `get_or_create`.
- Proteção Especial usa `get_or_create`.

### A.3 Bloqueio de re-preenchimento

Em **TODAS** as views de formulário, o método `post()` verifica:

```python
def post(self, request, *args, **kwargs):
    if self._get_existing_report():
        messages.error(request, "Este mês já foi lançado. Peça a um administrador para reabrir...")
        return redirect(...)
    return super().post(request, *args, **kwargs)
```

**Observação**: o bloqueio não verifica `status`. Qualquer registro existente (draft, finalized, submitted) bloqueia.

### A.4 Perfil de acesso por role

| Ação | Admin | Diretor | Agente | User |
|------|-------|---------|--------|------|
| Ver dashboard/home | Sim | Sim (sua diretoria) | Sim (unidades permitidas) | Não (sem vínculo) |
| Preencher formulário | Sim | Sim | Sim | Não |
| Editar após salvo | Não (bloqueado) | Não (bloqueado) | Não (bloqueado) | Não |
| Quick-edit (inline) | **Sim** | Não | Não | Não |
| Excluir mês | **Sim** | Não | Não | Não |
| Ver tabela de dados | Sim | Sim | Sim (filtrado) | Não |
| Escrever narrativa (MonthlyReport) | Sim | Sim | Sim (própria) | Não |
| Ver narrativas de outros | Sim | Sim (todas da diretoria) | Não (só própria) | Não |

### A.5 `get_allowed_units` — filtro de unidade

Definido em `apps/accounts/mixins.py`:

```python
def get_user_allowed_units(user, directorate):
    # admin → None (todas)
    # primary_directorate match → None (todas)
    # ProfileDirectorate link com allowed_units=None → None (todas)
    # ProfileDirectorate link com allowed_units=list → só essas
    # sem link → [] (nenhuma)
```

Esse filtro afeta `CrasHomeView` e `CrasDataView` (que têm o conceito de unidade). Apps sem unidades (beneficios, creasidoso, etc.) usam `DirectorateAccessMixin.dispatch()` para bloquear acesso completo à diretoria, em vez de filtrar unidades.

### A.6 Registro de quem preencheu

| Tabela | Campo | Preenchido por | Observação |
|--------|-------|---------------|------------|
| `cras_reports` | `user_id` | `request.user.pk` (via `user_external_id` no model) | Setado no `form_valid()` |
| `beneficios_reports` | `user_id` | `None` (!) | O código explicitamente seta `report.user_external_id = None` |
| `naica_reports` | `user_id` | `request.user.pk` | |
| `creas_idoso_reports` | `created_by` | `request.user.id` | |
| `creas_pcd_reports` | `created_by` | `request.user.id` | |
| `creas_pop_rua_reports` | `created_by` | `request.user.id` | |
| `monthly_reports` | `user_id` | `request.user.pk` (via `user_external_id`) | Narrative reports |
| `monitorings_genericmonitoringreport` | `created_by` | Padrão vazio — NÃO setado explicitamente | Usa default do banco |
| `casa_da_mulher_reports` | `user_id` | `request.user.id` | |
| `diversidade_reports` | `user_id` | `request.user.id` | |
| `nucleo_diversidade_reports` | `user_id` | `request.user.id` | |
| `creas_protetivo_reports` | `user_id` | `request.user.id` | |
| `creas_socioeducativo_reports` | `user_id` | `request.user.id` | |

**Divergência**: `beneficios_reports.user_id` é setado para `None` explicitamente no `form_valid()`. Isso parece ser um bug — ou uma decisão consciente de não rastrear quem preencheu benefícios.

---

## B) Regras de Negócio Inferidas do Código

### B.1 Um registro por diretoria/mês (exceto CRAS e NAICA que adicionam unidade)

**Regra explícita**: O `unique_together` do banco garante que só existe um registro por `(directorate, month, year)` para a maioria das tabelas. Para CRAS e NAICA, o unique inclui `unit_name`.

**Consequência**: Dois agentes da mesma diretoria NÃO podem preencher o mesmo mês independentemente — o segundo a salvar encontra o registro do primeiro.

### B.2 Ordem de preenchimento

**Inferência**: Não há restrição de ordem — o usuário pode preencher qualquer mês em qualquer ordem. Janeiro não precisa existir para Fevereiro ser preenchido. Isso é consistente com o uso de `get_or_create` (não há validação de mês anterior).

### B.3 Preenchimento parcial

**Inferência**: Todos os campos numéricos têm `required=False` e `initial=0`. O usuário pode submeter o formulário com campos vazios (viram 0). Isso significa que um mês pode ser "lançado" sem dados reais — o simples ato de abrir e salvar o formulário bloqueia o mês.

### B.4 "Reabertura" de mês

**Inferência**: O único mecanismo de "reabertura" é o quick-edit (admin-only). Não existe uma ação que mude `status` de `finalized` para `draft` e libere o formulário completo novamente. O admin pode corrigir célula por célula, mas não pode reabrir o formulário inteiro para o agente preencher novamente.

### B.5 Deleção de mês

**Inferência**: Views `*DeleteMonthView` (admin-only) fazem `DELETE` físico no banco. Depois de deletado, o mês pode ser preenchido novamente normalmente. Não há soft-delete.

### B.6 Filtro de agente em narrativas

**Regra explícita**:
```python
if self.is_agente():
    qs = qs.filter(user_external_id=self.request.user.pk)
```
Agentes só veem as próprias narrativas (`MonthlyReport`). Diretores e admins veem todas da diretoria.

---

## C) Perguntas de Alinhamento

### C.1 Concorrência entre usuários da mesma diretoria
1. **Dois agentes da mesma diretoria deveriam poder preencher o mesmo mês?**
   - **Resposta (2026-07-21)**: ✅ Quem preencher primeiro bloqueia o mês. Um único registro por diretoria/mês. Está como deve ser.
2. **Se não deveriam, quem "ganha" o direito de preencher?**
   - **Resposta (2026-07-21)**: ✅ O primeiro que salvar. Sem mecanismo adicional de lock.

### C.2 Preenchimento parcial e bloqueio acidental
3. **Um agente que abre o formulário, digita zero em tudo e salva — isso bloqueia o mês para sempre (só admin desbloqueia). Isso é intencional?** Ou deveria haver um estado "rascunho" que não bloqueia e um "finalizar" explícito?
   - **Resposta (2026-07-21)**: ✅ O usuário confirmou que o comportamento atual está funcionando como esperado. O simples ato de salvar já bloqueia. Se precisar corrigir, é pelo admin.
4. **O botão "salvar" deveria ter duas ações diferentes (salvar rascunho vs. finalizar)?**
   - **Resposta (2026-07-21)**: ✅ Não. O fluxo atual (salvar = bloquear) está correto.

### C.3 Reabertura de mês
5. **O fluxo esperado para correção é: agente pede → admin faz quick-edit → mês continua com status?**
   - **Resposta (2026-07-21)**: ✅ Somente admin corrige. O quick-edit é suficiente. Não precisa de ação de "reabrir" que mude status.
6. **Deveria existir um log de auditoria de quem editou o quê via quick-edit?** Hoje o campo `updated_at` é atualizado, mas não há registro de qual admin fez a alteração.
   - **PENDENTE** — não abordado pelo usuário.

### C.4 user_id em benefícios
7. **Por que `beneficios_reports.user_id` é setado para `None` no `form_valid()`?** É um bug ou intencional?
   - **Resposta (2026-07-21)**: ✅ É um **BUG**. Deveria seguir o mesmo padrão das outras diretorias (registrar `request.user.id`). Corrigir em próxima sessão.

### C.5 Status de relatório
8. **O campo `status` (draft/finalized/submitted) tem algum efeito funcional além de exibição?** Hoje o código NUNCA lê `status` para tomar decisões (exceto `GenericMonitoringReport` e `Visit`).
   - **Resposta (2026-07-21)**: ✅ O usuário confirmou que o comportamento atual está funcionando como precisa.
9. **Quem pode mudar o status?** Hoje parece que ninguém — não há view/botão para transição de status.
   - **Resposta (2026-07-21)**: ✅ O status atual é suficiente. Sem necessidade de transições explícitas.
10. **`MonthlyReport.status` default é `'finalized'` no banco.** Isso significa que narrativas já nascem finalizadas?
    - **PENDENTE** — não abordado pelo usuário.

### C.6 Perfis e permissões
11. **Um "diretor" deveria poder editar relatórios preenchidos por seus agentes?**
    - **Resposta (2026-07-21)**: ✅ **NÃO**. Diretor somente visualiza. Apenas admins editam, deletam ou alteram.
12. **O perfil "user" (sem role específica) existe mas nunca é usado nas views — qual o propósito?**
    - **Resposta (2026-07-21)**: Os usuários foram migrados do Supabase e ainda estão sendo vinculados a diretorias e cargos. O perfil "user" existe como padrão durante a migração.

---

## D) Esboço de Cenários Given-When-Then

### D.1 Agente preenche mês pela primeira vez
> **Status**: Regra explícita — confirmada.

```
Dado que o agente "João" tem vínculo com a diretoria CRAS
E não existe CrasReport para unidade "MORUMBI", mês 7, ano 2026
Quando João acessa /cras/<pk>/preencher/?year=2026&month=7&unit=MORUMBI
E preenche os campos e clica em Salvar
Então um novo CrasReport é criado com status "draft"
E user_id é setado para o UUID de João
E João é redirecionado para o dashboard
```

### D.2 Agente tenta re-preencher mês já lançado
> **Status**: Regra explícita — confirmada.

```
Dado que existe um CrasReport para unidade "MORUMBI", mês 7, ano 2026
Quando o agente "João" acessa o formulário para essa mesma combinação
Então o sistema exibe mensagem de erro "Este mês já foi lançado"
E redireciona para o formulário com os parâmetros atuais
```

### D.3 Admin faz quick-edit
> **Status**: Regra explícita — confirmada.

```
Dado que existe um relatório com id=X
E o usuário é admin
Quando o admin edita o campo "atendimentos" para 150 via POST /cras/quick-edit/
Então o valor é atualizado no banco
E o campo updated_at é atualizado
```

### D.4 Admin exclui um mês
> **Status**: Regra explícita — confirmada.

```
Dado que existe um relatório para mês 7
E o usuário é admin
Quando o admin clica em "Excluir" e confirma
Então o registro é deletado fisicamente do banco
E o mês pode ser preenchido novamente
```

### D.5 Dois agentes preenchem o mesmo mês — PENDENTE DE ALINHAMENTO
> **Status**: Depende das respostas C.1, C.2

```
Dado [definir após alinhamento]
Quando [definir após alinhamento]
Então [definir após alinhamento]
```

### D.6 Status e reabertura — PENDENTE DE ALINHAMENTO
> **Status**: Depende das respostas C.3, C.8, C.9

```
Dado [definir após alinhamento]
Quando [definir após alinhamento]
Então [definir após alinhamento]
```

---

## Changelog

| Data | Mudança | Motivo |
|------|---------|--------|
| 2026-07-21 | Criação do arquivo | Mapeamento do fluxo de preenchimento mensal multi-usuário |
| 2026-07-21 | Respostas Q1-Q5, Q7, Q8, Q9, Q11, Q12 confirmadas | Concorrência, bloqueio, admin-only, bug beneficios user_id, permissões |
| 2026-07-21 | Débito técnico #6 adicionado ao CLAUDE.md | Bug beneficios_reports.user_id = None |
