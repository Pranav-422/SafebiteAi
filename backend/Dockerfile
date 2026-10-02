FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/data/safebite.db \
    PORT=5000

RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py safety_engine.py seed_data.py schema.sql gunicorn.conf.py ./

RUN useradd --create-home --uid 10001 safebite \
 && mkdir -p /data && chown safebite:safebite /data
USER safebite
VOLUME ["/data"]
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/api/health').status==200 else 1)"

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
