-- ============================================================
-- MIGRAÇÃO: Supabase Auth → PostgreSQL puro (Django ModelBackend)
-- ============================================================
-- Executar UMA VEZ: no banco do VPS e no banco de dev local.
-- Pré-requisito: python manage.py migrate já rodou (cria accounts_user).
-- ANTES de executar: pg_dump -Fc postgres > backup_pre_migracao.dump
-- ============================================================

BEGIN;

-- ============================================================
-- PASSO 1: Copiar usuários de auth.users → accounts_user
-- ============================================================
-- Preserva os mesmos UUIDs para manter integridade com profiles,
-- submissions e demais tabelas que referenciam o id do usuário.
-- Se auth.users não existir (banco já puro), este bloco não faz nada.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'auth' AND table_name = 'users'
    ) THEN
        INSERT INTO accounts_user (
            id,
            username,
            email,
            password,
            first_name,
            last_name,
            is_staff,
            is_active,
            is_superuser,
            date_joined,
            last_login
        )
        SELECT
            au.id,
            -- username = email (único e já conhecido pelos usuários)
            au.email,
            au.email,
            -- '!' = senha inutilizável, padrão Django para contas externas
            '!',
            '',
            '',
            false,
            true,
            false,
            COALESCE(au.created_at, NOW()),
            au.last_sign_in_at
        FROM auth.users au
        WHERE au.id NOT IN (SELECT id FROM accounts_user)
        ON CONFLICT (id) DO NOTHING;

        RAISE NOTICE 'Passo 1 OK: usuários copiados de auth.users para accounts_user.';
    ELSE
        RAISE NOTICE 'Passo 1 PULADO: schema auth.users não existe neste banco.';
    END IF;
END $$;


-- ============================================================
-- PASSO 2: Remover FK de profiles → auth.users
-- ============================================================
-- O nome exato da constraint varia conforme o banco. Tentamos os
-- dois nomes mais comuns gerados pelo Supabase.
-- Após este passo, profiles.id é uma PK livre — gerenciada pelo Django.

ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_id_fkey;
ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_user_id_fkey;
-- Alguns dumps Supabase geram o nome abaixo:
ALTER TABLE profiles DROP CONSTRAINT IF EXISTS "profiles_id_fkey";

-- submissions também referencia auth.users via user_id
ALTER TABLE submissions DROP CONSTRAINT IF EXISTS submissions_user_id_fkey;
ALTER TABLE submissions DROP CONSTRAINT IF EXISTS "submissions_user_id_fkey";

-- Converter submissions.user_id para FK para accounts_user (opcional mas correto)
-- Só adiciona se a coluna existir e accounts_user tiver os dados já:
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'submissions' AND column_name = 'user_id'
    ) THEN
        -- Adiciona FK para accounts_user somente se não existir ainda
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints tc
            JOIN information_schema.constraint_column_usage ccu
              ON tc.constraint_name = ccu.constraint_name
            WHERE tc.table_name = 'submissions'
              AND tc.constraint_type = 'FOREIGN KEY'
              AND ccu.table_name = 'accounts_user'
        ) THEN
            ALTER TABLE submissions
                ADD CONSTRAINT submissions_user_id_accounts_fkey
                FOREIGN KEY (user_id) REFERENCES accounts_user(id)
                ON DELETE SET NULL;
            RAISE NOTICE 'Passo 2b: FK submissions.user_id → accounts_user adicionada.';
        END IF;
    END IF;
END $$;

DO $$ BEGIN RAISE NOTICE 'Passo 2 OK: FK de profiles/submissions para auth.users removida.'; END $$;


-- ============================================================
-- PASSO 3: Desabilitar RLS em todas as tabelas de negócio
-- ============================================================
-- Django usa managed=False e controla acesso na camada de aplicação.
-- RLS com auth.uid() não funciona fora do Supabase (sem JWT no contexto).
-- Desabilitar é seguro — as views Django já garantem autorização.

ALTER TABLE profiles                    DISABLE ROW LEVEL SECURITY;
ALTER TABLE directorates               DISABLE ROW LEVEL SECURITY;
ALTER TABLE profile_directorates       DISABLE ROW LEVEL SECURITY;
ALTER TABLE submissions                DISABLE ROW LEVEL SECURITY;

-- Tabelas de relatório (aplicar a todas que existirem no banco)
DO $$
DECLARE
    tbl TEXT;
    tables TEXT[] := ARRAY[
        'sine_reports', 'qualificacao_reports', 'naica_reports',
        'cras_reports', 'beneficios_reports',
        'creas_idoso_reports', 'creas_pcd_reports', 'creas_pop_rua_reports',
        'creas_protetivo_reports', 'creas_socioeducativo_reports',
        'protecao_especial_reports', 'casa_da_mulher_reports',
        'diversidade_reports', 'nucleo_diversidade_reports',
        'oscs', 'visits', 'monitorings_genericmonitoringreport',
        'map_units', 'map_categories', 'system_settings',
        'work_plans', 'form_delegations', 'activity_log'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = tbl
        ) THEN
            EXECUTE format('ALTER TABLE %I DISABLE ROW LEVEL SECURITY', tbl);
            RAISE NOTICE 'RLS desabilitado: %', tbl;
        END IF;
    END LOOP;
END $$;

DO $$ BEGIN RAISE NOTICE 'Passo 3 OK: RLS desabilitado em todas as tabelas de negócio.'; END $$;


-- ============================================================
-- PASSO 4: Remover políticas RLS (DROP POLICY)
-- ============================================================
-- Opcional — as políticas ficam inativas com RLS desabilitado,
-- mas removê-las limpa o schema e remove dependência de auth.uid().

DO $$
DECLARE
    pol RECORD;
BEGIN
    FOR pol IN
        SELECT schemaname, tablename, policyname
        FROM pg_policies
        WHERE schemaname = 'public'
    LOOP
        EXECUTE format(
            'DROP POLICY IF EXISTS %I ON %I.%I',
            pol.policyname, pol.schemaname, pol.tablename
        );
        RAISE NOTICE 'Policy removida: % em %', pol.policyname, pol.tablename;
    END LOOP;
END $$;

DO $$ BEGIN RAISE NOTICE 'Passo 4 OK: todas as políticas RLS removidas.'; END $$;


-- ============================================================
-- PASSO 5: Remover funções específicas do Supabase
-- ============================================================
-- is_admin() usava auth.uid() — não funciona sem Supabase JWT.
-- Funções auth.* são internas do Supabase.

DROP FUNCTION IF EXISTS public.is_admin() CASCADE;
DROP FUNCTION IF EXISTS auth.uid() CASCADE;
DROP FUNCTION IF EXISTS auth.role() CASCADE;
DROP FUNCTION IF EXISTS auth.email() CASCADE;
DROP FUNCTION IF EXISTS auth.jwt() CASCADE;

DO $$ BEGIN RAISE NOTICE 'Passo 5 OK: funções Supabase removidas (se existiam).'; END $$;


-- ============================================================
-- PASSO 6: Corrigir UNIQUE constraint de sine_reports e qualificacao_reports
-- ============================================================
-- Bug identificado: constraint original não inclui directorate_id,
-- impedindo múltiplas diretorias de ter relatório no mesmo mês/ano.

DO $$
DECLARE
    tbl TEXT;
    old_constraint TEXT;
    tables TEXT[] := ARRAY['sine_reports', 'qualificacao_reports'];
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = tbl
        ) THEN
            -- Descobrir o nome atual da constraint UNIQUE(month, year)
            SELECT tc.constraint_name INTO old_constraint
            FROM information_schema.table_constraints tc
            JOIN information_schema.constraint_column_usage ccu
              ON tc.constraint_name = ccu.constraint_name
            WHERE tc.table_name = tbl
              AND tc.constraint_type = 'UNIQUE'
              AND ccu.column_name IN ('month', 'year')
              AND tc.constraint_name NOT LIKE '%directorate%'
            LIMIT 1;

            IF old_constraint IS NOT NULL THEN
                EXECUTE format('ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I', tbl, old_constraint);
                EXECUTE format(
                    'ALTER TABLE %I ADD CONSTRAINT %I UNIQUE (directorate_id, month, year)',
                    tbl, tbl || '_directorate_month_year_key'
                );
                RAISE NOTICE 'Passo 6: constraint UNIQUE corrigida em %', tbl;
            ELSE
                RAISE NOTICE 'Passo 6: constraint já correta ou não encontrada em %', tbl;
            END IF;
        END IF;
    END LOOP;
END $$;

DO $$ BEGIN RAISE NOTICE 'Passo 6 OK: constraints UNIQUE de SINE/Qualificação corrigidas.'; END $$;


-- ============================================================
-- PASSO 7: Verificação final
-- ============================================================

-- 7a. Profiles sem accounts_user correspondente (deve retornar 0 linhas)
DO $$
DECLARE
    orphan_count INT;
BEGIN
    SELECT COUNT(*) INTO orphan_count
    FROM profiles p
    LEFT JOIN accounts_user au ON au.id = p.id
    WHERE au.id IS NULL;

    IF orphan_count > 0 THEN
        RAISE WARNING 'ATENÇÃO: % profiles sem accounts_user! Verificar manualmente.', orphan_count;
    ELSE
        RAISE NOTICE 'Passo 7a OK: todos os profiles têm accounts_user correspondente.';
    END IF;
END $$;

-- 7b. Contagens para conferência
SELECT
    (SELECT COUNT(*) FROM profiles) AS total_profiles,
    (SELECT COUNT(*) FROM accounts_user) AS total_accounts_users,
    (SELECT COUNT(*) FROM directorates) AS total_directorates;

COMMIT;

-- ============================================================
-- PÓS-MIGRAÇÃO (executar manualmente se necessário)
-- ============================================================
-- 1. Verificar que o login Django funciona:
--    python manage.py shell -c "from django.contrib.auth import get_user_model; print(get_user_model().objects.count())"
--
-- 2. Se auth schema não for mais necessário, pode ser dropado com:
--    DROP SCHEMA auth CASCADE;
--    (CUIDADO: irreversível. Confirmar que nenhuma tabela depende mais dele.)
--
-- 3. Atualizar variáveis de ambiente (.env) removendo SUPABASE_URL e SUPABASE_ANON_KEY.
