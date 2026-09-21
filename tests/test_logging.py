import unittest

from langchain_core.messages import AIMessage

from app.logging_config import get_logger, log_model_response


class LoggingTests(unittest.TestCase):
    def test_model_log_contains_request_and_usage_metadata(self):
        response = AIMessage(
            content="done",
            id="chatcmpl-test",
            response_metadata={"model_name": "test-model"},
            usage_metadata={
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
            },
        )
        logger = get_logger("tests")

        with self.assertLogs(logger, level="INFO") as captured:
            log_model_response(
                logger,
                operation="test",
                response=response,
                duration_ms=12.5,
                run_id="run-test",
            )

        entry = captured.output[0]
        self.assertIn("request_id=chatcmpl-test", entry)
        self.assertIn("model=test-model", entry)
        self.assertIn("total_tokens=15", entry)


if __name__ == "__main__":
    unittest.main()
