from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_home_page_loads():
    response = client.get("/")
    assert response.status_code == 200
    assert "咳辨" in response.text
    assert "五节点辨证路径" in response.text


def test_knowledge_tree_has_eight_syndromes():
    response = client.get("/api/knowledge-tree")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 8
    assert "痰热郁肺" in [item["syndrome"] for item in payload["syndromes"]]


def test_rule_api_returns_same_schema():
    response = client.post(
        "/api/rule-analyze",
        json={"symptoms": ["咳嗽", "痰黄黏稠", "口渴"], "tongue": "舌红苔黄腻", "pulse": "脉滑数"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "rule"
    assert payload["result"]["case_scope"] == "cough"
    assert len(payload["result"]["node3_differential"]["candidates"]) <= 3


def test_analyze_defaults_to_mock_mode():
    response = client.post("/api/analyze", json={"symptoms": ["咳嗽", "痰多"]})
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "mock"
    assert payload["result"]["node5_formula"]["base_formula"] is None


def test_example_cases_are_available():
    response = client.get("/api/example-cases")
    assert response.status_code == 200
    assert len(response.json()["cases"]) >= 5
