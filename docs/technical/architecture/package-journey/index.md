# Package Journey — Overview

A developer installs `openframe-core`, wires it into a template, and serves a request. This section traces that journey end-to-end across four stages.

---

## The Four Stages

```mermaid
flowchart LR
    TW["1. Template Wiring\nPluginRegistry assembles ports"]
    AL["2. Adapter Lifecycle\ninitialize → health() → execute → shutdown"]
    TF["3. Tracing Flow\nTracingProxy + TelemetryMiddleware produce spans"]
    EP["4. Error Propagation\nOpenFrameError → record_error → HTTP response"]

    TW --> AL --> TF --> EP

    style TW fill:#1a1a1a,color:#F0F0F0,stroke:#6DB33F
    style AL fill:#141414,color:#F0F0F0,stroke:#4E8A2A
    style TF fill:#141414,color:#F0F0F0,stroke:#4E8A2A
    style EP fill:#141414,color:#F0F0F0,stroke:#4E8A2A
```

| Stage | Page | What it covers |
|---|---|---|
| Template Wiring | [Template Wiring](template-wiring.md) | How `PluginRegistry` and `deps.py` assemble ports with `TracingProxy` |
| Adapter Lifecycle | [Adapter Lifecycle](adapter-lifecycle.md) | `initialize`, `health()`, execute, reconnect, `shutdown` |
| Tracing Flow | [Tracing Flow](tracing-flow.md) | How spans flow from middleware through proxy to adapter |
| Error Propagation | [Error Propagation](error-propagation.md) | How `OpenFrameError` flows through `record_error` to an HTTP response |
