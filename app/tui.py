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
from app.observability import agentops_trace


logger = get_logger("tui")


NODE_STATUS = {
    "planner": "Research plan ready",
    "react_agent": "ReAct: reasoning about the next action",
    "act": "ReAct: acting and observing tool evidence",
    "save_research": "Evidence saved",
    "evaluator": "Evaluating research coverage",
    "retry_planner": "Planning follow-up research",
    "writer": "Final report ready",
}


class ResearchTUI(App[None]):
    TITLE = "Research Desk"
    SUB_TITLE = "Evidence-led research agent"
    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+k", "clear", "Clear"),
        ("ctrl+f", "focus_query", "Focus query"),
    ]

    CSS = """
    $archive_ink: #0b1220;
    $deep_ink: #101b2d;
    $signal_cyan: #45c7e8;
    $evidence_mint: #72e0b8;
    $paper: #f4f1e8;
    $slate: #8ea0b8;
    $quiet_slate: #60738d;

    Screen {
        background: $archive_ink;
        color: $paper;
    }

    Header {
        background: $archive_ink;
        color: $slate;
    }

    #shell {
        padding: 1 3;
    }

    #hero {
        height: 4;
        margin-bottom: 1;
        padding-left: 1;
        border-left: thick $signal_cyan;
        color: $paper;
        text-style: bold;
    }

    #query-label {
        height: 1;
        color: $slate;
        text-style: bold;
    }

    #query-row {
        height: 3;
        margin-bottom: 1;
    }

    #query {
        width: 1fr;
        border: tall $quiet_slate;
        background: $deep_ink;
        color: $paper;
    }

    #query:focus {
        border: tall $signal_cyan;
    }

    #run {
        width: 16;
        margin-left: 1;
        background: $signal_cyan;
        color: $archive_ink;
        text-style: bold;
    }

    #run:hover {
        background: $evidence_mint;
    }

    #workspace {
        height: 1fr;
    }

    .panel {
        border: round $quiet_slate;
        background: $deep_ink;
        padding: 1 2;
    }

    #progress-panel {
        width: 40;
        margin-right: 1;
    }

    #report-panel {
        width: 1fr;
        border: round $signal_cyan;
    }

    .panel-title {
        height: 2;
        color: $evidence_mint;
        text-style: bold;
    }

    #status {
        min-height: 2;
        margin-bottom: 1;
        color: $slate;
    }

    #spinner {
        height: 1;
        margin-bottom: 1;
        color: $signal_cyan;
        display: none;
    }

    #plan, #report {
        height: 1fr;
        overflow-y: auto;
    }

    #hint {
        height: 2;
        padding-top: 1;
        color: $quiet_slate;
    }

    Footer {
        background: $archive_ink;
        color: $slate;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="shell"):
            yield Static(
                "RESEARCH DESK  /  EVIDENCE-LED AGENT\n"
                "Research with a visible method: plan, act, observe, evaluate, report.",
                id="hero",
            )
            yield Static("QUESTION / RESEARCH BRIEF", id="query-label")
            with Horizontal(id="query-row"):
                yield Input(
                    placeholder="State the question, scope, and evidence standard...",
                    id="query",
                )
                yield Button("Start run", id="run", variant="primary")
            with Horizontal(id="workspace"):
                with Vertical(id="progress-panel", classes="panel"):
                    yield Static("01 / RUN LEDGER", classes="panel-title")
                    yield Static("Desk ready. No active run.", id="status")
                    yield LoadingIndicator(id="spinner")
                    yield Markdown("_The research plan will be logged here._", id="plan")
                with Vertical(id="report-panel", classes="panel"):
                    yield Static("02 / RESEARCH REPORT", classes="panel-title")
                    yield Markdown(
                        "# Desk ready\n\nEnter a research brief to begin an evidence-led run.",
                        id="report",
                    )
            yield Static(
                f"TRACE / {LOG_FILE}",
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
        button.label = "Researching..." if busy else "Start run"
        self.query_one("#spinner", LoadingIndicator).display = busy

    @work(thread=True, exclusive=True, group="research", exit_on_error=False)
    def run_research(self, state: AgentState) -> None:
        run_id = state["run_id"]
        try:
            with agentops_trace(run_id, "tui"):
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
        self.query_one("#status", Static).update("Desk ready. No active run.")
        self.query_one("#plan", Markdown).update(
            "_The research plan will be logged here._"
        )
        self.query_one("#report", Markdown).update(
            "# Desk ready\n\nEnter a research brief to begin an evidence-led run."
        )
        self.query_one("#query", Input).focus()

    def action_focus_query(self) -> None:
        self.query_one("#query", Input).focus()


def main() -> None:
    ResearchTUI().run()


if __name__ == "__main__":
    main()
