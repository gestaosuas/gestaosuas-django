#!/bin/bash
# ============================================================
# Gestaosuas-django — Configuração inicial da VPS
# Executa UMA VEZ para conectar ao GitHub e configurar rclone
# Uso: bash configurar-vps.sh
# ============================================================

APP_DIR="$HOME/AppData/Gestaosuas-django"
GITHUB_REPO="https://github.com/rdssystems/Gestaosuas-django.git"

echo ""
echo "============================================"
echo "  Gestaosuas — Configuração inicial VPS"
echo "============================================"
echo ""

# ── 1. Conectar ao GitHub ──────────────────────────────────
echo "[1/3] Configurando Git + GitHub..."
cd "$APP_DIR"

if [ -d ".git" ]; then
    echo "      Repositório git já existe. Atualizando remote..."
    git remote set-url origin "$GITHUB_REPO" 2>/dev/null || git remote add origin "$GITHUB_REPO"
else
    git init
    git remote add origin "$GITHUB_REPO"
fi

# Configura usuário git local
git config user.email "deploy@gestaosuas"
git config user.name "Gestaosuas VPS"

echo ""
echo "      IMPORTANTE: Para autenticar no GitHub, você precisará de um"
echo "      Personal Access Token (PAT) da conta rdssystems."
echo ""
echo "      Configure o token no remote URL:"
echo "      git remote set-url origin https://TOKEN@github.com/rdssystems/Gestaosuas-django.git"
echo ""
read -p "      Cole seu PAT agora (ou ENTER para pular): " PAT
if [ -n "$PAT" ]; then
    git remote set-url origin "https://${PAT}@github.com/rdssystems/Gestaosuas-django.git"
    echo "      Token configurado."
fi

# Pull do código
echo ""
echo "      Baixando código do GitHub..."
git fetch origin
git checkout -B master origin/master 2>/dev/null || git reset --hard origin/master
chmod +x atualizar.sh
echo "      Código sincronizado com GitHub. ✓"

# ── 2. Instalar rclone ─────────────────────────────────────
echo ""
echo "[2/3] Verificando rclone..."
if command -v rclone &>/dev/null; then
    echo "      rclone já instalado: $(rclone version | head -1)"
else
    echo "      Instalando rclone..."
    curl https://rclone.org/install.sh | bash
    echo "      rclone instalado. ✓"
fi

# ── 3. Configurar Google Drive ─────────────────────────────
echo ""
echo "[3/3] Configurando Google Drive (rclone)..."
echo ""
echo "      Será aberto o assistente de configuração do rclone."
echo "      Siga os passos:"
echo "        1. Digite 'n' para novo remote"
echo "        2. Nome: gdrive"
echo "        3. Tipo: drive (Google Drive)"
echo "        4. Siga as instruções para autenticar"
echo "           (precisará de um navegador OU usar headless auth)"
echo ""
read -p "      Iniciar configuração do Google Drive agora? [s/N] " CONF
if [[ "$CONF" =~ ^[Ss]$ ]]; then
    rclone config
fi

echo ""
echo "============================================"
echo "  Configuração concluída!"
echo ""
echo "  Próximos passos:"
echo "  1. Restaurar banco:  bash restaurar-banco.sh /caminho/dump.dump"
echo "  2. Atualizar app:    ./atualizar.sh"
echo "============================================"
echo ""
