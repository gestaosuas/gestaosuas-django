#!/bin/bash
# ============================================================
# Gestaosuas-django — Script de Atualização com Backup
# Uso: ./atualizar.sh
# Backup no Google Drive: opcional, via mount de pasta local (ex: CasaOS)
# configurado em GDRIVE_DIR no .env deste projeto (não versionado — o caminho
# de montagem/conta é específico da VPS e não deve viver no código público).
# ============================================================
set -eo pipefail
# pipefail é necessário porque o passo 4 (ALTER TABLEs pendentes) roda o psql
# dentro de um pipe (`| grep -c ...`) — sem pipefail, `set -e` só olha o exit
# code do grep, e uma falha real do psql (ON_ERROR_STOP=1) passaria batida,
# deixando o script seguir para o rebuild com o schema aplicado pela metade.

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
# $HOME (/DATA) pertence ao root nesta VPS (CasaOS) — usuário klismanrds não
# tem escrita direta ali. /DATA/AppData é 777, funciona como diretório de
# backups compartilhado entre os apps desta máquina.
BACKUP_DIR="/DATA/AppData/gestaosuas_backups"
DATE=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="gestaosuas_${DATE}.dump"

# `docker compose` só é reconhecido com DOCKER_CONFIG apontando para um dir
# gravável — o padrão (/DATA/.docker) pertence ao root nesta VPS.
export DOCKER_CONFIG="/tmp/dockercfg"
mkdir -p "$DOCKER_CONFIG"

# Nome/usuário reais do banco (nunca "postgres"/"postgres" nesta VPS — ver .env).
if [ -f "$APP_DIR/.env" ]; then
    set -a
    source "$APP_DIR/.env"
    set +a
fi
DB_NAME="${DB_NAME:-postgres}"
DB_USER="${DB_USER:-postgres}"

echo ""
echo "============================================"
echo "  Gestaosuas — Atualização + Backup"
echo "  $(date '+%d/%m/%Y %H:%M:%S')"
echo "============================================"
echo ""

# ── 1. Backup do banco ─────────────────────────────────────
echo "[1/5] Fazendo backup do banco de dados..."
mkdir -p "$BACKUP_DIR"
docker exec gestaosuas_db pg_dump -U "$DB_USER" -Fc "$DB_NAME" > "$BACKUP_DIR/$DUMP_FILE"

# Criptografia opcional (best-effort, igual GDRIVE_DIR): sem
# BACKUP_ENCRYPTION_PASSPHRASE no .env, o backup segue funcionando sem
# criptografia, só com aviso — nunca derruba o deploy por causa disso.
if [ -n "${BACKUP_ENCRYPTION_PASSPHRASE:-}" ]; then
    openssl enc -aes-256-cbc -pbkdf2 -salt \
        -in "$BACKUP_DIR/$DUMP_FILE" \
        -out "$BACKUP_DIR/$DUMP_FILE.enc" \
        -pass "env:BACKUP_ENCRYPTION_PASSPHRASE"
    rm "$BACKUP_DIR/$DUMP_FILE"
    DUMP_FILE="$DUMP_FILE.enc"
    echo "      Salvo (criptografado) em: $BACKUP_DIR/$DUMP_FILE ($(du -sh "$BACKUP_DIR/$DUMP_FILE" | cut -f1))"
else
    echo "      AVISO: BACKUP_ENCRYPTION_PASSPHRASE não definida no .env — backup salvo sem criptografia."
    echo "      Salvo em: $BACKUP_DIR/$DUMP_FILE ($(du -sh "$BACKUP_DIR/$DUMP_FILE" | cut -f1))"
fi

# ── 2. Copia para o Google Drive (opcional) ────────────────
# Best-effort: sem GDRIVE_DIR configurado no .env, ou falha ao copiar
# (mount ausente, sem espaço etc.), nunca deve derrubar o deploy — o
# backup local (passo 1) já está garantido.
echo "[2/5] Copiando backup para o Google Drive..."
if [ -z "${GDRIVE_DIR:-}" ]; then
    echo "      Pulado: GDRIVE_DIR não definido no .env deste projeto."
elif mkdir -p "$GDRIVE_DIR" 2>/dev/null && cp "$BACKUP_DIR/$DUMP_FILE" "$GDRIVE_DIR/$DUMP_FILE" 2>/dev/null; then
    echo "      Copiado para: $GDRIVE_DIR/$DUMP_FILE"
    # Mantém apenas os 10 backups mais recentes no Drive (mesma retenção do local).
    GDRIVE_COUNT=$(ls -1 "$GDRIVE_DIR"/*.dump* 2>/dev/null | wc -l)
    if [ "$GDRIVE_COUNT" -gt 10 ]; then
        ls -1t "$GDRIVE_DIR"/*.dump* | tail -n +11 | while read -r f; do rm -f "$f"; done
    fi
else
    echo "      AVISO: não foi possível copiar para o Google Drive (mount em $GDRIVE_DIR disponível?)."
    echo "      Backup mantido localmente em $BACKUP_DIR/$DUMP_FILE"
fi

# ── 3. Pull do GitHub ──────────────────────────────────────
echo "[3/5] Baixando atualizações do GitHub..."
cd "$APP_DIR"
git fetch origin
git reset --hard origin/master
echo "      Código atualizado para $(git log -1 --format='%h %s')"

# ── 4. Aplicar ALTER TABLEs pendentes ──────────────────────
echo "[4/5] Aplicando alterações de schema pendentes..."
ALTERS_FILE="$APP_DIR/scripts/pending_alters.sql"
if [ -f "$ALTERS_FILE" ]; then
    ALTER_COUNT=$(docker exec -i gestaosuas_db psql -U "${DB_USER:-postgres}" -d "${DB_NAME:-postgres}" -v ON_ERROR_STOP=1 < "$ALTERS_FILE" 2>&1 | grep -c "ALTER TABLE")
    echo "      $ALTER_COUNT coluna(s) verificada(s)."
else
    echo "      Nenhum $ALTERS_FILE encontrado — pulado."
fi

# ── 5. Rebuild dos containers ──────────────────────────────
echo "[5/5] Reconstruindo e reiniciando containers..."
docker compose -f docker-compose.yml up -d --build
echo "      Containers reiniciados."

# ── Limpeza de backups antigos (mantém últimos 10) ─────────
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/*.dump* 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt 10 ]; then
    echo ""
    echo "[*] Removendo backups antigos (mantendo os 10 mais recentes)..."
    ls -1t "$BACKUP_DIR"/*.dump* | tail -n +11 | while read f; do rm -f "$f"; done
fi

echo ""
echo "============================================"
echo "  Atualização concluída com sucesso!"
echo "  Backup: $BACKUP_DIR/$DUMP_FILE"
echo "============================================"
echo ""
