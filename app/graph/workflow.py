from langgraph.graph import END, START, StateGraph

from app.agents.planner import planner_node
from app.agents.researcher import (
    researcher_node,
    researcher_router,
)
from app.agents.tool_executor import tool_node
from app.agents.save_research import (
    save_research_node,
    step_router,
)
from app.agents.evaluator import (
    evaluator_node,
    evaluation_router,
)
from app.agents.retry import retry_planner_node
from app.agents.writer import writer_node

from app.graph.state import AgentState


builder = StateGraph(AgentState)


# -------------------------
# Nodes
# -------------------------

builder.add_node(
    "planner",
    planner_node,
)

builder.add_node(
    "researcher",
    researcher_node,
)

builder.add_node(
    "tools",
    tool_node,
)

builder.add_node(
    "save_research",
    save_research_node,
)

builder.add_node(
    "evaluator",
    evaluator_node,
)

builder.add_node(
    "retry_planner",
    retry_planner_node,
)

builder.add_node(
    "writer",
    writer_node,
)


# -------------------------
# Edges
# -------------------------

builder.add_edge(
    START,
    "planner",
)

builder.add_edge(
    "planner",
    "researcher",
)


# researcher:
#
# tool call -> tools
# finished  -> save
#
builder.add_conditional_edges(
    "researcher",
    researcher_router,
    {
        "tools": "tools",
        "save_research": "save_research",
    },
)


# tool observation returns to agent
builder.add_edge(
    "tools",
    "researcher",
)


# next research step OR evaluator
builder.add_conditional_edges(
    "save_research",
    step_router,
    {
        "researcher": "researcher",
        "evaluator": "evaluator",
    },
)


# evaluator chooses retry or writer
builder.add_conditional_edges(
    "evaluator",
    evaluation_router,
    {
        "retry_planner": "retry_planner",
        "writer": "writer",
    },
)


builder.add_edge(
    "retry_planner",
    "researcher",
)


builder.add_edge(
    "writer",
    END,
)


graph = builder.compile()