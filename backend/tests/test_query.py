from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.retrieval import Hit


class FakeRetrieval:
    """Stands in for the real vector store so tests are fast and need no Ollama."""

    def __init__(self, *args, **kwargs):
        pass

    def retrieve(self, question, top_k):
        return [Hit(text="Cairo is the capital of Egypt.", source="geo.pdf", page=1, score=0.9)]


class FakeLowScoreRetrieval(FakeRetrieval):
    def retrieve(self, question, top_k):
        return [Hit(text="Unrelated text.", source="geo.pdf", page=2, score=0.05)]


class FakeGeneration:
    def __init__(self, *args, **kwargs):
        pass

    def generate(self, question, hits):
        return "Cairo is the capital of Egypt [1]."


def make_client(retrieval_cls):
    with patch("app.main.RetrievalService", retrieval_cls), patch(
        "app.main.GenerationService", FakeGeneration
    ):
        with TestClient(app) as client:
            yield client


@pytest.fixture
def client():
    yield from make_client(FakeRetrieval)


@pytest.fixture
def low_score_client():
    yield from make_client(FakeLowScoreRetrieval)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_query_happy_path(client):
    response = client.post("/query", json={"question": "What is the capital of Egypt?"})
    assert response.status_code == 200
    body = response.json()
    assert "Cairo" in body["answer"]
    assert body["sources"] == ["[1] geo.pdf (page 1)"]


def test_query_missing_question_returns_422(client):
    response = client.post("/query", json={})
    assert response.status_code == 422


def test_query_empty_question_returns_422(client):
    response = client.post("/query", json={"question": "   "})
    assert response.status_code == 422


def test_irrelevant_question_returns_not_found(low_score_client):
    response = low_score_client.post("/query", json={"question": "Who won the 1998 World Cup?"})
    assert response.status_code == 200
    assert "could not find" in response.json()["answer"].lower()
    assert response.json()["sources"] == []
