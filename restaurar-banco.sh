#!/bin/bash
# ============================================================
# Gestaosuas-django — Restaurar banco de dados
# Uso: bash restaurar-banco.sh <arquivo.dump>
#      bash restaurar-banco.sh  (baixa último backup do Drive)
# ============================================================
set -e

DUMP_FILE="$1"
DB_CONTAINER="gestaosuas_db"
DB_USER="postgres"
DB_NAME="postgres"

echo ""
echo "============================================"
echo "  Gestaosuas — Restauração do Banco"
echo "============================================"
echo ""

# ── Se não passou arquivo, baixa do Google Drive ───────────
if [ -z "$DUMP_FILE" ]; then
    if ! command -v rclone &>/dev/null; then
        echo "ERRO: rclone não instalado e nenhum arquivo informado."
        echo "Uso: bash restaurar-banco.sh <arquivo.dump>"
        exit 1
    fi
    echo "Buscando backup mais recente no Google Drive..."
    LATEST=$(rclone ls gdrive:Gestaosuas/backups/ | sort | tail -1 | awk '{print $2}')
    if [ -z "$LATEST" ]; then
        echo "ERRO: nenhum backup encontrado em gdrive:Gestaosuas/backups/"
        exit 1
    fi
    DUMP_FILE="/tmp/$LATEST"
    echo "Baixando: $LATEST..."
    rclone copy "gdrive:Gestaosuas/backups/$LATEST" /tmp/ --progress
fi

if [ ! -f "$DUMP_FILE" ]; then
    echo "ERRO: arquivo não encontrado: $DUMP_FILE"
    exit 1
fi

echo "Arquivo: $DUMP_FILE ($(du -sh "$DUMP_FILE" | cut -f1))"
echo ""
echo "ATENÇÃO: O banco '$DB_NAME' no container '$DB_CONTAINER' será SUBSTITUÍDO."
read -p "Confirmar? [s/N] " CONF
if [[ ! "$CONF" =~ ^[Ss]$ ]]; then
    echo "Cancelado."
    exit 0
fi

# ── Restaurar ──────────────────────────────────────────────
echo ""
echo "Restaurando banco..."

# Termina conexões ativas
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB_NAME' AND pid <> pg_backend_pid();" \
    &>/dev/null || true

# Limpa e recria o banco
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -c "DROP DATABASE IF EXISTS ${DB_NAME}_old;" &>/dev/null || true
docker exec "$DB_CONTAINER" psql -U "$DB_USER" \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB_NAME' AND pid <> pg_backend_pid();" \
    &>/dev/null || true

# Restaura com pg_restore
docker exec -i "$DB_CONTAINER" pg_restore -U "$DB_USER" -d "$DB_NAME" --clean --if-exists -v < "$DUMP_FILE" 2>&1 | tail -5

echo ""
echo "============================================"
echo "  Banco restaurado com sucesso!"
echo "  Reiniciando app..."
echo "============================================"
cd "$(dirname "$0")"
docker compose -f docker-compose.yml restart app
echo "  Pronto."
echo ""
