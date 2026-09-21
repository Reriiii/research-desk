import unittest
from unittest.mock import Mock, patch

from agentops.enums import TraceState

from app.observability import agentops_trace


class ObservabilityTests(unittest.TestCase):
    @patch("app.observability.agentops.end_trace")
    @patch("app.observability.agentops.start_trace")
    def test_successful_run_closes_agentops_trace(self, start_trace, end_trace):
        trace = Mock()
        trace.span.get_span_context.return_value.trace_id = 1
        start_trace.return_value = trace

        with patch("app.observability._initialized", True):
            with agentops_trace("run-id", "test"):
                pass

        start_trace.assert_called_once_with(
            "research-agent",
            tags={"run_id": "run-id", "source": "test"},
        )
        end_trace.assert_called_once_with(trace, end_state=TraceState.SUCCESS)


if __name__ == "__main__":
    unittest.main()
