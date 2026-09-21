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

Configure `MODEL`, `OPENAI_API_KEY`, `TAVILY_API_KEY`, and
`AGENTOPS_API_KEY` in `.env`.

## Run

Start the interactive terminal UI:

```powershell
uv run python tui.py
```

Enter a research question and press `Enter` or select **Research**. Use
`Ctrl+F` to focus the query, `Ctrl+K` to clear the current result, and `Ctrl+Q`
to quit.

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

## Diagnostics

Detailed progress is written to `logs/research-agent.log`. Every research run
has a `run_id`; use it to filter planner, researcher, Tavily, evaluator, and
writer events belonging to one request. Model response entries include latency,
OpenAI request ID, resolved model name, and token usage. Set `LOG_LEVEL=DEBUG`
in `.env` for additional diagnostics.

If OpenAI usage is not visible in the dashboard, match the dashboard project to
the project owning the API key or set `OPENAI_PROJECT=proj_...` explicitly.

AgentOps is initialized by `main.py`, `tui.py`, and `run.py`. Each research run
is sent as a separate `research-agent` trace tagged with the local `run_id` and
its source (`api`, `tui`, or `cli`).

Live PowerShell view:

```powershell
Get-Content .\logs\research-agent.log -Wait
```

## Test

Tests use only the standard library and mock all external services:

```powershell
uv run python -m unittest discover -v
```
