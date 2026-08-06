FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app

RUN useradd --create-home --uid 10001 stockbot
RUN mkdir -p /app/runtime && chown -R stockbot:stockbot /app

USER stockbot

EXPOSE 8765 8766 8767

HEALTHCHECK --interval=30s --timeout=5s --retries=3   CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8767/health', timeout=3)"

CMD ["python", "tools/run_saas_operations_server.py", "--host", "0.0.0.0", "--port", "8767"]
