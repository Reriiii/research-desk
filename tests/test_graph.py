import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage
from langgraph.graph.message import add_messages
from pydantic import ValidationError

from app.agents.evaluator import Evaluation, evaluation_router
from app.agents.planner import ResearchPlan
from app.agents.researcher import MAX_TOOL_ROUNDS, researcher_node
from app.agents.save_research import save_research_node
from app.agents.tool_executor import tool_node
from app.graph.state import create_initial_state
from app.graph.workflow import graph
from app.main import app


class GraphTests(unittest.TestCase):
    def test_graph_compiles(self):
        self.assertIsNotNone(graph)

    @patch("app.agents.writer._get_writer_model")
    @patch("app.agents.evaluator._get_evaluation_model")
    @patch("app.agents.researcher._get_research_model")
    @patch("app.agents.planner._get_planner_model")
    def test_graph_runs_end_to_end_without_external_calls(
        self,
        get_planner_model,
        get_research_model,
        get_evaluation_model,
        get_writer_model,
    ):
        get_planner_model.return_value.invoke.return_value = ResearchPlan(
            steps=["step one", "step two", "step three"]
        )
        get_research_model.return_value.invoke.side_effect = [
            AIMessage(content="note one"),
            AIMessage(content="note two"),
            AIMessage(content="note three"),
        ]
        get_evaluation_model.return_value.invoke.return_value = Evaluation(
            sufficient=True,
            reason="enough evidence",
        )
        get_writer_model.return_value.invoke.return_value = AIMessage(
            content="final report"
        )

        result = graph.invoke(create_initial_state("query"))

        self.assertEqual(
            result["research_notes"],
            ["note one", "note two", "note three"],
        )
        self.assertEqual(result["final_report"], "final report")
        self.assertTrue(result["research_complete"])

    def test_initial_state_contains_all_control_fields(self):
        state = create_initial_state("query")

        self.assertEqual(state["query"], "query")
        self.assertEqual(state["tool_call_count"], 0)
        self.assertEqual(state["retry_count"], 0)

    def test_plan_requires_three_to_six_steps(self):
        with self.assertRaises(ValidationError):
            ResearchPlan(steps=[])
        with self.assertRaises(ValidationError):
            ResearchPlan(steps=[str(index) for index in range(7)])

    @patch("app.agents.researcher._get_research_model")
    def test_researcher_persists_request_for_tool_followup(self, get_model):
        response = AIMessage(
            content="",
            tool_calls=[{"name": "web_search", "args": {"query": "q"}, "id": "1"}],
        )
        get_model.return_value.invoke.return_value = response
        state = create_initial_state("overall question")
        state["plan"] = ["first step"]

        update = researcher_node(state)

        self.assertIsInstance(update["messages"][0], HumanMessage)
        self.assertIn("overall question", update["messages"][0].text)
        self.assertIn("first step", update["messages"][0].text)
        self.assertIs(update["messages"][1], response)

    def test_save_research_clears_messages(self):
        state = create_initial_state("query")
        state["plan"] = ["step"]
        state["messages"] = [HumanMessage(content="request", id="request")]

        update = save_research_node(state)
        merged = add_messages(state["messages"], update["messages"])

        self.assertEqual(merged, [])
        self.assertIsInstance(update["messages"][0], RemoveMessage)
        self.assertEqual(update["research_notes"], ["request"])

    def test_unknown_tool_returns_error_message(self):
        state = create_initial_state("query")
        state["messages"] = [
            AIMessage(
                content="",
                tool_calls=[{"name": "missing", "args": {}, "id": "call-1"}],
            )
        ]

        update = tool_node(state)

        self.assertEqual(update["messages"][0].status, "error")
        self.assertIn("missing", update["messages"][0].text)
        self.assertEqual(update["tool_call_count"], 1)

    @patch("app.agents.researcher._get_research_model")
    @patch("app.agents.researcher._get_model")
    def test_tool_limit_forces_a_final_answer(self, get_model, get_research_model):
        get_model.return_value.invoke.return_value = AIMessage(content="final note")
        state = create_initial_state("query")
        state["plan"] = ["step"]
        state["messages"] = [HumanMessage(content="request")]
        state["tool_call_count"] = MAX_TOOL_ROUNDS

        update = researcher_node(state)

        self.assertEqual(update["messages"][-1].text, "final note")
        get_model.return_value.invoke.assert_called_once()
        get_research_model.assert_not_called()

    def test_evaluation_stops_after_retry_limit(self):
        state = create_initial_state("query")
        state["retry_count"] = 2

        self.assertEqual(evaluation_router(state), "writer")


class ApiTests(unittest.TestCase):
    def test_root_redirects_to_docs(self):
        response = TestClient(app).get("/", follow_redirects=False)

        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "/docs")

    @patch("app.api.routes.graph.invoke")
    def test_research_endpoint(self, invoke):
        invoke.return_value = {
            "final_report": "report",
            "research_complete": True,
            "evaluation": "sufficient",
        }
        client = TestClient(app)

        response = client.post("/research", json={"query": "test query"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["final_report"], "report")

    def test_health_endpoint(self):
        response = TestClient(app).get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
