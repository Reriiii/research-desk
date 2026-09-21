import unittest
from unittest.mock import patch

from textual.widgets import Button, Input, Markdown, Static

from app.tui import ResearchTUI


class TUITests(unittest.IsolatedAsyncioTestCase):
    @patch("app.tui.graph.stream")
    async def test_research_updates_plan_and_report(self, stream):
        stream.return_value = iter(
            [
                {
                    "planner": {
                        "plan": ["Find sources", "Compare evidence", "Summarize"]
                    }
                },
                {"writer": {"final_report": "# Final report\n\nCompleted."}},
            ]
        )
        app = ResearchTUI()

        async with app.run_test(size=(120, 40)) as pilot:
            app.query_one("#query", Input).value = "Research this topic"
            await pilot.click("#run")
            await app.workers.wait_for_complete()
            await pilot.pause()

            self.assertTrue(
                str(app.query_one("#status", Static).render()).endswith(
                    ": research complete"
                )
            )
            self.assertEqual(
                app.query_one("#report", Markdown)._markdown,
                "# Final report\n\nCompleted.",
            )
            self.assertFalse(app.query_one("#run", Button).disabled)
            stream.assert_called_once()


if __name__ == "__main__":
    unittest.main()
