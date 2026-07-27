from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CaseInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    symptoms: list[str] = Field(default_factory=list, max_length=30)
    tongue: str = Field(default="", max_length=200)
    pulse: str = Field(default="", max_length=200)
    other_information: str = Field(default="", max_length=1000)


class NamedEvidence(BaseModel):
    name: str
    evidence: list[str]


class DifferentialReason(BaseModel):
    syndrome: str
    reason: str


class CandidateSyndrome(BaseModel):
    syndrome: str
    rule_match_score: int
    supporting_evidence: list[str]
    contradictory_evidence: list[str]
    missing_key_evidence: list[str]
    why_not_other_syndromes: list[DifferentialReason]


class Node1Symptoms(BaseModel):
    chief_complaint: str
    normalized_symptoms: list[str]
    tongue: list[str]
    pulse: list[str]
    missing_information: list[str]
    red_flags: list[str]
    information_sufficient: bool


class Node2LocationNature(BaseModel):
    locations: list[NamedEvidence]
    natures: list[NamedEvidence]
    summary: str


class Node3Differential(BaseModel):
    candidates: list[CandidateSyndrome]
    recommended_next_questions: list[str]


class Node4Conclusion(BaseModel):
    final_syndrome: str | None
    confidence_level: Literal["low", "medium", "high"]
    pathogenesis: str
    treatment_principle: str
    uncertainty_note: str


class FormulaLogic(BaseModel):
    herb_or_group: str
    role: str
    reason: str


class FormulaModification(BaseModel):
    trigger_symptom: str
    adjustment: str
    reason: str
    source: Literal["hard_rule"] = "hard_rule"


class Node5Formula(BaseModel):
    base_formula: str | None
    formula_target: str
    formula_logic: list[FormulaLogic]
    modifications: list[FormulaModification]
    safety_note: str


class AnalysisResponse(BaseModel):
    case_scope: Literal["cough"] = "cough"
    analysis_status: Literal["insufficient", "differential", "concluded"]
    node1_symptoms: Node1Symptoms
    node2_location_nature: Node2LocationNature
    node3_differential: Node3Differential
    node4_conclusion: Node4Conclusion
    node5_formula: Node5Formula


class RuleAnalysisEnvelope(BaseModel):
    """规则接口返回与完整分析一致，另附运行模式。"""

    mode: Literal["rule"]
    result: AnalysisResponse


class AnalyzeEnvelope(BaseModel):
    mode: Literal["mock", "llm", "fallback"]
    result: AnalysisResponse
    note: str
