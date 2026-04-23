FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir \
      fastapi \
      uvicorn \
      openai \
      requests \
      pydantic \
      prometheus-fastapi-instrumentator \
      ray \
      "vllm>=0.8.0"

ENV PYTHONPATH=/app

CMD ["python", "-m", "scripts.run_backend"]
