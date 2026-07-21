# 01 — Cadeia de Relatórios (Dependências Sequenciais)

> **Área**: Relatórios mensais cujo valor de um mês depende ou deveria depender do mês anterior.

---

## A) Mapeamento Técnico

### Apps e models envolvidos

| App | Model | Tabela | Tipo de dependência |
|-----|-------|--------|-------------------|
| `cras` | `CrasReport` | `cras_reports` | `mes_anterior` → `atual` mês N-1 (manual, não automático) |
| `protecaoespecial` | `CreasProtetivoReport` | `creas_protetivo_reports` | `fam_mes_anterior` → `fam_atual` mês N-1 (manual) + `atend_mes_anterior` → `atend_atual` mês N-1 (manual) |
| `protecaoespecial` | `CreasSocioeducativoReport` | `creas_socioeducativo_reports` | Campos `_1_dia` representam o estoque do início do mês (= total do mês anterior) |
| `directorates` | `MonthlyReport` | `monthly_reports` | Relatórios narrativos por setor — independentes dos numéricos, mas referenciam o mesmo mês/ano |
| `ceai` | `Submission` | `submissions` (compartilhada com `directorates.MonthlySubmission`) | Sem dependência sequencial — cada mês é independente |

### Relações entre models

```
CRAS:    CrasReport (dados numéricos) ──┐
                                         ├── mesma diretoria/mês/ano, tabelas diferentes
NARRAT:  MonthlyReport (relato textual) ─┘   setor = "cras"

PROTETIVO: CreasProtetivoReport ──┐
NARRAT:    MonthlyReport ──────────┘  setor = "creas"

SOCIOEDUC: CreasSocioeducativoReport ──┐
NARRAT:    MonthlyReport ──────────────┘  setor = "creas"

CEAI:     Submission (JSON genérico) ──┐
NARRAT:   MonthlyReport ───────────────┘  setor = "ceai"
```

### Views relevantes

| View | App | Template | Função |
|------|-----|----------|--------|
| `CrasCreateUpdateView` | cras | `cras/form.html` | Preenche/edita relatório CRAS; `form_valid()` faz `get_or_create` |
| `CrasHomeView` | cras | `cras/home.html` | Dashboard com cards por mês/unidade |
| `CrasDataView` | cras | `cras/data.html` | Tabela com 12 meses, permite quick-edit (só admin) |
| `CreasProtetivoFormView` | protecaoespecial | — | Preenche protetivo; campos computados `fam_atual`/`atend_atual` |
| `CreasSocioeducativoFormView` | protecaoespecial | — | Preenche socioeducativo; campos computados `fam_total_acompanhamento` |
| `*MonthlyNarrativeView` | vários | `*/monthly_report.html` | Narrativa textual mensal (`MonthlyReport`) |
| `CeaiDashboardView` | ceai | `ceai/dashboard.html` | Dashboard CEAI |

---

## B) Regras de Negócio Inferidas do Código

### B.1 CRAS — dependência `mes_anterior` → `atual`

**Inferência**: O campo `mes_anterior` é preenchido manualmente (não vem do banco). O campo `atual` é calculado automaticamente no formulário (`clean()`):

```python
# apps/cras/forms.py
def clean(self):
    mes_ant = int(cleaned.get("mes_anterior") or 0)
    admit = int(cleaned.get("admitidas") or 0)
    cleaned["atual"] = mes_ant + admit
```

O help text do formulário sugere: `"Preenchido automaticamente: (Atual do mês anterior - Desligadas do mês anterior)"`

**Regra inferida**: Para o mês N, o usuário deveria preencher `mes_anterior` = `atual` do mês N-1. Mas nada no código valida isso — o campo é livre. O `atual` é `mes_anterior + admitidas`, e `desligadas` reduz o estoque para o mês seguinte mas não afeta o `atual` do mês corrente.

**Observação**: O template `cras/data.html` mostra tabela de 12 meses lado a lado — sugere que o usuário revisa visualmente a continuidade, mas sem validação.

### B.2 CRAS Protetivo — dependência de famílias e atendimentos

**Inferência**: O formulário tem campos `fam_mes_anterior`, `fam_admitidas`, `fam_desligadas`, `fam_atual`. O model `CreasProtetivoReport.save()` é que faz o cálculo? Vamos ver...

O model protecaoespecial não tem `save()` sobrescrito que faça cálculo automático. O formulário `CreasProtetivoForm` (herda de `StyledMonitoringForm`) também não tem `clean()` customizado. Portanto os campos `fam_atual` e `atend_atual` são preenchidos manualmente pelo usuário.

**Regra inferida**: O usuário deve manualmente calcular `fam_atual = fam_mes_anterior + fam_admitidas`. Sem validação automática.

### B.3 CRAS Socioeducativo — dependência "primeiro dia do mês"

**Inferência**: Campos `fam_acompanhamento_1_dia`, `masc_acompanhamento_1_dia`, `fem_acompanhamento_1_dia` representam o total em acompanhamento no primeiro dia do mês (= total do mês anterior). Campos `_total_parcial` são computados no `save()` do model:

```python
# apps/protecaoespecial/models.py (CreasSocioeducativoReport.save)
```

**Regra inferida**: Os totais parciais são calculados automaticamente no `save()` do model (soma de `_1_dia + admitidos/inseridos`). Mas `_1_dia` é preenchido manualmente — não vem do mês anterior automaticamente.

### B.4 MonthlyReport — narrativa textual

**Regra explícita**: `MonthlyReport` é um relato descritivo (content = JSONB com texto livre) vinculado a `(directorate, setor, month, year)`. Não há dependência de dados entre meses.

**Inferência**: Agentes só veem os próprios relatórios (filtro `user_external_id`). Diretores e admins veem todos da diretoria. Isso sugere que cada agente escreve seu próprio relato, e o diretor consolida.

### B.5 CEAI — Submissions independentes

**Inferência**: O CEAI usa a tabela `submissions` com um JSONB chamado `data` que contém o formulário inteiro. Cada mês/ano é independente — sem cálculo automático entre meses.

### B.6 Cadeia de status e fechamento

**Regra explícita no código**: Todas as views de formulário (`post()`) bloqueiam re-preenchimento se já existe um registro para aquele mês/ano:

```python
if self._get_existing_report():
    messages.error(request, "Este mês já foi lançado...")
    return redirect(...)
```

Isso vale para: CRAS, Beneficios, NAICA, CREAS Idoso/PCD, Monitoramento (genérico), Proteção Especial.

**Mas não há verificação de `status`** — o bloqueio é binário (existe vs. não existe), não considera se o status é `draft`, `finalized` ou `submitted`. Ou seja: uma vez criado, NUNCA mais pode ser editado pelo usuário normal, mesmo que ainda seja `draft`.

### B.7 Quick-edit (admin only)

**Regra explícita**: Views `*QuickEditView` têm `allowed_roles = ["admin"]` e permitem editar qualquer campo numérico de qualquer mês via POST AJAX. Isso é o "reabrir" mencionado nas mensagens de erro. O admin pode corrigir qualquer valor sem restrição de status.

---

## C) Perguntas de Alinhamento

### C.1 Comportamento no fechamento de mês
1. **Qual é o fluxo correto de fechamento?** O usuário preenche → salva (status `draft`?) → depois "finaliza"? Ou o simples ato de salvar já "fecha" o mês (bloqueia edição)?
2. **O status `finalized` vs `submitted` tem diferença funcional?** Hoje nenhum código lê o campo `status` da maioria dos relatórios para tomar decisões (exceto `GenericMonitoringReport.status` e `Visit.status`). O status serve só para o dashboard, ou deveria controlar permissão de edição?

### C.2 Continuidade entre meses (CRAS)
3. **O campo `mes_anterior` do CRAS deve ser preenchido automaticamente com o `atual` do mês anterior?** Hoje é manual. Se o mês anterior for corrigido (quick-edit), o mês seguinte fica inconsistente.
   - **Resposta (2026-07-21)**: Alguns formulários têm fórmulas que calculam o valor do mês anterior. O usuário vai revisar cada um individualmente e pedir ajustes. (Parcialmente resolvido — revisão caso a caso pendente.)
4. **Se um admin corrige o `atual` de Janeiro, deveria recalcular automaticamente o `mes_anterior` de Fevereiro?**
   - **Resposta (2026-07-21)**: ✅ **SIM**. Se for uma fórmula que recebe o valor do mês anterior, deve recalcular automaticamente.

### C.3 Continuidade entre meses (Proteção Especial)
5. **Campos `_1_dia` (Socioeducativo) e `_mes_anterior` (Protetivo) deveriam ser preenchidos automaticamente do mês anterior?** Mesma questão do CRAS.
6. **Os campos computados `fam_atual`, `atend_atual` (Protetivo) e `*_total_parcial` (Socioeducativo) são calculados no `save()` do model — isso está correto?** Ou deveriam ser readonly e calculados no formulário (como o CRAS faz com `atual`)?

### C.4 Concorrência (dois usuários mesma diretoria, mesmo mês)
7. **O que acontece se dois usuários diferentes da mesma diretoria abrirem o formulário do mesmo mês ao mesmo tempo?**
   - **Resposta (2026-07-21)**: ✅ Quem preencher primeiro bloqueia o mês. Está funcionando como esperado.
8. **Agentes diferentes da mesma diretoria preenchem o mesmo formulário ou cada um tem o seu?**
   - **Resposta (2026-07-21)**: ✅ Um único registro por diretoria/mês. O primeiro que salvar bloqueia. Está correto.

### C.5 MonthlyReport — narrativa textual
9. **Agentes diferentes da mesma diretoria escrevem narrativas separadas ou compartilham a mesma?** O código filtra `user_external_id` para agentes, sugerindo que cada agente tem a sua. Mas o `unique_together` do banco é `(directorate_id, setor, month, year)` — sem `user_id`. Se dois agentes escreverem no mesmo mês, o segundo sobrescreve o primeiro?
   - **PENDENTE** — usuário pediu explicação menos técnica. Ver reformulação abaixo.
10. **O `MonthlyReport` depende do relatório numérico estar preenchido?** Ou podem existir independentemente?

### C.6 Status e reabertura
11. **Quem pode "reabrir" um mês?** A mensagem de erro diz "Peça a um administrador para reabrir". Mas o código não tem uma ação explícita de "reabrir" — o admin simplesmente edita via quick-edit. Isso é suficiente?
    - **Resposta (2026-07-21)**: ✅ Somente admin. O quick-edit célula-por-célula é o mecanismo suficiente.
12. **Deveria existir uma ação explícita de "reabrir" que muda o status de `finalized` para `draft`?** Ou o quick-edit já cobre todos os casos?
    - **Resposta (2026-07-21)**: ✅ O quick-edit atual já cobre. Não precisa de ação explícita de reabertura.

---

## D) Esboço de Cenários Given-When-Then

### D.1 Bloqueio de re-preenchimento
> **Status**: Regra explícita no código — confirmada.

```
Dado que existe um CrasReport para diretoria X, unidade "MORUMBI", mês 6, ano 2026
Quando um agente tenta acessar o formulário de preenchimento para essa mesma combinação
Então o sistema redireciona com mensagem de erro "Este mês já foi lançado"
E o formulário não é exibido
```

### D.2 Quick-edit por admin
> **Status**: Regra explícita no código — confirmada.

```
Dado que existe um CrasReport com status "finalized"
E o usuário é admin
Quando o admin edita um valor via quick-edit (POST para /cras/quick-edit/)
Então o valor é atualizado no banco
E o campo updated_at é atualizado
E o status NÃO é alterado (permanece "finalized")
```

### D.3 Cálculo de `atual` no CRAS (formulário)
> **Status**: Regra explícita no código — confirmada.

```
Dado que o usuário preenche mes_anterior=100 e admitidas=20
Quando o formulário é submetido
Então o campo atual é salvo como 120
```

### D.4 Dependência entre meses (CRAS — fórmula automática)
> **Status**: Confirmado via resposta C.2 (2026-07-21). Fórmulas que dependem do mês anterior devem recalcular automaticamente.

```
Dado que existe um CrasReport para Janeiro com atual=100
E o admin corrige atual de Janeiro para 120 via quick-edit
Quando o sistema recalcula os meses dependentes
Então o mes_anterior de Fevereiro (se existir) deve ser atualizado para 120
E o campo atual de Fevereiro deve ser recalculado (mes_anterior + admitidas)
```

**Nota**: O escopo exato de quais fórmulas são afetadas será definido quando o usuário revisar cada formulário (resposta 6, C.2).

---

## Changelog

| Data | Mudança | Motivo |
|------|---------|--------|
| 2026-07-21 | Criação do arquivo | Mapeamento inicial de cadeias de dependência entre relatórios |
| 2026-07-21 | Respostas Q2, Q3, Q4, Q7 confirmadas | Alinhamento com usuário: concorrência, bloqueio, admin-only, fórmulas automáticas |
| 2026-07-21 | D.4 convertido de PENDENTE para confirmado | Fórmulas que dependem do mês anterior devem recalcular automaticamente |
