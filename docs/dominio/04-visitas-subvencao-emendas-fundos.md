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
| Relatório de Visita | `parecer_tecnico` (JSONB) — herda `work_plan.objeto/objetivos/metas/atividades` + preenche `documents` |
| Relatório Final | `relatorio_final` (JSONB) |
| Parecer Conclusivo | `parecer_conclusivo` (JSONB) |

### A.5-B Estrutura de campos do Relatório Final e Parecer Conclusivo (Etapa 3) diverge entre Subvenção e Emendas e Fundos (CONFIRMADO pelo usuário em 2026-08-02)

**Regra confirmada**: os formulários de Relatório Final (`relatorio_final`) e Parecer Conclusivo (`parecer_conclusivo`) usam o mesmo template compartilhado (`report_form.html`, `VisitReportView`) para todas as diretorias do módulo, mas a **estrutura de campos diverge** entre Subvenção e Emendas e Fundos — confirmado comparando com o código-fonte atual do app Next.js legado (`Documents/Gestaosuas`), que já refletia essa mudança feita na produção original antes da migração para Django:

- **Emendas e Fundos**: mantém a estrutura original (igual ao que já existia antes desta sessão) — tem o campo **"Recurso"** (`emenda`) na seção 1 (Dados da Parceria) de ambos os relatórios; o Parecer Conclusivo tem só uma seção final "3. CONCLUSÃO" (campo `conclusao`); o Relatório Final não tem seção de conclusão separada.
- **Subvenção**: **NÃO tem mais** o campo "Recurso"/`emenda` em nenhum dos dois relatórios. Ganhou uma nova seção "6. CONCLUSÃO" (campo `conclusao`) no Relatório Final. No Parecer Conclusivo, a antiga seção "3. CONCLUSÃO" foi renomeada para **"3. SUSTENTABILIDADE E CONTINUIDADE DAS AÇÕES QUE FORAM OBJETO DA PARCERIA"** (mesmo campo `conclusao`, só o título mudou) e ganhou uma nova seção final **"4. CONCLUSÃO"** (novo campo `conclusao_final`) — esse é o campo obrigatório para finalizar (substituiu `conclusao` nessa exigência).

Implementado em `apps/directorates/views.py` (`VisitReportView.get_context_data()`, dict de defaults condicional a `is_subvencao`) e `templates/directorates/monitoring/report_form.html` (blocos `{% if is_subvencao %}`/`{% else %}` nas seções afetadas, tanto no HTML quanto na coleta/validação JS de `saveReport()`). A variável `is_subvencao` já existia no contexto (usada desde antes pela Etapa 2), só precisou ser movida para o início do método pra ficar disponível também na montagem do dict de defaults da Etapa 3.

**Correção importante (2026-07-25)**: o campo `parecer_tecnico` **é** o "Relatório de Visita" da Etapa 2 — não é um 4º relatório separado. A rota `directorates:visit-report` com `report_type='parecer_tecnico'` sempre foi usada com o rótulo "Relatório de Visita" em todos os links/botões do app (`visit_list.html`, `_tab_content.html`), mas a `VisitReportView.REPORT_LABELS` (código) tinha o rótulo desalinhado ("Relatório do Monitoramento"), e o redirect ao finalizar a Nova Visita apontava erroneamente para `relatorio_final` (Etapa 3) em vez de `parecer_tecnico` (Etapa 2). Nomenclatura correta e definitiva dos 3 campos JSONB de relatório:
- `parecer_tecnico` → **Relatório de Visita** (Etapa 2)
- `relatorio_final` → **Relatório Final** (Etapa 3a)
- `parecer_conclusivo` → **Parecer Conclusivo** (Etapa 3b)

### A.6 Permissões de Visita por Perfil (CONFIRMADO pelo usuário em 2026-07-21; refinado em 2026-07-25 e 2026-08-19)

| Ação | Admin | Diretor | Agente — Subvenção/Emendas e Fundos¹ | Agente — Outros/demais |
|------|-------|---------|---------------------------------------|--------------------------|
| Ver visitas da diretoria | Todas | Todas (visualização) | **Todas as de outros agentes** (exceto as criadas por admin) + próprias/delegadas | **Apenas as próprias + delegadas** |
| Criar Nova Visita | Sim | Sim | Sim | Sim |
| Editar visita (rascunho) | Sim | **Sim, se ele criou** / só visualiza se for de outra pessoa | **Sim**, inclusive as de outro agente da mesma diretoria (exceto criadas por admin) | **Sim** (só as próprias/delegadas) |
| Finalizar visita | Sim | **Sim, se ele criou** / não, se for de outra pessoa | **Sim**, inclusive as de outro agente | **Sim** (só as próprias/delegadas) |
| Preencher Relatório de Visita | Sim | **Sim, se ele criou** / não, se for de outra pessoa | **Sim**, inclusive as de outro agente | **Sim** (só as próprias/delegadas) |
| Relatório Final / Parecer | Sim | **Sim, se ele criou** / não, se for de outra pessoa | **Sim**, inclusive as de outro agente | **Sim** (só as próprias/delegadas) |
| Excluir visita | Sim | Não | Não | Não |

¹ **Regra nova (2026-08-19, pedido explícito do usuário)**: "somente em monitoramento, no caso em Emendas e Fundos e Subvenção, as visitas criadas por um agente da mesma diretoria podem ser vistas e editadas por outros agentes da mesma diretoria (semelhante ao que o Diretor vê)". Diferente do Diretor (que só visualiza visita alheia, nunca edita), o agente ganha **edição completa** — não só leitura — na visita de um colega da mesma diretoria. A exclusão de visitas criadas por admin usa o mesmo `get_admin_user_ids()` já aplicado ao Diretor (admin não é "um agente"), **exceto quando a visita foi explicitamente delegada** ao agente via `FormDelegation` — a delegação sempre fura a exclusão de admin, senão o caso de uso mais comum de delegar (admin cria a visita, delega pra um agente preencher) ficaria impossível de enxergar (bug real reportado pelo usuário em produção, corrigido em 2026-08-20 — ver Changelog). A diretoria "Outros" fica **fora** dessa regra nova — continua só próprias + delegadas, igual às demais diretorias fora do módulo `monitoramento`. Implementado em `VisitAccessMixin.dispatch()`, `VisitListView.get_queryset()`, `MonitoringReportListView.get_queryset()` (`apps/directorates/views.py`) e `MonitoramentoHomeView.get_context_data()` (`apps/monitoramento/views.py`), guardado por `is_subvencao_directorate()`.

**Resumo (refinado 2026-07-25, estendido 2026-08-19, corrigido 2026-08-20)**: fora de Subvenção/Emendas e Fundos, agente edita/finaliza só as próprias visitas (ou as que foram delegadas a ele via `FormDelegation`) — visita de outro agente, mesmo com acesso à diretoria, não abre nem em modo leitura. Dentro de Subvenção/Emendas e Fundos, agente vê e edita as visitas de qualquer colega da mesma diretoria (exceto as criadas por admin, a menos que explicitamente delegadas a ele), sem precisar de delegação pra colegas. Diretor vê tudo na sua diretoria em modo leitura, **exceto as visitas que ele mesmo criou**, que ele edita/finaliza normalmente igual um agente dono (esclarecido pelo usuário: diretor supervisiona o trabalho alheio, mas não fica travado no próprio). Admin tem acesso total sempre.

**Bug real corrigido (2026-08-20)**: entre 2026-08-19 e 2026-08-20, a exclusão de visitas admin-criadas nos 3 pontos acima era absoluta — nem uma `FormDelegation` conseguia furá-la, então delegar uma visita criada por admin pra um agente em Subvenção/Emendas e Fundos não tinha efeito visível nenhum (a visita ficava invisível em toda lista/dashboard do agente, apesar da delegação estar salva corretamente no banco). Reportado pelo usuário em produção ("tentamos delegar a um agente, mas parece que não funcionou"). `VisitAccessMixin.dispatch()` (acesso direto por URL) nunca teve esse bug — sempre checou `FormDelegation` incondicionalmente — mas sem nenhum link apontando pra visita em lugar nenhum da UI, isso era inatingível na prática. Corrigido incluindo `Q(id__in=delegated_visit_ids)` na condição de visibilidade dos 3 pontos, ao lado da exclusão de admin.

**Reforço de servidor (2026-07-25)**: até então, `FormDelegation` só filtrava listagens (`VisitListView`, `MonitoringReportListView`, dashboard do módulo) — as telas de edição (`VisitInstrumentalView`, `VisitReportView`, `RevertReportView`, upload/remoção de documentos e notificações, reverter visita) não validavam dono/delegação nenhuma, então qualquer agente ou diretor com acesso à diretoria conseguia abrir e salvar a visita de outra pessoa via URL direta (UUID). Corrigido com `VisitAccessMixin` (`apps/directorates/views.py`), que aplica exatamente a tabela acima antes de despachar a request; a UI (`visit_instrumental.html`, `report_form.html`) também desabilita o formulário (`<fieldset disabled>`) e esconde os botões de salvar/finalizar quando `can_edit` é falso, para não mostrar uma tela editável que na prática vai rejeitar o POST. `VisitDelegateView` (delegar visita) também passou a exigir admin ou diretor — antes qualquer agente com acesso à diretoria podia redelegar (e apagar as delegações existentes de) qualquer visita.

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

### A.9-B Dashboard de abas (Subvenção/Emendas/Outros) e diretoria "Outros" simplificada

**Regra confirmada (2026-07-24/25)**: A diretoria "Outros" usa o mesmo dashboard de abas (AJAX) de Subvenção/Emendas e Fundos, mas com escopo reduzido — só cadastro de OSC e instrumental de visita, sem Plano de Trabalho nem Relatórios/Pareceres.

Helpers em `apps/directorates/views.py`:
```python
def is_subvencao_directorate(directorate): ...  # "subvencao" no nome
def is_emendas_directorate(directorate): ...    # "emendas" ou "fundos" no nome
def is_outros_directorate(directorate): ...     # "outros" no nome
```

Em `apps/monitoramento/views.py` (`MonitoramentoHomeView.get_context_data()`):
- `is_subvencao_only = is_subvencao_directorate(directorate) or is_emendas_directorate(directorate)`
- `is_outros = is_outros_directorate(directorate)`
- `context["show_visit_tabs"] = is_subvencao_only or is_outros` → controla se o template renderiza o sistema de abas (`monitoramento/home.html` + partial `monitoramento/_tab_content.html`) em vez do dashboard genérico de `GenericMonitoringReport`
- `context["is_outros_mode"] = is_outros` → controla quantas abas aparecem
- **Cuidado já cometido uma vez**: o bloco que popula `context["oscs"]`, `context["dashboard_visits"]`, etc. precisa do mesmo `if is_subvencao_only or is_outros:` — se só o template for atualizado para mostrar abas mas o Python continuar checando `is_subvencao_only` sozinho, a página de Outros renderiza as abas mas com 0 OSCs/0 visitas (bug real encontrado via teste Playwright nesta sessão).

**Abas por tipo de diretoria**:
| Aba | Subvenção / Emendas e Fundos | Outros |
|---|---|---|
| Cadastrar OSC | Sim | Sim |
| Instrumental de Visita | Sim | Sim |
| Plano de Trabalho | Sim | **Não** |
| Relatórios e Pareceres | Sim | **Não** |

**Navegação AJAX das abas**: `MonitoramentoHomeView.get_template_names()` verifica o header `X-Requested-With` — se a requisição veio do clique numa aba (`fetch` com esse header), retorna só o partial `monitoramento/_tab_content.html`; senão retorna `monitoramento/home.html` completo (que inclui o partial via `{% include %}` dentro de `#tabContentRegion`). Isso evita reload de página inteira ao trocar de aba. A função JS `initTabInteractions()` (ícones Lucide, gráficos Chart.js, handlers de modal/busca) precisa ser chamada de novo após cada troca de aba via AJAX, já que o conteúdo é substituído via `innerHTML`.

**Abas restritas por papel dentro do MESMO dashboard (CONFIRMADO pelo usuário em 2026-07-25, corrigido no mesmo dia)**: a primeira versão desta mudança redirecionava diretor/agente pra fora do dashboard de abas, direto pra `directorates:visit-list` (a lista avulsa, standalone). O usuário pediu pra desfazer isso explicitamente — não queria essa página avulsa em uso nenhum. **Comportamento final**: diretor/agente continuam no dashboard de abas (`monitoramento:home`), só que com a navegação e o `?tab=` restritos via allowlist em `MonitoramentoHomeView.get_context_data()` — só `tab=visits` e `tab=reports` são permitidos (e `reports` nem existe pra Outros); qualquer outro valor de `?tab=` (incluindo o default `overview` e tentativas diretas de `?tab=oscs`/`?tab=plans`) cai em `visits`. `home.html` esconde os links de "Cadastrar OSC" e "Plano de Trabalho" da navegação quando `is_admin_user` é falso. Ou seja: diretor/agente sempre chegam na aba "Instrumental de Visita" (a mesma aba, dentro do mesmo dashboard — não a lista avulsa), com "Relatórios e Pareceres" como única outra aba visível.

**Formulário "Nova Visita" simplificado para Outros** (`templates/directorates/monitoring/visit_instrumental.html`, confirmado por print do usuário em 2026-07-24): a view passa `context["is_outros_visit"] = is_outros_directorate(directorate)` (em `VisitCreateView` e `VisitInstrumentalView`), e o template usa esse flag pra esconder, só para Outros:
- Campos "Total/Mês" e "Subvencionados" e o card inteiro "Usuários presentes" (seção Atendimento)
- Seção III (Forma de Acesso do Usuário)
- Seção IV (Colaboradores/RH) — inclui a tabela `#rhTable`, que não existe no DOM pra Outros; `renderRhRows()` tem guarda `if (!tbody) return;` pra não quebrar o JS de inicialização
- Seção V (Observações e Recomendações) na forma antiga — Outros usa em vez disso um único campo "Observações" simplificado
- Assinatura "Técnico Responsável 2" (só resta Técnico 1 + Responsável pela OSC)

Restam pra Outros: Identificação (OSC + data + turno), Atendimento (tipo horário, horário início/fim, "Discriminação do Serviço" = `atendimento[aplicacao_recurso]`, "Observações" = `atendimento[observacoes_atendimento]`), Fotos/Evidências, Assinaturas (Técnico 1 + Responsável).

**Gap conhecido, baixa prioridade**: a seção oculta `#reportPrintView` (só usada na impressão) ainda renderiza incondicionalmente os cabeçalhos "Identificação"/"Atendimento"/"Forma de Acesso do Usuário"/"Observações e Recomendações" mesmo para Outros — não afeta o formulário interativo, só a versão impressa.

### A.9-C Coluna "Documentos" com 3 estados (aba Instrumental de Visita)

**Regra confirmada (2026-07-24)**: na tabela de visitas dentro da aba "Instrumental de Visita" (`_tab_content.html`), o botão da coluna "Documentos" mostra 3 estados em vez de um binário liberado/bloqueado, baseado em `visit.relatorio_status` (computado em `MonitoramentoHomeView` a partir de `visit.parecer_tecnico.get("status")`, mesmo padrão já usado em `VisitListView`):

| Estado | Condição | Cor | Ícone/Texto |
|---|---|---|---|
| Preencher | visita finalizada, `parecer_tecnico` ainda não existe/rascunho não iniciado | Azul (`is-doc-pending`) | "Preencher" |
| Rascunho | `parecer_tecnico.status == "draft"` | Laranja (`is-doc-draft`) | "Rascunho" |
| Finalizado | `parecer_tecnico.status == "finalized"` | Verde (`is-doc-finalized`) | "Finalizado" |
| — | visita ainda não finalizada (`status` != `finalized`) | — | "Liberado ao finalizar" (sem link) |

### A.9-D Redirecionamento pós-ação (criar/editar/excluir/finalizar)

**Regra confirmada (2026-07-24/25)**: como existem 2 UIs distintas de listagem — a aba dentro do dashboard de Subvenção/Emendas/Outros (`monitoramento:home` + `?tab=`) e a página avulsa `directorates:visit-list`/`osc-list` usada pelas demais diretorias — todo redirect pós-ação usa um helper central em vez de sempre apontar pra `visit-list`/`osc-list`:

```python
def get_visit_list_redirect(directorate):
    if is_subvencao_directorate(directorate) or is_outros_directorate(directorate):
        return reverse("monitoramento:home", kwargs={"pk": directorate.pk}) + "?tab=visits"
    return reverse("directorates:visit-list", kwargs={"pk": directorate.pk})

def get_osc_list_redirect(directorate):
    if is_subvencao_directorate(directorate) or is_outros_directorate(directorate):
        return reverse("monitoramento:home", kwargs={"pk": directorate.pk}) + "?tab=oscs"
    return reverse("directorates:osc-list", kwargs={"pk": directorate.pk})
```

Usado como fallback em `get_success_url()`/`return_url` de `VisitInstrumentalView`, `VisitCreateView`, `VisitDelegateView`, `VisitRevertView`, `VisitDeleteView`, `VisitReportView`, `OscCreateView`, `OscUpdateView`, `OscDeleteView` — sempre respeitando um `next` explícito primeiro (query string ou campo hidden do form), e só caindo nesse helper quando não há `next`. Ao finalizar a "Nova Visita", o redirect força ir para a lista de visitas (nunca direto pra dentro de um relatório) — decisão confirmada pelo usuário em 2026-07-24.

**Bug já corrigido nesta linha (2026-07-25)**: `OscUpdateView.get_success_url()` não checava `next` nenhuma vez (sempre ia pra `osc-list`), e o link "Editar OSC"/formulário de criação inline dentro da aba não passavam `?next=`/campo hidden `next` — editar ou criar uma OSC a partir da aba de Subvenção/Emendas/Outros jogava o usuário de volta pra página avulsa antiga. Corrigido: `OscUpdateView` agora checa `next` como as demais, e `osc_form.html` (a página completa de criar/editar OSC) ganhou `context["return_url"]` (mesmo padrão de `visit_instrumental.html`) usado no link "Voltar para Lista", no botão "Cancelar" e num campo hidden `next` no próprio `<form>`.

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

**Inferência**: Um diretor/admin pode delegar uma visita específica para um agente preencher. A delegação é registrada na tabela `form_delegations` com `visit_id` + `user_id` (agente) + `delegated_by` (quem delegou). O agente então vê a visita no seu dashboard. Delegar virou admin-only em 2026-08-16 (diretor perdeu o acesso). **Feedback de sucesso/falha (2026-08-24)**: `VisitDelegateView.post()` valida os IDs marcados contra `Profile` reais antes de gravar e mostra um toast de sucesso (nomeando quem recebeu a delegação) ou de erro — antes não dava nenhum retorno visual, só um redirect silencioso, então o admin não tinha como confirmar se funcionou. **Modal pré-marca quem já está habilitado + ícone no card (2026-08-24)**: o modal "Delegar Visita" agora pré-marca os checkboxes de quem já tem `FormDelegation` naquela visita (desmarcar e salvar revoga — o delete+recreate já suportava isso, só faltava mostrar o estado atual); cards de visita (Instrumental de Visita e Relatórios e Pareceres) ganharam uma pill/indicador "Delegada" quando há alguém habilitado.

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
> **Status**: Confirmado pelo usuário em 2026-07-21; regra de agente estendida em 2026-08-19 (só Subvenção/Emendas e Fundos).

```
Dado que o agente "João" criou a visita #123 na diretoria "Subvenção"
E a visita está como rascunho
Quando João tenta editar a visita
Então ele consegue abrir o formulário e salvar alterações

Dado que o diretor "Maria" é da mesma diretoria de João
Quando Maria tenta editar a visita #123
Então ela NÃO consegue editar (somente visualização)

Dado que o agente "Pedro" é da mesma diretoria "Subvenção" mas NÃO criou a visita #123
Quando Pedro acessa a visita #123
Então ele VÊ a visita no seu dashboard e CONSEGUE editar/salvar (regra nova 2026-08-19,
     só em Subvenção/Emendas e Fundos — em qualquer outra diretoria, incluindo "Outros",
     Pedro não veria nem acessaria a visita de João)

Dado que a visita #124 na diretoria "Subvenção" foi criada por um usuário admin
Quando o agente "Pedro" (mesma diretoria) tenta acessar a visita #124
Então ele NÃO vê nem acessa (admin não conta como "um agente" pra essa regra)

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
| 2026-07-25 | Bug corrigido: `Visit.STATUS_CHOICES` não tinha `finalized`; JS de "Finalizar Visita" mandava `status=completed`, que o banco sempre rejeitava (`visits_status_check` só aceita `draft`/`finalized`) | Toda tentativa de finalizar uma visita falhava silenciosamente (exceção capturada sem log). Corrigido: JS manda `finalized`, `STATUS_CHOICES` alinhado ao banco, exceção agora loga o traceback real |
| 2026-07-25 | Campos de relatório renomeados/esclarecidos na tabela da A.5: `parecer_tecnico` é a **Etapa 2 (Relatório de Visita)**, não um 4º relatório à parte | `VisitReportView.REPORT_LABELS` tinha o rótulo desalinhado ("Relatório do Monitoramento") mesmo com todos os links do app já usando "Relatório de Visita" para essa mesma rota — confirmado pelo usuário |
| 2026-07-25 | Redirect ao finalizar a Nova Visita corrigido | Antes ia direto para `relatorio_final` (Etapa 3, errado); depois foi corrigido pra ir direto pro `parecer_tecnico` (Etapa 2); **versão final confirmada pelo usuário**: deve voltar para a lista de visitas (`visit-list`), onde o botão "Relatório de Visita" aparece habilitado — sem redirecionamento forçado para dentro de nenhum formulário |
| 2026-07-25 | Duas listagens de visita unificadas via redirect, não deletadas | Usuário pediu inicialmente pra unir as 2 tabelas de listagem de visita (avulsa vs. aba) numa só nova tela; depois recuou (`"tudo bem, não precisa deletar, só corrigir os redirecionamentos"`) — escopo final: manter as 2 telas existentes, só garantir que toda ação (criar/editar/excluir/finalizar visita e OSC) redireciona pra tela certa via `get_visit_list_redirect`/`get_osc_list_redirect` (seção A.9-D). Coluna "Documentos" da aba também ganhou os 3 estados (Preencher/Rascunho/Finalizado) que a tela avulsa já tinha (seção A.9-C) |
| 2026-07-25 | Diretoria "Outros" ganhou dashboard de abas (2 abas) + formulário de Nova Visita simplificado | Pedido do usuário com print de referência: Outros só precisa de "Cadastrar OSC" e "Instrumental de Visita" (sem Plano de Trabalho/Relatórios e Pareceres, que não se aplicam), e a Nova Visita de Outros usa um subconjunto de campos bem menor que Subvenção/Emendas (ver seção A.9-B) |
| 2026-07-25 | Bug de redirect de OSC (create/update/delete) corrigido para respeitar `next`/aba, mesma classe do bug já corrigido pra visitas | `OscUpdateView.get_success_url()` nunca checava `next`; link "Editar OSC" na aba não passava `?next=`. Testado via Playwright em Subvenção e Outros: criar/editar/excluir OSC agora sempre volta pra aba correta (ver seção A.9-D) |
| 2026-07-25 | Dashboard de abas (Cadastrar OSC/Instrumental/Plano/Relatórios) restrito a admin; diretor/agente redirecionados direto pra lista de visitas | Pedido do usuário: diretor/agente não devem ver "Cadastrar OSC" nem o dashboard de Subvenção/Emendas e Fundos/Outros — ao clicar na diretoria, vão direto pra `visit-list` (já filtrada por dono/delegação), com um botão novo "Relatórios e Pareceres" (não aparece pra Outros). Ver seção A.9-B. **[Corrigido no mesmo dia — ver entrada abaixo]**: usuário testou e não gostou de ser mandado pra `visit-list` (tela avulsa "que não estávamos usando"); voltou a usar o dashboard de abas, só que com a navegação restrita |
| 2026-07-25 | A.6 refinado: diretor edita/finaliza visitas que ELE criou (antes a tabela dizia "diretor nunca edita") | Esclarecido pelo usuário ao confirmar o comportamento de tela somente-leitura: diretor só vira supervisor/consulta nas visitas de outra pessoa, não nas próprias |
| 2026-07-25 | Reforço de servidor: `FormDelegation` passou a proteger também as telas de edição (não só listagens), via `VisitAccessMixin`; `VisitDelegateView` restrito a admin/diretor | Antes qualquer agente/diretor com acesso à diretoria conseguia abrir/salvar a visita de qualquer outra pessoa via URL direta (UUID), e qualquer agente conseguia redelegar (apagando delegações existentes) qualquer visita — brecha de segurança encontrada durante auditoria pedida pelo usuário ("revise a lógica de delegar acesso") |
| 2026-07-25 | Bug crítico corrigido: `VisitCreateView` nunca setava `Visit.user_id` — toda visita nova ficava "sem dono" | Consequência direta do item acima: com `VisitAccessMixin` bloqueando quem não é dono/delegado, um agente ficava trancado fora da própria visita recém-criada (`user_id=NULL` não bate com `request.user.id`). Achado porque o usuário reportou exatamente isso em produção/dev logo após o deploy. `VisitCreateView.post()` agora seta `user_id=request.user.pk`; as 5 visitas órfãs já existentes no banco de dev foram corrigidas via backfill uma-vez, usando `identificacao.registered_by_username` (sempre gravado, ver A.5) pra recuperar o dono real — mesmo backfill precisa rodar na VPS no deploy |
| 2026-07-25 | Navegação de abas do dashboard corrigida para allowlist, não redirect externo | Com o recuo do redirect pra `visit-list` (ver primeira entrada desta data), a restrição de abas virou: `MonitoramentoHomeView` calcula `dashboard_tab` com allowlist `{"visits", "reports"}` (só `{"visits"}` pra Outros) pra quem não é admin — qualquer `?tab=` fora disso (incluindo o default `overview`) cai em `visits`; `home.html` esconde os links de "Cadastrar OSC"/"Plano de Trabalho" via novo `is_admin_user` no contexto |
| 2026-08-02 | Nova seção A.5-B: estrutura de campos do Relatório Final/Parecer Conclusivo diverge entre Subvenção e Emendas e Fundos | Usuário confirmou que a produção original (app Next.js legado) teve mudanças nos itens desses 2 formulários só pra Subvenção (removeu campo "Recurso"/`emenda`, adicionou seção de Conclusão separada) — Emendas e Fundos mantém a estrutura antiga. `report_form.html`/`VisitReportView` atualizados para renderizar/validar/salvar os campos certos por tipo de diretoria (`is_subvencao`) |
| 2026-08-02 | Sincronização de dados do Supabase de produção (visits, oscs, work_plans, form_delegations, e várias tabelas de relatório por diretoria) pro banco de dev local | Ver seção "Migração Supabase → PostgreSQL puro (status)" do CLAUDE.md pra detalhes do processo incremental usado (sem reset, comparando IDs pra preservar dado local-only) |
| 2026-08-19 | A.6 estendido: em Subvenção/Emendas e Fundos (não em "Outros"), agente vê e edita as visitas de outros agentes da mesma diretoria (não só as próprias/delegadas), exceto as criadas por admin | Pedido explícito do usuário: "somente em monitoramento, no caso em emendas e fundos e subvenção, as visitas criadas por um agente da mesma diretoria, pode ser visto e editado por outros agentes da mesma diretoria (semelhante ao que o Diretor vê)". Diferente do Diretor (só leitura em visita alheia), o agente ganha edição completa. Implementado via `is_subvencao_directorate()` em `VisitAccessMixin`, `VisitListView`, `MonitoringReportListView` (`apps/directorates/views.py`) e `MonitoramentoHomeView` (`apps/monitoramento/views.py`); coberto por testes novos em `apps/directorates/tests.py` (`VisitAccessMixinSubvencaoPeerTests`) e `apps/monitoramento/tests.py` (`MonitoramentoAgentePeerVisibilityTests`) |
| 2026-08-20 | Bug real corrigido: em Subvenção/Emendas e Fundos, delegar uma visita criada por admin pra um agente não tinha efeito nenhum — a exclusão de visitas admin-criadas (entrada de 2026-08-19 acima) era absoluta, `FormDelegation` não furava ela em nenhuma lista/dashboard do agente | Reportado pelo usuário em produção: "tentamos delegar a um agente, mas parece que não funcionou". Investigação (agente Explore) confirmou que era regressão direta da mudança de 2026-08-19, não bug no `VisitDelegateView` em si (que sempre salvou a `FormDelegation` corretamente) nem no template/modal (checkbox `profile.pk` correto). Corrigido incluindo `Q(id__in=delegated_visit_ids)` na condição de visibilidade dos mesmos 3 pontos. De brinde, corrigidos 3 testes de `VisitDelegateViewTests` que estavam quebrados desde 2026-08-16 (esperavam diretor conseguindo delegar, mas isso virou admin-only nesse commit) — não relacionado ao bug em si, mas explica por que a suíte não pegou a regressão antes do deploy |
| 2026-08-24 | B.6 atualizado: `VisitDelegateView.post()` agora dá feedback de sucesso/falha (toast) ao delegar | Pedido explícito do usuário, testado em Emendas e Fundos: "ele deve dizer se foi delegado com sucesso ou se deu falha". A view nunca dava retorno visual nenhum — só um redirect silencioso. Validação de IDs contra `Profile` reais + `transaction.atomic()` no delete+recreate + `messages.success`/`messages.error` (renderizados automaticamente como toast global via `templates/base.html`, sem mudança de template) |
| 2026-08-24 | B.6 atualizado: modal "Delegar Visita" pré-marca quem já está habilitado (desmarcar revoga) + cards de visita ganham indicador "Delegada" | Pedido explícito do usuário: "a lista de delegar mostre quem está habilitado, para ao desmarcar, revogar o acesso" + "crie no card algum ícone pequeno indicando que aquela visita está delegada". Novo helper `build_delegation_map()` alimenta `visit.delegated_user_ids_str`/`visit.is_delegated` nos 3 pontos que renderizam cards (`VisitListView`, `MonitoringReportListView`, `MonitoramentoHomeView`); revogar já funcionava (delete+recreate a partir do POST), só faltava mostrar o estado atual |
