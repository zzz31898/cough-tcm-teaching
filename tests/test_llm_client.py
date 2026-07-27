from app.config import Settings
from app.services.llm_client import LLMClient


def test_responses_api_uses_standard_endpoint_and_payload():
    client = LLMClient(
        Settings(
            api_base_url="https://aiport.systems",
            api_key="test-key",
            model_name="gpt-5.6-sol",
            api_mode="responses",
            mock_mode=False,
        )
    )
    assert client._endpoint() == "https://aiport.systems/v1/responses"
    assert client._payload("system instructions", "case input") == {
        "model": "gpt-5.6-sol",
        "instructions": "system instructions",
        "input": "case input",
        "text": {"format": {"type": "json_object"}},
    }


def test_responses_api_extracts_http_response_output_text():
    payload = {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": '{"analysis_status":"differential"}'}],
            }
        ]
    }
    assert LLMClient._responses_output_text(payload) == '{"analysis_status":"differential"}'
