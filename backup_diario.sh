#!/bin/bash
# ============================================================
# Gestaosuas-django - Backup diario (sem deploy)
# Uso: agendado via cron (ver CLAUDE.md, secao "Gotchas operacionais da VPS")
#   0 2 * * * /bin/bash /caminho/do/projeto/backup_diario.sh
# Faz so o dump (com criptografia opcional) + retencao + notificacao
# Discord - nunca mexe em codigo nem containers da app.
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

notificar_discord() {
    # $1=titulo  $2=descricao (\n vira quebra de linha)  $3=cor decimal
    [ -z "${DISCORD_WEBHOOK_URL:-}" ] && return 0
    curl -s -H "Content-Type: application/json" \
        -d "{\"embeds\":[{\"title\":\"$1\",\"description\":\"$2\",\"color\":$3}]}" \
        "$DISCORD_WEBHOOK_URL" >> "$LOG" 2>&1
}

DUMP_OK=0
DRIVE_OK=0
DRIVE_TXT="pulado (GDRIVE_DIR nao definido)"

{
    echo "===================================="
    echo "  Backup diario iniciado: $(date '+%d/%m/%Y %H:%M:%S')"
    echo "===================================="

    mkdir -p "$BACKUP_DIR"
    if docker exec gestaosuas_db pg_dump -U "$DB_USER" -Fc "$DB_NAME" > "$BACKUP_DIR/$DUMP_FILE" 2>>"$LOG"; then
        # Criptografia opcional (best-effort, igual GDRIVE_DIR - ver atualizar.sh)
        if [ -n "${BACKUP_ENCRYPTION_PASSPHRASE:-}" ]; then
            openssl enc -aes-256-cbc -pbkdf2 -salt \
                -in "$BACKUP_DIR/$DUMP_FILE" \
                -out "$BACKUP_DIR/$DUMP_FILE.enc" \
                -pass "env:BACKUP_ENCRYPTION_PASSPHRASE"
            rm "$BACKUP_DIR/$DUMP_FILE"
            DUMP_FILE="$DUMP_FILE.enc"
            echo "Backup local (criptografado): $BACKUP_DIR/$DUMP_FILE ($(du -sh "$BACKUP_DIR/$DUMP_FILE" | cut -f1))"
        else
            echo "AVISO: BACKUP_ENCRYPTION_PASSPHRASE nao definida no .env - backup salvo sem criptografia."
            echo "Backup local: $BACKUP_DIR/$DUMP_FILE ($(du -sh "$BACKUP_DIR/$DUMP_FILE" | cut -f1))"
        fi
    else
        echo "ERRO: pg_dump falhou."
        rm -f "$BACKUP_DIR/$DUMP_FILE"
    fi
} >> "$LOG" 2>&1

if [ -s "$BACKUP_DIR/$DUMP_FILE" ]; then
    DUMP_OK=1
fi

if [ "$DUMP_OK" -eq 1 ]; then
    {
        # Retencao local: mantem so os $KEEP mais recentes
        BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/*.dump* 2>/dev/null | wc -l)
        if [ "$BACKUP_COUNT" -gt "$KEEP" ]; then
            ls -1t "$BACKUP_DIR"/*.dump* | tail -n +$((KEEP + 1)) | while read f; do rm -f "$f"; done
            echo "Retencao local: mantidos os $KEEP mais recentes."
        fi

        # Copia para o Google Drive (opcional, best-effort)
        if [ -z "${GDRIVE_DIR:-}" ]; then
            echo "Google Drive: pulado (GDRIVE_DIR nao definido no .env)."
        elif mkdir -p "$GDRIVE_DIR" 2>/dev/null && cp "$BACKUP_DIR/$DUMP_FILE" "$GDRIVE_DIR/$DUMP_FILE" 2>/dev/null; then
            echo "Google Drive: $GDRIVE_DIR/$DUMP_FILE"
            GDRIVE_COUNT=$(ls -1 "$GDRIVE_DIR"/*.dump* 2>/dev/null | wc -l)
            if [ "$GDRIVE_COUNT" -gt "$KEEP" ]; then
                ls -1t "$GDRIVE_DIR"/*.dump* | tail -n +$((KEEP + 1)) | while read f; do rm -f "$f"; done
                echo "Retencao no Drive: mantidos os $KEEP mais recentes."
            fi
        else
            echo "AVISO: falha ao copiar para o Google Drive (mount disponivel?)."
        fi

        echo "Backup diario concluido: $(date '+%d/%m/%Y %H:%M:%S')"
        echo ""
    } >> "$LOG" 2>&1

    if [ -z "${GDRIVE_DIR:-}" ]; then
        DRIVE_TXT="pulado (GDRIVE_DIR nao definido)"
    elif [ -f "$GDRIVE_DIR/$DUMP_FILE" ]; then
        DRIVE_OK=1
        DRIVE_TXT="✅ OK"
    else
        DRIVE_TXT="❌ FALHOU"
    fi
fi

# Notificacao no Discord — sempre dispara, uma vez por dia (cron roda 1x/dia
# pra esse app), verde se tudo certo, vermelho se o dump falhou, laranja se
# so o Drive falhou.
if [ "$DUMP_OK" -eq 0 ]; then
    echo "ALERTA: dump falhou, nada foi salvo." >> "$LOG"
    notificar_discord "❌ Backup Gestão SUAS FALHOU - $DATE" "🗄️ O pg_dump falhou — nenhum backup foi gerado." 15158332
elif [ "$DRIVE_OK" -eq 1 ]; then
    notificar_discord "✅ Backup Gestão SUAS OK - $DATE" "🗄️ Local: ✅ OK\n💾 Google Drive: $DRIVE_TXT" 3066993
else
    notificar_discord "⚠️ Backup Gestão SUAS - $DATE" "🗄️ Local: ✅ OK\n💾 Google Drive: $DRIVE_TXT" 15105570
fi
