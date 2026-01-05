# telemetry.py
from __future__ import annotations

import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)


def init_otel(service_name: str = "idle_chapters") -> None:
    """
    Initializes OpenTelemetry tracing.
    Uses OTLP exporter by default (good for local collector, Honeycomb, Datadog, etc.).
    """
    if os.getenv("OTEL_DISABLED", "").lower() in {"1", "true", "yes"}:
        return

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": os.getenv("APP_VERSION", "dev"),
            "deployment.environment": os.getenv("APP_ENV", "local"),
        }
    )

    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    # Export endpoint is controlled by OTEL_EXPORTER_OTLP_ENDPOINT env var.
    # Example: http://localhost:4317
    exporter = OTLPSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))
