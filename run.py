from app.graph.workflow import graph
from app.graph.state import create_initial_state


def main() -> None:
    initial_state = create_initial_state(
        "What are the major research directions "
        "in AI agents today?"
    )
    result = graph.invoke(initial_state)

    print("\n\n========== FINAL REPORT ==========\n")
    print(result["final_report"])


if __name__ == "__main__":
    main()
