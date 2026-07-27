from __future__ import annotations

import json
import re

from app.models.schemas import AnalysisResponse


def extract_json(raw_output: str) -> dict:
    cleaned = raw_output.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def validate_llm_response(raw_output: str) -> AnalysisResponse:
    return AnalysisResponse.model_validate(extract_json(raw_output))
