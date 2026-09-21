from langchain_core.messages import ToolMessage

from app.graph.state import AgentState
from app.tools.search import web_search


TOOLS = {
    web_search.name: web_search,
}


def tool_node(state: AgentState):
    last_message = state["messages"][-1]

    results = []

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        try:
            tool = TOOLS[tool_name]
            result = tool.invoke(tool_args)
            content = str(result)
            status = "success"
        except Exception as exc:
            content = f"Tool '{tool_name}' failed: {exc}"
            status = "error"

        results.append(
            ToolMessage(
                content=content,
                tool_call_id=tool_call["id"],
                status=status,
            )
        )

    return {
        "messages": results,
        "tool_call_count": state.get("tool_call_count", 0) + 1,
    }
