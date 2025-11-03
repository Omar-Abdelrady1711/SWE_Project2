FROM python:3.10-slim

# Work from /app/bs so "src.app:app" resolves like on your machine
WORKDIR /app/bs

# Copy only pyproject first to leverage Docker layer caching
COPY pyproject.toml /app/

# (Optional) install build tools for wheels if needed by deps
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install deps declared in pyproject (fastapi/uvicorn/sqlalchemy/pydantic + your libs)
# pip understands pyproject directly (PEP 517)
RUN pip install --no-cache-dir "pip>=23.2" && \
    pip install --no-cache-dir .

# Now copy the rest of your repo (including bs/src with the app code)
COPY . /app

# Expose the port the grader expects
EXPOSE 8000

# Start the API; bind to 0.0.0.0 so the grader can reach it
CMD ["python", "-m", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
