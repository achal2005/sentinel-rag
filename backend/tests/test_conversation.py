from __future__ import annotations

from app.conversation import resolve_turns


def test_resolves_invoice_reference() -> None:
    request, metadata = resolve_turns(
        [
            {"role": "user", "content": "The duplicate charge is invoice INV-4102."},
            {"role": "assistant", "content": "I found the invoice."},
            {"role": "user", "content": "Please cancel that invoice."},
        ]
    )
    assert request == "Please cancel invoice INV-4102."
    assert metadata["context_resolved"] is True
    assert metadata["resolved_fields"]["invoice_id"] == "INV-4102"


def test_resolves_support_issue_reference() -> None:
    request, metadata = resolve_turns(
        [
            {"role": "user", "content": "Production deploys return 503 in eu-west."},
            {"role": "assistant", "content": "Would you like support to investigate?"},
            {"role": "user", "content": "Create a support ticket for that issue."},
        ]
    )
    assert "Production deploys return 503 in eu-west" in request
    assert metadata["resolved_fields"]["issue"].startswith("Production deploys")


def test_does_not_guess_missing_invoice() -> None:
    request, metadata = resolve_turns(
        [{"role": "user", "content": "Please cancel that invoice."}]
    )
    assert request == "Please cancel that invoice."
    assert metadata["context_resolved"] is False
