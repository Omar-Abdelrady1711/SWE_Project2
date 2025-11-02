FROM python:3.11-slim
WORKDIR /app

# Install build/runtime deps (adjust as needed)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential git && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml* requirements.txt* /app/ 2>/dev/null || true
COPY . /app

RUN python -m pip install --upgrade pip || true
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt || true; fi

# Default entrypoint: adjust to your project's runner
CMD ["python", "-m", "src.cli"]
