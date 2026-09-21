from app.graph.workflow import graph
from app.graph.state import create_initial_state
from app.logging_config import LOG_FILE, configure_logging, get_logger


configure_logging(console=True)
logger = get_logger("cli")


def main() -> None:
    initial_state = create_initial_state(
        "What are the major research directions "
        "in AI agents today?"
    )
    logger.info(
        "run_id=%s event=cli_started log_file=%s",
        initial_state["run_id"],
        LOG_FILE,
    )
    result = graph.invoke(initial_state)

    print(f"Run ID: {initial_state['run_id']}")
    print(f"Log file: {LOG_FILE}")
    print("\n\n========== FINAL REPORT ==========\n")
    print(result["final_report"])


if __name__ == "__main__":
    main()
