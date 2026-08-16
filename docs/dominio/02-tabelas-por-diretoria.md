# 02 — Tabelas por Diretoria (Models de Report)

> **Área**: Quais models/tabelas de relatório cada app usa, agrupados por tipo de diretoria.

---

## A) Mapeamento Técnico

### A.1 Tabela-resumo: App × Model × Tabela × Diretoria(s)

| App | Model | Tabela | Tipo de Diretoria | Unidade (multi?) | Rota |
|-----|-------|--------|------------------|-----------------|------|
| `cras` | `CrasReport` | `cras_reports` | CRAS (Proteção Social Básica) | Sim (13 unidades) | `/cras/<dir_slug:pk>/` |
| `beneficios` | `BeneficiosReport` | `beneficios_reports` | Benefícios | Não (única por diretoria) | `/beneficios/painel/` (sem dir_slug!) |
| `naica` | `NaicaReport` | `naica_reports` | NAICA | Sim (múltiplas unidades) | `/naica/<dir_slug:pk>/` |
| `creasidoso` | `CreasIdosoReport` | `creas_idoso_reports` | CREAS Idoso | Não | `/creasidoso/<dir_slug:pk>/` |
| `creasidoso` | `CreasPcdReport` | `creas_pcd_reports` | CREAS PCD | Não | `/creasidoso/<dir_slug:pk>/preencher-pcd/` |
| `poprua` | `PopRuaReport` | `creas_pop_rua_reports` | CREAS Pop Rua | Não | `/poprua/?` (sem dir_slug!) |
| `protecaoespecial` | `CreasProtetivoReport` | `creas_protetivo_reports` | CREAS Protetivo | Não | `/protecao-especial/<dir_slug:pk>/` |
| `protecaoespecial` | `CreasSocioeducativoReport` | `creas_socioeducativo_reports` | CREAS Socioeducativo | Não | `/protecao-especial/<dir_slug:pk>/` |
| `sinecp` | `SineReport` | `sine_reports` | SINE | Não | `/sine-cp/painel/` (tab=sine) |
| `sinecp` | `QualificacaoReport` | `qualificacao_reports` | Qualificação Profissional | Não | `/sine-cp/painel/` (tab=cp) |
| `casamulher` | `CasaDaMulherReport` | `casa_da_mulher_reports` | Casa da Mulher | Não | `/casa-mulher/<dir_slug:pk>/` |
| `casamulher` | `DiversidadeReport` | `diversidade_reports` | Diversidade | Não | `/casa-mulher/<dir_slug:pk>/` |
| `casamulher` | `NucleoDiversidadeReport` | `nucleo_diversidade_reports` | Núcleo Diversidade | Não | `/casa-mulher/<dir_slug:pk>/` |
| `monitoramento` | `GenericMonitoringReport` | `monitorings_genericmonitoringreport` | Subvenção, Emendas e Fundos, Outros | Não | `/monitoramento/<dir_slug:pk>/` |
| `ceai` | `Submission` | `submissions` | CEAI | Não (usa `data` JSONB) | `/ceai/` (sem dir_slug!) |
| `directorates` | `MonthlyReport` | `monthly_reports` | Todas (narrativa textual) | Não | `/.../<pk>/relatorio-mensal/` |

### A.2 Apps sem diretoria na URL (diretoria fixa)

Estes apps **não usam `<dir_slug:pk>` na URL**. Buscam a diretoria por nome via `icontains`:

| App | Como encontra a diretoria | Fallback |
|-----|--------------------------|----------|
| `beneficios` | `Directorate.objects.filter(name__icontains="benef").first()` | — |
| `poprua` | `Directorate.objects.filter(name__icontains="pop").first()` | — |
| `ceai` | `Directorate.objects.filter(name__icontains="CEAI").first()` | — |
| `sinecp` | Lógica interna (SINE e CP na mesma diretoria) | — |

### A.3 Apps com unidades (multi-registro por diretoria/mês)

| App | Unidades | Como são armazenadas |
|-----|----------|---------------------|
| `cras` | 13 unidades (`CRAS_UNITS` em `views.py`) | Coluna `unit_name` (text), `unique_together = (unit_name, month, year)` no banco |
| `naica` | Múltiplas unidades | Coluna `unit_name` (text), `unique_together = (directorate, unit_name, month, year)` |
| Todos os outros | Unidades não se aplicam | unique_together = `(directorate, month, year)` |

---

## B) Regras de Negócio Inferidas do Código

### B.1 Apps com diretoria fixa (sem dir_slug na URL)

**Inferência**: `beneficios`, `poprua`, `ceai`, `sinecp` presumem que só existe UMA diretoria com aquele nome no banco. Se houver duas (ex.: duas diretorias com "benef" no nome), a query `filter(name__icontains="benef").first()` pega uma arbitrária.

**Risco**: Duplicata de diretoria no banco quebraria silenciosamente esses apps.

### B.2 Apps com dir_slug na URL

**Inferência**: O converter `DirectorateSlugConverter` normaliza o nome → slug. Se duas diretorias tiverem o mesmo slug (ex.: "CREAS Idoso" → "creas-idoso" e "CREAS-Idoso" → "creas-idoso"), o converter retorna a primeira que encontrar. O slug é derivado do `name`, não é uma coluna dedicada.

### B.3 unique_together inconsistente do CRAS

**Inferência**: O banco tem unique em `(unit_name, month, year)` sem `directorate_id`. Se duas diretorias de CRAS existissem e ambas tivessem "MORUMBI" no mesmo mês/ano, o banco rejeitaria o segundo insert. Hoje não é problema porque só existe uma diretoria de CRAS.

### B.4 CRAS vs NAICA — mesmo padrão, implementações diferentes

**Observação**: Ambos têm `unit_name`, ambos usam `get_or_create(directorate, month, year, unit_name)`, ambos têm formulários com seções. Mas:

- `CrasReport` tem `directorate = ForeignKey(null=True, blank=True)` — permite NULL
- `NaicaReport` tem `directorate = ForeignKey(...)` — NOT NULL implícito

O banco para `cras_reports` tem `directorate_id uuid` nullable. O banco para `naica_reports` tem `directorate_id uuid NOT NULL`.

### B.5 CEAI usa tabela submissions compartilhada

**Inferência**: `apps.ceai.models.Submission` e `apps.directorates.models.MonthlySubmission` apontam para a mesma tabela física (`submissions`). Isso significa que o CEAI e outras diretorias que usam `submissions` compartilham constraints e schema. Qualquer ALTER TABLE na `submissions` afeta ambos os apps.

### B.6 Apps em desenvolvimento (poprua, casamulher)

**Status**: Templates existem mas podem estar incompletos. Models existem, views existem. `poprua` não tem `admin.py` (vazio). `casamulher` não tem `admin.py`.

### B.7 Campos calculados automaticamente no formulário (não editáveis diretamente)

Alguns campos numéricos não são preenchidos manualmente — são somas/razões de outros campos do mesmo relatório, calculadas ao vivo em JS (para exibição) e sempre recalculadas de novo em `Form.clean()` no servidor (o valor vindo do POST é ignorado, mesmo que o campo já esteja `disabled` no HTML).

- **`beneficios_reports.total_visitas`** — Confirmado (2026-08-13, decisão explícita do usuário): soma de `visitas_cadunico + visita_nucleo_habitacao + visita_cesta_fraldas_colchoes + visita_dmae + visitas_pro_pao`. Ver `BeneficiosReportForm.clean()`.
- **`qualificacao_reports.resumo_taxa_ocupacao`** — Confirmado (2026-08-13, pergunta de alinhamento respondida pelo usuário): `resumo_vagas_ocupadas / resumo_vagas × 100`, arredondado a 2 casas decimais; `0.00` quando `resumo_vagas` é 0 (evita divisão por zero). Ver `QualificacaoReportForm.clean()`.

**Observação**: a edição rápida (quick-edit, inline na tabela "Ver Dados") NÃO passa por esse recálculo — só o formulário principal (`*CreateUpdateView`) garante o valor correto. Um admin editando um dos campos-fonte via quick-edit pode deixar o total/taxa dessincronizado até o próximo salvamento pelo formulário.

- **`visits.atendimento.presentes.total`** — Confirmado (2026-08-16, bug real reportado pelo usuário): soma de `presentes.manha + presentes.tarde`, calculada em `normalize_visit_attendance()` (`apps/directorates/views.py`) e em JS (`updateAttendanceTotal()`, `visit_instrumental.html`). **Diferente dos exemplos acima**: `atendimento.total_mes` é um campo *separado*, de texto livre, editado manualmente pelo usuário — antes dessa correção, o mesmo cálculo sobrescrevia `total_mes` por engano (bug), fazendo parecer que era um campo calculado quando não era.

### B.8 PSE Quantitativos (Trimestral) — tabela central por OSC (Subvenção/Emendas e Fundos)

Confirmado (2026-08-16, decisão explícita do usuário): diferente dos formulários mensais normais (onde cada período é um snapshot independente), o indicador "Quantitativos (Trimestral)" do PSE **acumula por OSC** em vez de reiniciar a cada visita.

- **Armazenamento**: `Osc.pse_quantitativos` (JSONField, mesma forma de `Visit.atendimento.pse_quantitativos` — 4 indicadores × 12 meses). Coluna adicionada via `pending_alters.sql` (`oscs.pse_quantitativos`).
- **Leitura**: toda vez que uma visita daquela OSC carrega a seção de PSE (visita existente via `VisitInstrumentalView.get_object()` → `merge_osc_pse_quantitativos()`; visita nova via `VisitCreateView` passando `osc_pse_map` num `json_script` + JS `updatePseQuantitativos()` no `change` do select de OSC, já que a OSC só é escolhida no navegador), o valor exibido é a tabela central **mesclada** com o que a visita específica já tinha preenchido localmente (a visita nunca perde o que já foi digitado nela).
- **Escrita**: ao salvar a visita (rascunho ou finalizada), `write_back_osc_pse_quantitativos()` grava de volta na OSC — merge por mês/indicador, nunca um overwrite cego do objeto inteiro (então duas visitas diferentes, em épocas diferentes, editando meses diferentes, não se apagam uma à outra).
- **Regra em aberto pra o futuro** (usuário já avisou que pode mudar): hoje qualquer visita pode editar qualquer mês, mesmo de períodos já cobertos por visitas anteriores — sem trava. Se no futuro for preciso travar dados de visitas já finalizadas (só permitindo editar a partir do mês da visita atual em diante, com o passado imutável), é uma regra nova a implementar em cima do que já existe aqui, não uma reescrita.

---

## C) Perguntas de Alinhamento

### C.1 Apps com diretoria fixa
1. **`beneficios`, `poprua`, `ceai` e `sinecp` devem sempre ter exatamente UMA diretoria cada?**
   - **Resposta (2026-07-21)**: ✅ Sim, atualmente. Mas o usuário está aberto a tornar dinâmico (campo `type` na tabela `directorates`) se for benéfico.
2. **Se um admin renomear a diretoria de "Benefícios" para algo sem "benef", o app quebra.**
   - **Resposta (2026-07-21)**: O usuário está aberto a uma solução mais robusta (ex.: campo `type` na tabela `directorates`). Pendente de implementação futura.

### C.2 Unidades CRAS/NAICA
3. **As 13 unidades do CRAS (`CRAS_UNITS` hardcoded em `cras/views.py`) são fixas?**
   - **Resposta (2026-07-21)**: ✅ **SIM**. São unidades fixas, já existem todas fisicamente.
4. **Se uma nova unidade CRAS for criada, o processo é: adicionar na lista hardcoded + deploy?**
   - **Resposta (2026-07-21)**: ✅ Sim. Unidades são fixas e qualquer nova exigiria deploy.
5. **NAICA tem unidades?** O código de `naica/views.py` referencia unidades, mas não há uma lista hardcoded como o CRAS.
   - **PENDENTE** — não abordado pelo usuário.

### C.3 Duas diretorias com mesmo nome/slug
6. **Já aconteceu de existirem duas diretorias cujo nome gera o mesmo slug?** O converter pega a primeira — deveria dar erro em vez de comportamento silencioso?

### C.4 CEAI e Submissions
7. **A tabela `submissions` ainda é usada por outras diretorias além do CEAI?** Se não, o model `MonthlySubmission` em directorates pode ser removido?
8. **O CEAI ainda coleta dados via `submissions` ou migrou para `ceai_categorias`/`ceai_oficinas`?** As views do CEAI parecem usar ambos.

---

## D) Esboço de Cenários Given-When-Then

### D.1 Navegação para diretoria CRAS
> **Status**: Regra explícita — confirmada.

```
Dado que existe uma Directorate com name="CRAS"
Quando o usuário acessa /cras/<slug-da-diretoria>/
Então o sistema exibe o dashboard do CRAS com as 13 unidades
E os dados são filtrados pela diretoria correspondente
```

### D.2 Benefícios — diretoria fixa
> **Status**: Regra explícita — confirmada.

```
Dado que existe uma Directorate com name contendo "benef"
Quando o usuário acessa /beneficios/painel/
Então o sistema encontra a diretoria via icontains("benef")
E exibe o dashboard de benefícios
```

### D.3 Duas diretorias com mesmo slug — PENDENTE DE ALINHAMENTO
> **Status**: Depende da resposta C.3

```
Dado [definir após alinhamento]
Quando [definir após alinhamento]
Então [definir após alinhamento]
```

### D.4 Nova unidade CRAS — PENDENTE DE ALINHAMENTO
> **Status**: Depende da resposta C.2

```
Dado [definir após alinhamento]
Quando [definir após alinhamento]
Então [definir após alinhamento]
```

---

## Changelog

| Data | Mudança | Motivo |
|------|---------|--------|
| 2026-07-21 | Criação do arquivo | Mapeamento de models de report por diretoria |
| 2026-07-21 | Respostas Q1-Q4 confirmadas | Unidades CRAS fixas, apps com diretoria fixa confirmados, abertura para campo type |
| 2026-08-13 | Adicionada seção B.7 (campos calculados: `beneficios_reports.total_visitas`, `qualificacao_reports.resumo_taxa_ocupacao`) | Fórmulas confirmadas com o usuário ao implementar o cálculo automático desses campos no formulário |
| 2026-08-16 | B.7 ganhou `visits.atendimento.presentes.total`; nova seção B.8 (`Osc.pse_quantitativos`, tabela central por OSC) | Corrigido bug real de Total/Mês sendo sobrescrito; regra de acumulação do PSE Quantitativos confirmada explicitamente pelo usuário |
