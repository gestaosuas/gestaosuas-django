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
