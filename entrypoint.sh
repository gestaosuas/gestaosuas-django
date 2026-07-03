#!/bin/sh
set -e

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
    exec python manage.py runserver 0.0.0.0:8000
else
    echo "Starting in PRODUCTION environment (Gunicorn enabled)..."
    exec gunicorn --bind 0.0.0.0:8000 config.wsgi:application
fi
