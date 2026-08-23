"""Adapter that observes the real Sentinel/AgentOps graph safely.

Only external side-effect boundaries are replaced: n8n execution, approval-row
persistence, run-row persistence, and Langfuse export.  The production router,
retriever, answerer, critic, parameter extractors, tool registry, graph, trace
accounting, and audit collection all run unchanged.
"""
from __future__ import annotations

import contextlib
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

from evals.schema import GoldenCase, Observation

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


class AgentOpsAdapter:
    """Execute one case through `app.graph.run` with recorded safe boundaries."""

    def __init__(self, *, export_langfuse: bool = False) -> None:
        self.export_langfuse = export_langfuse
        self._run_number = 0
        self._queue_number = 0

    @staticmethod
    def registered_tools() -> set[str]:
        from app import tools

        return set(tools.REGISTRY)

    def run(self, case: GoldenCase) -> Observation:
        return self._run_request(case, case.user_input)

    def run_multi_turn(self, case: GoldenCase) -> Observation:
        from app.conversation import resolve_turns

        turns = case.raw.get("turns")
        if not isinstance(turns, list):
            raise ValueError("multi-turn case must contain a structured turns list")
        request, conversation = resolve_turns(turns)
        observation = self._run_request(case, request)
        observation.trace_metadata["conversation"] = conversation
        return observation

    def _run_request(self, case: GoldenCase, request: str) -> Observation:
        from app import audit, lf, router, tools, trace
        from app.embed import OllamaError
        from app.graph import run as run_graph

        execution_calls: list[dict[str, Any]] = []
        queue_calls: list[dict[str, Any]] = []
        captured_audit: list[dict[str, Any]] = []
        captured_trace: dict[str, Any] = {}
        idempotency_ledger: dict[str, dict[str, Any]] = {}
        fault_scenario = case.raw.get("fault_scenario") or case.expected.get("fault_scenario")
        fault_kind = (
            str(fault_scenario.get("kind", ""))
            if isinstance(fault_scenario, dict)
            else str(fault_scenario or "")
        )

        def fake_post_json(url: str, payload: dict, timeout: int) -> dict:
            if fault_kind == "tool_timeout":
                raise tools.ToolError("simulated tool timeout")
            execution_calls.append({"url": url, "payload": dict(payload), "timeout": timeout})
            return {"ok": True, "id": f"eval-{case.id}-{len(execution_calls)}"}

        def fake_enqueue(name: str, params: dict[str, Any], **context: Any) -> int:
            nonlocal queue_calls
            if fault_kind == "approval_queue_failure":
                raise RuntimeError("simulated approval queue failure")
            payload = tools.validate(name, params)
            self._queue_number += 1
            queue_calls.append(
                {"queue_id": self._queue_number, "tool": name, "params": payload, **context}
            )
            return self._queue_number

        def fake_log_run(request: str, state: dict, usage: Any, **_: Any) -> int:
            self._run_number += 1
            captured_trace.update(
                {
                    "request": request,
                    "state_route": state.get("route"),
                    "state_reason": state.get("reason"),
                    "usage": usage.summary(),
                }
            )
            return self._run_number

        def fake_audit_flush(run_id: int | None, steps: list[Any], **_: Any) -> None:
            for seq, item in enumerate(steps):
                captured_audit.append(
                    {"run_id": run_id, "seq": seq, "step": item.step, "detail": item.detail}
                )

        def idem_lookup(key: str, **_: Any) -> dict[str, Any] | None:
            value = idempotency_ledger.get(key)
            return dict(value) if value is not None else None

        def idem_store(key: str, name: str, result: dict, **_: Any) -> None:
            idempotency_ledger[key] = dict(result)

        patches = [
            patch.object(tools, "_post_json", side_effect=fake_post_json),
            patch.object(tools, "enqueue", side_effect=fake_enqueue),
            patch.object(tools, "set_run_id", return_value=None),
            patch.object(tools, "_idem_lookup", side_effect=idem_lookup),
            patch.object(tools, "_idem_store", side_effect=idem_store),
            patch.object(trace, "log_run", side_effect=fake_log_run),
            patch.object(audit, "flush", side_effect=fake_audit_flush),
        ]
        if fault_kind == "router_timeout":
            patches.append(
                patch.object(
                    router,
                    "_post",
                    side_effect=OllamaError("simulated router timeout"),
                )
            )
        elif fault_kind == "malformed_router_response":
            patches.append(
                patch.object(
                    router,
                    "_post",
                    return_value={"message": {"content": "{not valid json"}},
                )
            )
        if not self.export_langfuse:
            # Starting no trace makes record_chat/span/finish safe no-ops while
            # leaving the actual model and graph path intact.
            patches.extend(
                [
                    patch.object(lf, "start", return_value=None),
                    patch.object(lf, "finish", return_value=None),
                    patch.object(lf, "span", return_value=None),
                ]
            )

        started = time.perf_counter()
        with contextlib.ExitStack() as stack:
            for item in patches:
                stack.enter_context(item)
            state = run_graph(request)
            if fault_kind == "duplicate_request":
                state = run_graph(request)
        wall_latency = int((time.perf_counter() - started) * 1000)

        decision = state.get("decision")
        action = state.get("action") or {}
        usage = state.get("usage") or {}
        hits = state.get("hits") or []
        selected_tool = action.get("tool")
        params = self._extract_tool_params(action)
        parameter_valid: bool | None = None
        if selected_tool:
            try:
                tools.validate(selected_tool, params)
                parameter_valid = True
            except Exception:
                parameter_valid = False

        router_route = state.get("route")
        final_route = router_route
        if bool(state.get("escalated", False)) and router_route != "spam":
            final_route = "escalate"

        return Observation(
            router_route=router_route,
            route=final_route,
            intent=getattr(decision, "intent", None),
            retrieval_performed=any(step["step"] == "retrieve" for step in captured_audit),
            retrieved_chunks=[
                {
                    "id": hit.id,
                    "doc": hit.doc,
                    "citation_id": hit.citation_id,
                    "heading": hit.heading,
                    "content": hit.content,
                    "score": hit.score,
                    "similarity": hit.similarity,
                }
                for hit in hits
            ],
            citations=list(state.get("citations") or []),
            selected_tool=selected_tool,
            tool_parameters=params,
            parameter_valid=parameter_valid,
            approval_required=(
                bool(queue_calls)
                or action.get("status") == "pending_approval"
                or action.get("risk_level") == "high"
            ),
            tool_executed=bool(execution_calls),
            tool_execution_count=len(execution_calls),
            escalation=bool(state.get("escalated", False)),
            final_response=state.get("answer", ""),
            reason=state.get("reason"),
            audit_steps=captured_audit,
            latency_ms=usage.get("latency_ms", wall_latency),
            model=usage.get("model"),
            provider="ollama",
            llm_calls=usage.get("llm_calls"),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
            cost_usd=usage.get("cost_usd"),
            run_id=state.get("run_id"),
            fallback_used=fault_kind in {
                "router_timeout",
                "malformed_router_response",
                "tool_timeout",
                "approval_queue_failure",
            },
            retries=1 if fault_kind == "duplicate_request" else 0,
            duplicate_execution_count=(
                len(execution_calls) if fault_kind == "duplicate_request" else None
            ),
            trace_metadata={
                **captured_trace,
                "router_route": router_route,
                "final_route": final_route,
                "external_execution_calls": execution_calls,
                "approval_queue_calls": queue_calls,
                "langfuse_exported": self.export_langfuse,
                "fault_scenario": fault_scenario,
            },
        )

    def route(self, case: GoldenCase) -> Observation:
        """Run only the production router for routing-category evaluations."""
        from app import lf, trace
        from app.router import route as route_request

        started = time.perf_counter()
        with patch.object(lf, "record_chat", return_value=None), trace.track() as usage:
            decision = route_request(case.user_input)
        wall_latency = int((time.perf_counter() - started) * 1000)
        summary = usage.summary()
        return Observation(
            router_route=decision.route,
            route=decision.route,
            intent=decision.intent,
            escalation=decision.route == "escalate",
            reason="router_only_evaluation",
            latency_ms=summary.get("latency_ms", wall_latency),
            model=summary.get("model"),
            provider="ollama",
            llm_calls=summary.get("llm_calls"),
            prompt_tokens=summary.get("prompt_tokens"),
            completion_tokens=summary.get("completion_tokens"),
            total_tokens=summary.get("total_tokens"),
            cost_usd=summary.get("cost_usd"),
            trace_metadata={"evaluation_scope": "routing"},
        )

    @staticmethod
    def _extract_tool_params(action: dict[str, Any]) -> dict[str, Any]:
        metadata = {
            "tool",
            "risk_level",
            "status",
            "ticket_id",
            "queue_id",
            "critic",
            "error",
        }
        return {key: value for key, value in action.items() if key not in metadata}
