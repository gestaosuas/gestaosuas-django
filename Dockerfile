FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    netcat-openbsd \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ /app/requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt

COPY . /app/

RUN rm -rf /app/.deps

RUN chmod +x /app/entrypoint.sh

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
RUN chown -R appuser:appgroup /app
# Sem USER aqui de proposito: o entrypoint precisa rodar como root por um
# instante pra corrigir a dono de volumes montados em runtime (ex.: media_volume,
# que pode ja existir com dono != appuser de antes desse setup) antes de trocar
# pra appuser e subir o servidor de fato. Ver entrypoint.sh.

EXPOSE 8000

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
