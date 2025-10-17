"""OpenTelemetry helpers (optional)."""

from __future__ import annotations

import os
from typing import Dict, Optional

try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    _OTEL_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    trace = None
    _OTEL_AVAILABLE = False

_TRACER = None


def _ensure_tracer() -> Optional["trace.Tracer"]:
    global _TRACER
    if not _OTEL_AVAILABLE:
        return None
    exporter_pref = os.environ.get("SKILLCHECK_OTEL_EXPORTER", "").lower()
    if not exporter_pref:
        return None
    if _TRACER is None:
        provider = TracerProvider(resource=Resource.create({"service.name": "skillcheck"}))
        processors = []
        if exporter_pref == "console":
            processors.append(ConsoleSpanExporter())
        elif exporter_pref == "otlp":
            try:  # pragma: no cover - optional dependency
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

                processors.append(OTLPSpanExporter())
            except Exception:
                return None
        else:
            return None
        for exporter in processors:
            provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _TRACER = trace.get_tracer("skillcheck")
    return _TRACER


def emit_run_span(name: str, skill_name: str, attributes: Dict[str, object]) -> bool:
    """Emit a span if OpenTelemetry is available."""
    tracer = _ensure_tracer()
    if tracer is None:
        return False
    with tracer.start_as_current_span(f"skillcheck.{name}") as span:  # pragma: no cover - requires otel
        span.set_attribute("skill.name", skill_name)
        for key, value in attributes.items():
            span.set_attribute(key, value)
    return True
