# Local Development

Run `openframe-core` locally without Modal, without a cloud account, without a real database.

---

## Install in Editable Mode

```bash
git clone https://github.com/Furious-Meteors/openframe-core
cd openframe-core
pip install -e ".[dev]"
```

---

## Run the Test Suite

```bash
pytest tests/ -v
```

284 tests. All pass with no external services. OTel tests use `InMemorySpanExporter` — no network calls.

---

## Run a Local FastAPI App

See [Quick Start](quick-start/index.md) for a full working example with an in-memory repository.

```bash
uvicorn main:app --reload
```

No database, no Redis, no Modal. The in-memory repository satisfies `BaseRepository` structurally.

---

## Build and Serve the Docs

```bash
pip install mkdocs mkdocs-material pymdown-extensions
mkdocs serve
# → http://localhost:8000
```

---

## What Doesn't Work Locally

| Feature | Why | Workaround |
|---|---|---|
| OTLP export | Needs real endpoint | Set `OTEL_EXPORTER_OTLP_ENDPOINT` to a local Jaeger or skip it — no-op mode works fine |
| Real database adapters | Needs running Postgres / Redis / etc. | Use in-memory fakes that satisfy the port Protocol |
| Modal-specific config (`MODAL_ENV`) | Modal injects this automatically | Set `OPENFRAME_ENV=dev` manually |
