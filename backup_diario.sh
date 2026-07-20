#!/bin/bash
# ============================================================
# Gestaosuas-django — Backup diário (sem deploy)
# Uso: agendado via cron (ver CLAUDE.md, seção "Gotchas operacionais da VPS")
#   0 2 * * * /bin/bash /caminho/do/projeto/backup_diario.sh
# Faz só o dump + retenção — nunca mexe em código nem containers da app.
# ============================================================
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="/DATA/AppData/gestaosuas_backups"
DATE=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="gestaosuas_${DATE}.dump"
LOG="$APP_DIR/backup_diario.log"
KEEP=10

if [ -f "$APP_DIR/.env" ]; then
    set -a
    source "$APP_DIR/.env"
    set +a
fi
DB_NAME="${DB_NAME:-postgres}"
DB_USER="${DB_USER:-postgres}"

{
    echo "===================================="
    echo "  Backup diário iniciado: $(date '+%d/%m/%Y %H:%M:%S')"
    echo "===================================="

    mkdir -p "$BACKUP_DIR"
    docker exec gestaosuas_db pg_dump -U "$DB_USER" -Fc "$DB_NAME" > "$BACKUP_DIR/$DUMP_FILE"
    echo "Backup local: $BACKUP_DIR/$DUMP_FILE ($(du -sh "$BACKUP_DIR/$DUMP_FILE" | cut -f1))"

    # Retenção local: mantém só os $KEEP mais recentes
    BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/*.dump 2>/dev/null | wc -l)
    if [ "$BACKUP_COUNT" -gt "$KEEP" ]; then
        ls -1t "$BACKUP_DIR"/*.dump | tail -n +$((KEEP + 1)) | xargs rm -f
        echo "Retenção local: mantidos os $KEEP mais recentes."
    fi

    # Cópia para o Google Drive (opcional, best-effort — ver atualizar.sh)
    if [ -z "${GDRIVE_DIR:-}" ]; then
        echo "Google Drive: pulado (GDRIVE_DIR não definido no .env)."
    elif mkdir -p "$GDRIVE_DIR" 2>/dev/null && cp "$BACKUP_DIR/$DUMP_FILE" "$GDRIVE_DIR/$DUMP_FILE" 2>/dev/null; then
        echo "Google Drive: $GDRIVE_DIR/$DUMP_FILE"
        GDRIVE_COUNT=$(ls -1 "$GDRIVE_DIR"/*.dump 2>/dev/null | wc -l)
        if [ "$GDRIVE_COUNT" -gt "$KEEP" ]; then
            ls -1t "$GDRIVE_DIR"/*.dump | tail -n +$((KEEP + 1)) | xargs rm -f
            echo "Retenção no Drive: mantidos os $KEEP mais recentes."
        fi
    else
        echo "AVISO: falha ao copiar para o Google Drive (mount disponível?)."
    fi

    echo "Backup diário concluído: $(date '+%d/%m/%Y %H:%M:%S')"
    echo ""
} >> "$LOG" 2>&1
