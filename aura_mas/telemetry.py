"""Logging and tracing setup, shared across CLI entry points and agents.

Kept deliberately small and provider-neutral: `configure_tracing` sets up a
local-only OpenTelemetry pipeline (console exporter + a durable JSONL
exporter, no collector/service required) so `ExplanationAgent` gets real
latency/token/trace-ID instrumentation without adding a new running service
to the stack. Spans were previously console-only and lost once the process
exited (see docs/ai-enhancement-research.md Section 4.3); `JsonlSpanExporter`
persists every span (`aura.llm.*.latency_ms`, prompt/completion token counts,
`aura.guardrail.passed`, `aura.explanation.fallback_triggered`) to
`data/otel_spans.jsonl` by default. Both `configure_*` functions are
idempotent -- safe to call more than once (e.g. once from `replay.py:main()`
and once from a test) without double-registering handlers/providers.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from typing import Optional, Sequence

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (ConsoleSpanExporter, SimpleSpanProcessor,
                                            SpanExporter, SpanExportResult)

LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"
DEFAULT_SPANS_PATH = "data/otel_spans.jsonl"


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format=LOG_FORMAT)


class JsonlSpanExporter(SpanExporter):
    """Appends one JSON object per finished span to a JSONL file.

    A minimal hand-rolled exporter rather than an OTLP/file-exporter package
    dependency: this project has no collector service, and the only consumer
    is future offline analysis of this project's own runs, so a plain JSONL
    file (readable the same way as `data/alerts_*.jsonl`) is the right level
    of infrastructure.
    """

    def __init__(self, path: str = DEFAULT_SPANS_PATH) -> None:
        self._path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        try:
            with self._lock, open(self._path, "a", encoding="utf-8") as f:
                for span in spans:
                    f.write(json.dumps(self._span_to_dict(span)) + "\n")
            return SpanExportResult.SUCCESS
        except Exception:  # noqa: BLE001
            logging.getLogger("aura.telemetry").exception("failed to persist span")
            return SpanExportResult.FAILURE

    def shutdown(self) -> None:  # pragma: no cover
        pass

    @staticmethod
    def _span_to_dict(span: ReadableSpan) -> dict:
        ctx = span.get_span_context()
        start_ns, end_ns = span.start_time, span.end_time
        return {
            "trace_id": format(ctx.trace_id, "032x"),
            "span_id": format(ctx.span_id, "016x"),
            "name": span.name,
            "start_time_ns": start_ns,
            "end_time_ns": end_ns,
            "duration_ms": round((end_ns - start_ns) / 1e6, 3) if start_ns and end_ns else None,
            "attributes": dict(span.attributes or {}),
            "status": span.status.status_code.name,
        }


def configure_tracing(service_name: str = "aura-mas-explanation",
                      spans_path: Optional[str] = DEFAULT_SPANS_PATH) -> trace.Tracer:
    """`spans_path=None` disables durable persistence and keeps the original
    console-only behavior; the default additionally persists every span to a
    JSONL file so `--llm` runs are no longer unrecoverable after the process
    exits."""
    if not isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider):
        return trace.get_tracer(__name__)
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    if spans_path:
        provider.add_span_processor(SimpleSpanProcessor(JsonlSpanExporter(spans_path)))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(__name__)


def get_explanation_tracer() -> trace.Tracer:
    """Lazy accessor: returns a no-op tracer if `configure_tracing` was never
    called, so `ExplanationAgent` stays constructible in tests with zero OTel
    setup."""
    return trace.get_tracer("aura_mas.explanation")
