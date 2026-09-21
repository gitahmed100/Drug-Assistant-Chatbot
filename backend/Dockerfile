FROM python:3.11-slim

WORKDIR /code

COPY requirements.txt .
# CPU-only PyTorch first (much smaller than the default CUDA build)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data ./data

# Ollama runs on your computer (the Docker host), not inside the container
ENV OLLAMA_HOST=http://host.docker.internal:11434

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
