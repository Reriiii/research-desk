from typing import Any

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    LoadingIndicator,
    Markdown,
    Static,
)

from app.graph.state import AgentState, create_initial_state
from app.graph.workflow import graph
from app.logging_config import LOG_FILE, get_logger, preview


logger = get_logger("tui")


NODE_STATUS = {
    "planner": "Research plan ready",
    "researcher": "Analyzing the current research step",
    "tools": "Searching for evidence",
    "save_research": "Evidence saved",
    "evaluator": "Evaluating research coverage",
    "retry_planner": "Planning follow-up research",
    "writer": "Final report ready",
}


class ResearchTUI(App[None]):
    TITLE = "Research Desk"
    SUB_TITLE = "LangGraph research agent"
    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+k", "clear", "Clear"),
        ("ctrl+f", "focus_query", "Focus query"),
    ]

    CSS = """
    Screen {
        background: #07111f;
        color: #d9e7f5;
    }

    Header {
        background: #0d2138;
        color: #eff8ff;
    }

    #shell {
        padding: 1 2;
    }

    #hero {
        height: 3;
        margin-bottom: 1;
        color: #86d9ff;
        text-style: bold;
    }

    #query-row {
        height: 3;
        margin-bottom: 1;
    }

    #query {
        width: 1fr;
        border: tall #24577a;
        background: #0a192a;
    }

    #query:focus {
        border: tall #45c4ed;
    }

    #run {
        width: 16;
        margin-left: 1;
        background: #0e7490;
        color: white;
        text-style: bold;
    }

    #workspace {
        height: 1fr;
    }

    .panel {
        border: round #24577a;
        background: #0a192a;
        padding: 1 2;
    }

    #progress-panel {
        width: 38;
        margin-right: 1;
    }

    #report-panel {
        width: 1fr;
    }

    .panel-title {
        height: 2;
        color: #67e8c8;
        text-style: bold;
    }

    #status {
        min-height: 2;
        margin-bottom: 1;
        color: #b8cbe0;
    }

    #spinner {
        height: 1;
        margin-bottom: 1;
        color: #45c4ed;
        display: none;
    }

    #plan, #report {
        height: 1fr;
        overflow-y: auto;
    }

    #hint {
        height: 2;
        padding-top: 1;
        color: #718ba5;
    }

    Footer {
        background: #0d2138;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="shell"):
            yield Static(
                "RESEARCH DESK\nAsk a question, then follow each stage of the agent.",
                id="hero",
            )
            with Horizontal(id="query-row"):
                yield Input(
                    placeholder="What do you want to research?",
                    id="query",
                )
                yield Button("Research", id="run", variant="primary")
            with Horizontal(id="workspace"):
                with Vertical(id="progress-panel", classes="panel"):
                    yield Static("PROGRESS", classes="panel-title")
                    yield Static("Ready for a research question.", id="status")
                    yield LoadingIndicator(id="spinner")
                    yield Markdown("_The research plan will appear here._", id="plan")
                with Vertical(id="report-panel", classes="panel"):
                    yield Static("REPORT", classes="panel-title")
                    yield Markdown(
                        "# Ready\n\nEnter a question above to start a research run.",
                        id="report",
                    )
            yield Static(
                f"Detailed diagnostics: {LOG_FILE}",
                id="hint",
            )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#query", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._start_research(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run":
            self._start_research(self.query_one("#query", Input).value)

    def _start_research(self, query: str) -> None:
        query = query.strip()
        if not query:
            self.notify("Enter a research question first.", severity="warning")
            self.query_one("#query", Input).focus()
            return

        if self.query_one("#run", Button).disabled:
            return

        state = create_initial_state(query)
        run_id = state["run_id"]
        logger.info(
            "run_id=%s event=tui_run_started query=%s log_file=%s",
            run_id,
            preview(query),
            LOG_FILE,
        )
        self._set_busy(True)
        self.query_one("#status", Static).update(
            f"Run {run_id}: creating a research plan..."
        )
        self.query_one("#plan", Markdown).update("_Planning..._")
        self.query_one("#report", Markdown).update(
            "# Research in progress\n\nEvidence and the final report will appear here."
        )
        self.run_research(state)

    def _set_busy(self, busy: bool) -> None:
        self.query_one("#query", Input).disabled = busy
        button = self.query_one("#run", Button)
        button.disabled = busy
        button.label = "Running..." if busy else "Research"
        self.query_one("#spinner", LoadingIndicator).display = busy

    @work(thread=True, exclusive=True, group="research", exit_on_error=False)
    def run_research(self, state: AgentState) -> None:
        run_id = state["run_id"]
        try:
            for chunk in graph.stream(
                state,
                stream_mode="updates",
            ):
                for node_name, update in chunk.items():
                    self.call_from_thread(
                        self._apply_graph_update,
                        node_name,
                        update,
                        run_id,
                    )
        except Exception as exc:
            logger.exception("run_id=%s event=tui_run_failed", run_id)
            self.call_from_thread(self._show_error, str(exc), run_id)
        else:
            logger.info("run_id=%s event=tui_run_complete", run_id)
            self.call_from_thread(self._finish_research, run_id)

    def _apply_graph_update(
        self,
        node_name: str,
        update: dict[str, Any],
        run_id: str,
    ) -> None:
        status = NODE_STATUS.get(node_name, f"Completed: {node_name}")
        self.query_one("#status", Static).update(f"Run {run_id}: {status}")

        if node_name == "planner":
            plan = update.get("plan", [])
            plan_text = "\n".join(
                f"{index}. {step}" for index, step in enumerate(plan, start=1)
            )
            self.query_one("#plan", Markdown).update(f"## Research plan\n\n{plan_text}")
        elif node_name == "save_research":
            current_step = update.get("current_step", 0)
            self.query_one("#status", Static).update(
                f"Run {run_id}: completed research step {current_step}"
            )
        elif node_name == "retry_planner":
            self.query_one("#status", Static).update(
                f"Run {run_id}: coverage incomplete; running follow-up research"
            )
        elif node_name == "writer":
            report = update.get("final_report")
            if report:
                self.query_one("#report", Markdown).update(str(report))

    def _finish_research(self, run_id: str) -> None:
        self._set_busy(False)
        self.query_one("#status", Static).update(f"Run {run_id}: research complete")
        self.query_one("#query", Input).focus()
        self.notify("Research report completed.", title="Research Desk")

    def _show_error(self, error: str, run_id: str) -> None:
        self._set_busy(False)
        self.query_one("#status", Static).update(f"Run {run_id}: research failed")
        self.query_one("#report", Markdown).update(
            f"# Research failed\n\n```text\n{error}\n```"
        )
        self.query_one("#query", Input).focus()
        self.notify(error, title="Research failed", severity="error")

    def action_clear(self) -> None:
        if self.query_one("#run", Button).disabled:
            self.notify("Wait for the current research run to finish.")
            return

        self.query_one("#query", Input).value = ""
        self.query_one("#status", Static).update("Ready for a research question.")
        self.query_one("#plan", Markdown).update(
            "_The research plan will appear here._"
        )
        self.query_one("#report", Markdown).update(
            "# Ready\n\nEnter a question above to start a research run."
        )
        self.query_one("#query", Input).focus()

    def action_focus_query(self) -> None:
        self.query_one("#query", Input).focus()


def main() -> None:
    ResearchTUI().run()


if __name__ == "__main__":
    main()
