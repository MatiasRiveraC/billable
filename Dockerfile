FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Invoices are stored in a volume mounted at /data/facturas (see docker-compose.yml).
# The directory is created here in case no volume is mounted.
RUN mkdir -p /data/facturas

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FACTURAS_DIR=/data/facturas

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "app:app"]
