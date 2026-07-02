#!/bin/sh

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "$DJANGO_DEBUG" = "1" ]; then
    echo "Starting in DEBUG environment (auto reload enabled)..."
    exec python manage.py runserver 0.0.0.0:8000
else
    echo "Starting in PRODUCTION environment (Gunicorn enabled)..."
    exec gunicorn --bind 0.0.0.0:8000 config.wsgi:application
fi
