from __future__ import annotations

from unittest.mock import patch

import pytest

from app import embed


def test_gemini_chat_normalizes_text_and_usage_for_existing_trace_code() -> None:
    native = {
        "candidates": [
            {"content": {"parts": [{"text": '{"route":"answer"}'}]}}
        ],
        "usageMetadata": {
            "promptTokenCount": 12,
            "candidatesTokenCount": 5,
        },
    }
    payload = {
        "model": "gemini-test",
        "format": "json",
        "options": {"temperature": 0.0},
        "messages": [
            {"role": "system", "content": "Return JSON."},
            {"role": "user", "content": "Classify this."},
        ],
    }

    with patch.object(embed, "_gemini_request", return_value=native) as request:
        result = embed._gemini_chat_post(payload)

    assert result == {
        "model": "gemini-test",
        "message": {"content": '{"route":"answer"}'},
        "prompt_eval_count": 12,
        "eval_count": 5,
    }
    sent = request.call_args.args[2]
    assert sent["systemInstruction"]["parts"][0]["text"] == "Return JSON."
    assert sent["generationConfig"]["responseMimeType"] == "application/json"


def test_gemini_embedding_uses_retrieval_task_and_configured_dimension() -> None:
    native = {"embedding": {"values": [0.25] * embed.EMBED_DIM}}

    with patch.object(embed, "_gemini_request", return_value=native) as request:
        result = embed._gemini_embed_post(
            {
                "model": "gemini-embedding-test",
                "prompt": "reset an API key",
                "task_type": "RETRIEVAL_QUERY",
            }
        )

    assert len(result["embedding"]) == embed.EMBED_DIM
    sent = request.call_args.args[2]
    assert sent["taskType"] == "RETRIEVAL_QUERY"
    assert sent["outputDimensionality"] == embed.EMBED_DIM


def test_missing_gemini_key_fails_without_attempting_network() -> None:
    with patch.object(embed, "GEMINI_API_KEY", ""):
        with pytest.raises(embed.GeminiError, match="not configured"):
            embed._gemini_request("gemini-test", "generateContent", {})


def test_provider_gateway_keeps_ollama_selectable() -> None:
    expected = {"message": {"content": "local"}}
    with (
        patch.object(embed, "LLM_PROVIDER", "ollama"),
        patch.object(embed, "_ollama_post", return_value=expected) as local,
    ):
        result = embed._post("/api/chat", {"model": "local-test"})

    assert result is expected
    local.assert_called_once()

