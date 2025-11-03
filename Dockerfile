# Dockerfile (at repo root)
FROM python:3.11-slim

WORKDIR /app

# copy project metadata & code
COPY pyproject.toml ./
COPY bs ./bs

# install deps declared in pyproject
RUN pip install -U pip && pip install .

EXPOSE 8000
CMD ["uvicorn", "bs.src.app:app", "--host", "0.0.0.0", "--port", "8000"]
