FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim
WORKDIR /app
ENV FASTEMBED_CACHE_PATH=/app/models
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
RUN .venv/bin/python -c "from fastembed import TextEmbedding, SparseTextEmbedding; from fastembed.rerank.cross_encoder import TextCrossEncoder; TextEmbedding('BAAI/bge-small-en-v1.5'); SparseTextEmbedding('Qdrant/bm25'); TextCrossEncoder('Xenova/ms-marco-MiniLM-L-6-v2')" && chmod -R a+rwX /app/models
COPY app ./app
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]