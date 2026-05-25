# Observability Module

`phoenix.py` provides optional OpenTelemetry-compatible tracing for agent
execution. Tracing is disabled by default and uses a no-op tracer unless
`ENABLE_TRACING=true`.

When enabled, spans are exported over OTLP/HTTP to
`PHOENIX_COLLECTOR_ENDPOINT`, which defaults to a locally running Phoenix
collector. Instrumentation records route names, result counts, tool names,
and approval status; it does not attach user messages, retrieved text, or
tool argument payloads to spans.

If tracing configuration cannot be initialized, the module logs a warning and
continues with no-op tracing so agent requests remain functional.
