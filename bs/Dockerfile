FROM python:3.10-slim            

WORKDIR /app

# leverage caching
COPY pyproject.toml ./           
COPY bs ./bs

RUN pip install -U pip && pip install .

# make /app/bs/src importable as top-level "src"
ENV PYTHONPATH=/app/bs

EXPOSE 8000
CMD ["sh", "-c", "python -m uvicorn src.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
