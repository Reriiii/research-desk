from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import get_model_name
from app.graph.state import AgentState


@lru_cache(maxsize=1)
def _get_writer_model():
    return ChatOpenAI(
        model=get_model_name(),
        temperature=0.2,
    )


def writer_node(state: AgentState):
    notes = "\n\n".join(state["research_notes"])
    evaluation = state["evaluation"] or "No quality concerns were reported."

    response = _get_writer_model().invoke(
        f"""
You are a professional research writer.

Answer the user's question using ONLY the evidence collected below.

Original question:

{state["query"]}

Research evidence:

{notes}

Research quality evaluation:

{evaluation}

Requirements:

- Provide a clear direct answer.
- Organize the answer into meaningful sections.
- Distinguish factual evidence from interpretation.
- Include relevant source URLs when available.
- Mention uncertainty when evidence is incomplete.
- Do not invent missing information.
"""
    )

    return {"final_report": response.text}
