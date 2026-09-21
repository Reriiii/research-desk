from time import perf_counter

from langchain_core.messages import ToolMessage

from app.graph.state import AgentState
from app.logging_config import get_logger, preview
from app.tools.search import web_search


TOOLS = {
    web_search.name: web_search,
}
logger = get_logger("agents.react_action")


def tool_node(state: AgentState):
    last_message = state["messages"][-1]
    run_id = state["run_id"]

    results = []
    logger.info(
        "run_id=%s event=node_start node=react_action calls=%d iteration=%d",
        run_id,
        len(last_message.tool_calls),
        state.get("react_iteration", 0) + 1,
    )

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        started = perf_counter()
        logger.info(
            "run_id=%s event=tool_start tool=%s call_id=%s args=%s",
            run_id,
            tool_name,
            tool_call["id"],
            preview(tool_args),
        )

        try:
            tool = TOOLS[tool_name]
            result = tool.invoke(tool_args)
            content = str(result)
            status = "success"
        except Exception as exc:
            content = f"Tool '{tool_name}' failed: {exc}"
            status = "error"
            logger.exception(
                "run_id=%s event=tool_failed tool=%s call_id=%s duration_ms=%.1f",
                run_id,
                tool_name,
                tool_call["id"],
                (perf_counter() - started) * 1000,
            )
        else:
            logger.info(
                "run_id=%s event=tool_complete tool=%s call_id=%s "
                "duration_ms=%.1f result_chars=%d",
                run_id,
                tool_name,
                tool_call["id"],
                (perf_counter() - started) * 1000,
                len(content),
            )

        results.append(
            ToolMessage(
                content=content,
                tool_call_id=tool_call["id"],
                status=status,
            )
        )

    logger.info(
        "run_id=%s event=node_complete node=react_action observations=%d errors=%d",
        run_id,
        len(results),
        sum(message.status == "error" for message in results),
    )
    return {
        "messages": results,
        "react_iteration": state.get("react_iteration", 0) + 1,
    }
