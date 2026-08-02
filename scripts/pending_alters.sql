-- pending_alters.sql
-- Idempotente — todas as colunas usam ADD COLUMN IF NOT EXISTS
-- Executado automaticamente pelo atualizar.sh em cada deploy

-- ============================================================================
-- creas_idoso_reports — estratificação por gênero (2026-07-21)
-- ============================================================================
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS paefi_total_acompanhamento integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS idoso_total_geral_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS idoso_total_geral_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS violencia_fisica_atendidas_anterior_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS violencia_fisica_atendidas_anterior_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS violencia_fisica_inseridos_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS violencia_fisica_inseridos_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS violencia_fisica_desligados_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS violencia_fisica_desligados_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS violencia_fisica_total_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS violencia_fisica_total_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS violencia_fisica_total_geral integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS abuso_sexual_atendidas_anterior_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS abuso_sexual_atendidas_anterior_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS abuso_sexual_inseridos_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS abuso_sexual_inseridos_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS abuso_sexual_desligados_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS abuso_sexual_desligados_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS abuso_sexual_total_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS abuso_sexual_total_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS abuso_sexual_total_geral integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS exploracao_sexual_atendidas_anterior_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS exploracao_sexual_atendidas_anterior_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS exploracao_sexual_inseridos_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS exploracao_sexual_inseridos_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS exploracao_sexual_desligados_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS exploracao_sexual_desligados_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS exploracao_sexual_total_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS exploracao_sexual_total_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS exploracao_sexual_total_geral integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS negligencia_atendidas_anterior_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS negligencia_atendidas_anterior_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS negligencia_inseridos_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS negligencia_inseridos_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS negligencia_desligados_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS negligencia_desligados_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS negligencia_total_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS negligencia_total_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS negligencia_total_geral integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS exploracao_financeira_atendidas_anterior_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS exploracao_financeira_atendidas_anterior_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS exploracao_financeira_inseridos_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS exploracao_financeira_inseridos_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS exploracao_financeira_desligados_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS exploracao_financeira_desligados_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS exploracao_financeira_total_masc integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS exploracao_financeira_total_fem integer DEFAULT 0;
ALTER TABLE creas_idoso_reports ADD COLUMN IF NOT EXISTS exploracao_financeira_total_geral integer DEFAULT 0;

-- ============================================================================
-- creas_pcd_reports — estratificação por gênero (2026-07-21)
-- ============================================================================
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_violencia_fisica_atendidas_anterior_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_violencia_fisica_atendidas_anterior_fem integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_violencia_fisica_inseridos_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_violencia_fisica_inseridos_fem integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_violencia_fisica_desligados_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_violencia_fisica_desligados_fem integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_violencia_fisica_total_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_violencia_fisica_total_fem integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_abuso_sexual_atendidas_anterior_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_abuso_sexual_atendidas_anterior_fem integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_abuso_sexual_inseridos_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_abuso_sexual_inseridos_fem integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_abuso_sexual_desligados_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_abuso_sexual_desligados_fem integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_abuso_sexual_total_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_abuso_sexual_total_fem integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_exploracao_sexual_atendidas_anterior_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_exploracao_sexual_atendidas_anterior_fem integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_exploracao_sexual_inseridos_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_exploracao_sexual_inseridos_fem integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_exploracao_sexual_desligados_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_exploracao_sexual_desligados_fem integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_exploracao_sexual_total_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_exploracao_sexual_total_fem integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_negligencia_atendidas_anterior_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_negligencia_atendidas_anterior_fem integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_negligencia_inseridos_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_negligencia_inseridos_fem integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_negligencia_desligados_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_negligencia_desligados_fem integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_negligencia_total_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_negligencia_total_fem integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_exploracao_financeira_atendidas_anterior_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_exploracao_financeira_atendidas_anterior_fem integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_exploracao_financeira_inseridos_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_exploracao_financeira_inseridos_fem integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_exploracao_financeira_desligados_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_exploracao_financeira_desligados_fem integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_exploracao_financeira_total_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_exploracao_financeira_total_fem integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_total_geral_masc integer DEFAULT 0;
ALTER TABLE creas_pcd_reports ADD COLUMN IF NOT EXISTS def_total_geral_fem integer DEFAULT 0;

-- ============================================================================
-- creas_protetivo_reports — estratificação por gênero + faixa etária (2026-07-21)
-- ============================================================================
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS vf_at_m0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS vf_at_m7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS vf_at_m13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS vf_at_f0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS vf_at_f7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS vf_at_f13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS vf_in_m0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS vf_in_m7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS vf_in_m13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS vf_in_f0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS vf_in_f7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS vf_in_f13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS vf_de_m0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS vf_de_m7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS vf_de_m13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS vf_de_f0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS vf_de_f7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS vf_de_f13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS as_at_m0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS as_at_m7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS as_at_m13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS as_at_f0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS as_at_f7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS as_at_f13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS as_in_m0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS as_in_m7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS as_in_m13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS as_in_f0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS as_in_f7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS as_in_f13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS as_de_m0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS as_de_m7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS as_de_m13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS as_de_f0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS as_de_f7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS as_de_f13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS es_at_m0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS es_at_m7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS es_at_m13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS es_at_f0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS es_at_f7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS es_at_f13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS es_in_m0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS es_in_m7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS es_in_m13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS es_in_f0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS es_in_f7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS es_in_f13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS es_de_m0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS es_de_m7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS es_de_m13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS es_de_f0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS es_de_f7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS es_de_f13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ng_at_m0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ng_at_m7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ng_at_m13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ng_at_f0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ng_at_f7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ng_at_f13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ng_in_m0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ng_in_m7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ng_in_m13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ng_in_f0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ng_in_f7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ng_in_f13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ng_de_m0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ng_de_m7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ng_de_m13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ng_de_f0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ng_de_f7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ng_de_f13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ti_at_m0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ti_at_m7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ti_at_m13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ti_at_f0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ti_at_f7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ti_at_f13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ti_in_m0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ti_in_m7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ti_in_m13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ti_in_f0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ti_in_f7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ti_in_f13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ti_de_m0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ti_de_m7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ti_de_m13 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ti_de_f0 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ti_de_f7 integer DEFAULT 0;
ALTER TABLE creas_protetivo_reports ADD COLUMN IF NOT EXISTS ti_de_f13 integer DEFAULT 0;

-- ============================================================================
-- qualificacao_reports — nova unidade "UDITECH Centro" em Concluintes/Atendimentos (2026-07-27)
-- ============================================================================
ALTER TABLE qualificacao_reports ADD COLUMN IF NOT EXISTS uditech_centro_concluintes integer DEFAULT 0;
ALTER TABLE qualificacao_reports ADD COLUMN IF NOT EXISTS uditech_centro_atendimentos integer DEFAULT 0;

-- ============================================================================
-- activity_logs — reaproveitada para o sino de notificacoes admin (2026-07-27)
-- updated_at corrige drift do model (herdava de TimeStampedUUIDModel mas a
-- coluna nunca existiu de verdade - tabela nunca tinha sido usada ate agora).
-- read_at e novo: NULL = nao lida, timestamp = quando foi lida (estado global,
-- nao por admin).
-- ============================================================================
ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now();
ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS read_at timestamptz;

-- A tabela ja tinha ~4400 linhas de atividade do app antigo (Next.js/Supabase,
-- desde marco/2026 - convencoes de action_type diferentes, algumas com a
-- corrupcao de UTF-8 conhecida). Sem isso, o sino de notificacoes estrearia
-- mostrando esse historico inteiro como "nao lido". Idempotente por causa do
-- corte de data fixo (so afeta o backlog anterior ao rollout deste recurso).
UPDATE activity_logs SET read_at = created_at WHERE read_at IS NULL AND created_at < '2026-07-28 00:00:00+00';
