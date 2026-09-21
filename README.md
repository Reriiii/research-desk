# LangGraph Research Agent

A multi-step research agent built with LangGraph, OpenAI, and Tavily. It plans a
research task, gathers web evidence, evaluates coverage, retries missing areas,
and writes a final report.

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```powershell
uv sync --frozen
Copy-Item .env.example .env
```

Configure `MODEL`, `OPENAI_API_KEY`, and `TAVILY_API_KEY` in `.env`.

## Run

Run the example query:

```powershell
uv run python run.py
```

Start the HTTP API:

```powershell
uv run python main.py
```

Then send `POST /research` with a JSON body such as:

```json
{"query": "What are the major research directions in AI agents today?"}
```

Check service availability with `GET /health`.

## Test

Tests use only the standard library and mock all external services:

```powershell
uv run python -m unittest discover -v
```
