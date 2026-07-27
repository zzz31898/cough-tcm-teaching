from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from starlette.requests import Request

from app.config import get_settings
from app.knowledge.cough_rules import COUGH_SYNDROMES, EXAMPLE_CASES
from app.models.schemas import AnalyzeEnvelope, CaseInput, RuleAnalysisEnvelope
from app.services.llm_client import LLMClient
from app.services.prompt_builder import REPAIR_PROMPT, SYSTEM_PROMPT, build_user_prompt
from app.services.response_validator import validate_llm_response
from app.services.rule_engine import analyze_case


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="咳辨 · 中医咳嗽辨证逻辑可视化教学系统",
    description="面向中医学习者的五节点辨证思维教学工具。",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/knowledge-tree")
async def knowledge_tree():
    return {
        "scope": "cough",
        "count": len(COUGH_SYNDROMES),
        "syndromes": [
            {
                "syndrome": rule["syndrome"],
                "location": rule["location"],
                "nature": rule["nature"],
                "core_symptoms": rule["core_symptoms"],
                "differential_with": rule["differential_with"],
                "treatment_principle": rule["treatment_principle"],
                "base_formula": rule["base_formula"],
            }
            for rule in COUGH_SYNDROMES
        ],
    }


@app.get("/api/example-cases")
async def example_cases():
    return {"cases": EXAMPLE_CASES}


@app.post("/api/rule-analyze", response_model=RuleAnalysisEnvelope)
async def rule_analyze(case: CaseInput):
    return RuleAnalysisEnvelope(mode="rule", result=analyze_case(case))


@app.post("/api/analyze", response_model=AnalyzeEnvelope)
async def analyze(case: CaseInput):
    rule_result = analyze_case(case)
    settings = get_settings()
    if not settings.llm_enabled:
        return AnalyzeEnvelope(
            mode="mock",
            result=rule_result,
            note="当前为教学演示模式：结果由可复核的硬规则生成。",
        )

    client = LLMClient(settings)
    try:
        raw = await client.complete(SYSTEM_PROMPT, build_user_prompt(case, rule_result))
        try:
            result = validate_llm_response(raw)
        except (ValidationError, ValueError) as validation_error:
            repair_prompt = REPAIR_PROMPT.format(
                validation_errors=str(validation_error),
                invalid_output=raw,
            )
            repaired = await client.complete(SYSTEM_PROMPT, repair_prompt)
            result = validate_llm_response(repaired)
        return AnalyzeEnvelope(
            mode="llm",
            result=result,
            note="硬规则初筛后，由结构化模型解释生成；字段已通过校验。",
        )
    except Exception as e:
        import traceback
        print(f"LLM Error: {e}")
        print(traceback.format_exc())
        return AnalyzeEnvelope(
            mode="fallback",
            result=rule_result,
            note="模型服务暂不可用，已安全回退至硬规则教学结果。",
        )
