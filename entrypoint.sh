#!/bin/sh
set -e

# Volumes montados em runtime (media_volume) podem existir com dono != appuser
# (ex.: criados antes do container passar a rodar sem privilegio, ou por algum
# outro motivo). Corrige aqui, ainda como root, antes de trocar de usuario -
# sem isso, uploads (evidencias de visita, etc.) falham com PermissionError.
mkdir -p /app/media
chown -R appuser:appgroup /app/media

echo "Aguardando banco de dados..."
until python -c "
import os, sys
try:
    import psycopg
    conn = psycopg.connect(
        host=os.environ.get('DB_HOST', 'db'),
        port=int(os.environ.get('DB_PORT', 5432)),
        dbname=os.environ.get('DB_NAME', 'postgres'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', 'postgres'),
        connect_timeout=3,
    )
    conn.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    echo "Banco não disponível, aguardando..."
    sleep 2
done
echo "Banco disponível."

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "$DJANGO_DEBUG" = "1" ]; then
    echo "Starting in DEBUG environment (auto reload enabled)..."
    exec su appuser -s /bin/sh -c "python manage.py runserver 0.0.0.0:8000"
else
    echo "Starting in PRODUCTION environment (Gunicorn enabled)..."
    exec su appuser -s /bin/sh -c "gunicorn --bind 0.0.0.0:8000 config.wsgi:application"
fi
