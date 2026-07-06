-- ============================================================
-- SETUP: Banco de desenvolvimento PostgreSQL puro
-- ============================================================
-- Executar após subir o container db:
--   docker compose up -d db
--
-- Opção A — banco fresco (sem dados):
--   psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -f scripts/setup_dev_db.sql
--   python manage.py migrate
--   python manage.py createsuperuser
--
-- Opção B — restaurar dump de produção (com dados reais):
--   pg_restore -h 127.0.0.1 -p 5432 -U postgres -d postgres \
--              --no-owner --no-acl gestaosuas_dump.dump
--   python manage.py migrate   # cria tabelas Django internas se faltarem
--   python manage.py shell -c "from django.contrib.auth import get_user_model; \
--     U = get_user_model(); \
--     u = U.objects.create_superuser('admin@dev.local','admin@dev.local','admin123'); \
--     print('Superuser criado:', u.email)"
--   # Depois rode migrate_to_pure_pg.sql para remover dependências Supabase
-- ============================================================

-- Extensão necessária para gen_random_uuid() / uuid_generate_v4()
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- O restante das tabelas Django internas (auth, sessions, admin, contenttypes)
-- é criado automaticamente via: python manage.py migrate
--
-- As tabelas de negócio (profiles, directorates, cras_reports, etc.)
-- têm managed=False no Django — devem vir do dump de produção ou ser
-- criadas manualmente com os scripts SQL do diretório supabase/migrations/
-- (executar em ordem cronológica pelo nome do arquivo).
