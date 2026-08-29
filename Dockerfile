FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system teluai && useradd --system --gid teluai --create-home teluai

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN chown -R teluai:teluai /app
USER teluai

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3)"

# app.server is the canonical production composition boundary. It assembles
# authentication, workspace isolation, canonical chat transport, Language
# Space routes, and the Melimi Lab on top of the FastAPI application.
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
