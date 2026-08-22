from __future__ import annotations

from app.graph import _extract_ticket_params
from app.router import Decision


def test_trailing_sentence_punctuation_is_not_part_of_email() -> None:
    params = _extract_ticket_params(
        {
            "request": "Create a support ticket for the failure; requester user@example.com.",
            "decision": Decision("action", "support_issue", "medium", True),
        }
    )
    assert params["requester_email"] == "user@example.com"
