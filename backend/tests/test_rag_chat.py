"""Unit and Integration Tests for Collectorate RAG Engine and Chat Router."""

import pytest
from fastapi.testclient import TestClient
from server import app
from pipeline.rag_engine import CollectorateRAGEngine

client = TestClient(app)


def test_rag_engine_greeting():
    rag = CollectorateRAGEngine()
    res = rag.query("hi", officer_id="OFC001")
    assert res is not None
    assert "answer" in res
    assert "வணக்கம் அலுவலர் OFC001" in res["answer"]
    assert "sources" in res


def test_rag_engine_knowledge_patta():
    rag = CollectorateRAGEngine()
    res = rag.query("பட்டா பெயர் மாறுதல் விதிமுறைகள் என்ன?", officer_id="OFC001")
    assert res is not None
    assert "answer" in res
    assert ("பட்டா" in res["answer"] or "வருவாய்" in res["answer"])


def test_rag_engine_knowledge_pension():
    rag = CollectorateRAGEngine()
    res = rag.query("முதியோர் உதவித்தொகை தகுதிகள் என்ன?", officer_id="OFC001")
    assert res is not None
    assert "answer" in res
    assert ("முதியோர்" in res["answer"] or "ஓய்வூதியம்" in res["answer"] or "ரூ.1,000" in res["answer"])


def test_api_chat_endpoint_greeting():
    payload = {
        "message": "வணக்கம்",
        "officer_id": "OFC001",
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "blocks" in data
    assert len(data["blocks"]) > 0
    assert "வணக்கம் அலுவலர் OFC001" in data["blocks"][0]["content"]


def test_api_chat_endpoint_with_attachment_text():
    # Test message with attachment tag
    payload = {
        "message": "[இணைப்பு: Press_Release_sample.pdf] இந்த ஆவணம் எதைப் பற்றியது?",
        "officer_id": "OFC001",
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "blocks" in data
    content = data["blocks"][0]["content"]
    assert len(content) > 0
    assert "ஆவண" in content or "ஈரோடு" in content
