#!/bin/bash
# ============================================================
# Gestaosuas-django — Script de Atualização com Backup
# Uso: ./atualizar.sh
# Pré-requisito: rclone configurado com remote "gdrive"
# ============================================================
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="$HOME/backups/gestaosuas"
DATE=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="gestaosuas_${DATE}.dump"
GDRIVE_REMOTE="gdrive:Gestaosuas/backups"

echo ""
echo "============================================"
echo "  Gestaosuas — Atualização + Backup"
echo "  $(date '+%d/%m/%Y %H:%M:%S')"
echo "============================================"
echo ""

# ── 1. Backup do banco ─────────────────────────────────────
echo "[1/4] Fazendo backup do banco de dados..."
mkdir -p "$BACKUP_DIR"
docker exec gestaosuas_db pg_dump -U postgres -Fc postgres > "$BACKUP_DIR/$DUMP_FILE"
echo "      Salvo em: $BACKUP_DIR/$DUMP_FILE ($(du -sh "$BACKUP_DIR/$DUMP_FILE" | cut -f1))"

# ── 2. Upload para Google Drive ────────────────────────────
echo "[2/4] Enviando backup para o Google Drive..."
if command -v rclone &>/dev/null; then
    rclone copy "$BACKUP_DIR/$DUMP_FILE" "$GDRIVE_REMOTE/" --progress
    echo "      Upload concluído → $GDRIVE_REMOTE/$DUMP_FILE"
else
    echo "      AVISO: rclone não encontrado. Instale com: curl https://rclone.org/install.sh | bash"
    echo "      Backup mantido localmente em $BACKUP_DIR/$DUMP_FILE"
fi

# ── 3. Pull do GitHub ──────────────────────────────────────
echo "[3/4] Baixando atualizações do GitHub..."
cd "$APP_DIR"
git fetch origin
git reset --hard origin/master
echo "      Código atualizado para $(git log -1 --format='%h %s')"

# ── 4. Rebuild dos containers ──────────────────────────────
echo "[4/4] Reconstruindo e reiniciando containers..."
docker compose -f docker-compose.yml up -d --build
echo "      Containers reiniciados."

# ── Limpeza de backups antigos (mantém últimos 10) ─────────
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/*.dump 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt 10 ]; then
    echo ""
    echo "[*] Removendo backups antigos (mantendo os 10 mais recentes)..."
    ls -1t "$BACKUP_DIR"/*.dump | tail -n +11 | xargs rm -f
fi

echo ""
echo "============================================"
echo "  Atualização concluída com sucesso!"
echo "  Backup: $BACKUP_DIR/$DUMP_FILE"
echo "============================================"
echo ""
