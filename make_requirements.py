"""Writes backend/requirements.txt with the exact versions installed in your venv."""
from importlib.metadata import version

packages = {
    "fastapi": "fastapi",
    "uvicorn[standard]": "uvicorn",
    "pydantic": "pydantic",
    "pydantic-settings": "pydantic-settings",
    "ollama": "ollama",
    "chromadb": "chromadb",
    "sentence-transformers": "sentence-transformers",
    "pytest": "pytest",
    "httpx": "httpx",
}

lines = [f"{name}=={version(dist)}" for name, dist in packages.items()]
with open("backend/requirements.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\n".join(lines))
