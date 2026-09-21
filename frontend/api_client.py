import os

import requests
from dotenv import load_dotenv

load_dotenv()  # reads frontend/.env

# The backend URL comes from the environment - never hard-coded.
API_BASE_URL = os.getenv("API_BASE_URL", "").rstrip("/")


class APIError(Exception):
    """A friendly, user-readable error."""


def _require_url() -> str:
    if not API_BASE_URL:
        raise APIError("API_BASE_URL is not set. Copy .env.example to .env and set the backend URL.")
    return API_BASE_URL


def check_health() -> bool:
    try:
        response = requests.get(f"{_require_url()}/health", timeout=5)
        return response.status_code == 200
    except (requests.exceptions.RequestException, APIError):
        return False


def ask_question(question: str, timeout: int = 180) -> dict:
    """Call POST /query. Returns {"answer": str, "sources": list[str]} or raises APIError."""
    url = f"{_require_url()}/query"
    try:
        response = requests.post(url, json={"question": question}, timeout=timeout)
    except requests.exceptions.ConnectionError:
        raise APIError("Cannot reach the backend. Is it running (uvicorn app.main:app --reload)?")
    except requests.exceptions.Timeout:
        raise APIError("The request took too long. The model may still be loading - please try again.")

    if response.status_code == 422:
        raise APIError("Please type a valid question (at least 3 characters).")
    if response.status_code == 503:
        raise APIError("The language model is not available. Is Ollama running?")
    if response.status_code != 200:
        raise APIError(f"The backend returned an error (HTTP {response.status_code}).")
    return response.json()
