from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable

from app.knowledge.cough_rules import COUGH_SYNDROMES
from app.knowledge.symptom_aliases import RED_FLAG_ALIASES, SYMPTOM_ALIASES
from app.models.schemas import (
    AnalysisResponse,
    CandidateSyndrome,
    CaseInput,
    DifferentialReason,
    FormulaLogic,
    FormulaModification,
    NamedEvidence,
    Node1Symptoms,
    Node2LocationNature,
    Node3Differential,
    Node4Conclusion,
    Node5Formula,
)


SPLIT_PATTERN = re.compile(r"[，,、；;。.\s]+")


def _clean(value: str) -> str:
    return re.sub(r"\s+", "", value.strip())


def _apply_alias(value: str) -> str:
    cleaned = _clean(value)
    for alias, canonical in sorted(SYMPTOM_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        cleaned = cleaned.replace(alias, canonical)
    return cleaned


def _split_signs(value: str) -> list[str]:
    return [_apply_alias(part) for part in SPLIT_PATTERN.split(value) if _clean(part)]


def normalize_symptoms(symptoms: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for raw in symptoms:
        for item in _split_signs(raw):
            if item and item not in normalized:
                normalized.append(item)
    return normalized


def _matches(term: str, haystack: str) -> bool:
    normalized_term = _apply_alias(term)
    return bool(normalized_term and normalized_term in haystack)


def _matched_terms(terms: list[str], haystack: str) -> list[str]:
    return [term for term in terms if _matches(term, haystack)]


def _detect_red_flags(raw_text: str) -> list[str]:
    return [
        canonical
        for canonical, aliases in RED_FLAG_ALIASES.items()
        if any(alias in raw_text for alias in aliases)
    ]


def _question_for(term: str) -> str:
    if "痰" in term:
        return f"痰的颜色、质地或咯出情况是否符合“{term}”？"
    if term.startswith("脉") or term in {"浮紧", "浮数", "滑数", "弦数", "细数", "濡滑"}:
        return f"脉象是否见{term.removeprefix('脉')}？"
    if "舌" in term or "苔" in term:
        return f"舌象是否见{term}？"
    return f"是否伴有{term}？"


def _score_syndrome(rule: dict, symptom_text: str, tongue_text: str, pulse_text: str) -> dict:
    core_hits = _matched_terms(rule["core_symptoms"], symptom_text)
    support_hits = _matched_terms(rule["supporting_symptoms"], symptom_text)
    tongue_hits = _matched_terms(rule["tongue_signs"], tongue_text)
    pulse_hits = _matched_terms(rule["pulse_signs"], pulse_text)
    all_text = f"{symptom_text}|{tongue_text}|{pulse_text}"
    contradiction_hits = _matched_terms(rule["contradictory_signs"], all_text)

    score = (
        len(core_hits) * 3
        + len(support_hits)
        + len(tongue_hits) * 2
        + len(pulse_hits) * 2
        - len(contradiction_hits) * 3
    )
    if not core_hits:
        score -= 2

    evidence = list(dict.fromkeys(core_hits + support_hits + tongue_hits + pulse_hits))
    missing_core = [item for item in rule["core_symptoms"] if item not in core_hits]
    missing_signs: list[str] = []
    if not tongue_hits and rule["tongue_signs"]:
        missing_signs.append(rule["tongue_signs"][0])
    if not pulse_hits and rule["pulse_signs"]:
        missing_signs.append(rule["pulse_signs"][0])

    return {
        "rule": rule,
        "score": max(score, 0),
        "supporting": evidence,
        "contradictory": contradiction_hits,
        "missing": (missing_core + missing_signs)[:4],
        "core_hits": core_hits,
    }


def _make_differential_reasons(current: dict, ranked: list[dict]) -> list[DifferentialReason]:
    reasons: list[DifferentialReason] = []
    for other in ranked:
        if other["rule"]["syndrome"] == current["rule"]["syndrome"]:
            continue
        if other["score"] < current["score"]:
            reason = (
                f"{other['rule']['syndrome']}当前规则匹配度更低"
                f"（{other['score']} vs {current['score']}），"
                f"且仍缺少{('、'.join(other['missing'][:2]) or '关键特异表现')}。"
            )
        else:
            reason = "两条路径接近，仍需结合舌脉、痰的性质与病程继续鉴别。"
        reasons.append(DifferentialReason(syndrome=other["rule"]["syndrome"], reason=reason))
        if len(reasons) == 2:
            break
    return reasons


def _location_and_nature(ranked: list[dict]) -> tuple[list[NamedEvidence], list[NamedEvidence]]:
    locations: dict[str, list[str]] = defaultdict(list)
    natures: dict[str, list[str]] = defaultdict(list)
    for candidate in ranked:
        evidence = candidate["supporting"][:4] or ["当前直接证据不足"]
        for location in candidate["rule"]["location"]:
            locations[location].extend(evidence)
        for nature in candidate["rule"]["nature"]:
            natures[nature].extend(evidence)

    location_items = [
        NamedEvidence(name=name, evidence=list(dict.fromkeys(evidence))[:4])
        for name, evidence in locations.items()
    ]
    nature_items = [
        NamedEvidence(name=name, evidence=list(dict.fromkeys(evidence))[:4])
        for name, evidence in natures.items()
    ]
    return location_items[:3], nature_items[:5]


def analyze_case(case: CaseInput) -> AnalysisResponse:
    normalized_symptoms = normalize_symptoms(case.symptoms)
    symptom_text = "|".join(normalized_symptoms)
    tongue_signs = _split_signs(case.tongue)
    pulse_signs = _split_signs(case.pulse)
    tongue_text = "|".join(tongue_signs)
    pulse_text = "|".join(pulse_signs)
    other_text = _apply_alias(case.other_information)
    raw_text = "|".join([symptom_text, tongue_text, pulse_text, other_text])

    ranked_all = sorted(
        [_score_syndrome(rule, symptom_text + "|" + other_text, tongue_text, pulse_text) for rule in COUGH_SYNDROMES],
        key=lambda item: item["score"],
        reverse=True,
    )
    ranked = ranked_all[:3]
    top = ranked[0]
    red_flags = _detect_red_flags(raw_text)

    specific_symptoms = [item for item in normalized_symptoms if item != "咳嗽"]
    direct_evidence_count = len(set(top["supporting"]))
    has_observation = bool(tongue_signs or pulse_signs)
    information_sufficient = (
        len(specific_symptoms) >= 3
        and has_observation
        and top["score"] >= 8
        and direct_evidence_count >= 4
    )

    if information_sufficient:
        analysis_status = "concluded"
    elif len(specific_symptoms) >= 2 or has_observation:
        analysis_status = "differential"
    else:
        analysis_status = "insufficient"

    missing_information: list[str] = []
    if not tongue_signs:
        missing_information.append("舌质与舌苔")
    if not pulse_signs:
        missing_information.append("脉象")
    if not any("痰" in item for item in normalized_symptoms):
        missing_information.append("痰的颜色、质地与量")
    if not any(word in raw_text for word in ("恶寒", "发热", "口渴", "潮热", "畏风")):
        missing_information.append("寒热与津液表现")
    if not any(word in other_text for word in ("天", "周", "月", "年", "病程", "反复", "长期")):
        missing_information.append("起病诱因与病程")

    candidates = [
        CandidateSyndrome(
            syndrome=item["rule"]["syndrome"],
            rule_match_score=item["score"],
            supporting_evidence=item["supporting"],
            contradictory_evidence=item["contradictory"],
            missing_key_evidence=item["missing"],
            why_not_other_syndromes=_make_differential_reasons(item, ranked),
        )
        for item in ranked
    ]

    questions: list[str] = []
    for item in ranked:
        for missing in item["missing"]:
            question = _question_for(missing)
            if question not in questions:
                questions.append(question)
            if len(questions) >= 4:
                break
        if len(questions) >= 4:
            break

    locations, natures = _location_and_nature(ranked)
    top_rule = top["rule"]
    score_gap = top["score"] - ranked[1]["score"]

    if information_sufficient and not red_flags:
        confidence = "high" if top["score"] >= 13 and score_gap >= 4 else "medium"
        uncertainty = (
            "当前证据链较完整，仍应结合动态舌脉与病程变化复核。"
            if confidence == "high"
            else "首选路径已形成，但与次位候选仍需结合病程和兼症复核。"
        )
    elif red_flags:
        confidence = "low"
        uncertainty = "存在危险信号；教学辨证不能替代及时、规范的医学评估。"
    else:
        confidence = "low"
        uncertainty = "当前不能唯一辨证，保留候选路径，补充关键问诊后再判断。"

    final_syndrome = top_rule["syndrome"] if information_sufficient else None
    formula_allowed = information_sufficient and not red_flags
    formula_logic = (
        [
            FormulaLogic(
                herb_or_group=item["herb_or_group"],
                role=item["role"],
                reason=item["target_pathogenesis"],
            )
            for item in top_rule["formula_explanation"]
        ]
        if formula_allowed
        else []
    )
    modifications: list[FormulaModification] = []
    if formula_allowed:
        for modification in top_rule["modification_rules"]:
            triggers = [
                condition
                for condition in modification["condition"]
                if _matches(condition, raw_text)
            ]
            if triggers:
                modifications.append(
                    FormulaModification(
                        trigger_symptom="、".join(triggers),
                        adjustment=modification["adjustment"],
                        reason=modification["reason"],
                    )
                )

    if red_flags:
        safety_note = (
            f"已识别危险信号：{'、'.join(red_flags)}。请及时进行正规医学评估；"
            "本页仅保留教学推演，不展示代表方。"
        )
    elif not information_sufficient:
        safety_note = "信息不足，暂不进入代表方展示；请先补充关键问诊信息。"
    else:
        safety_note = "仅展示教材代表方及配伍逻辑，不含剂量，不构成诊疗或处方建议。"

    return AnalysisResponse(
        analysis_status=analysis_status,
        node1_symptoms=Node1Symptoms(
            chief_complaint="咳嗽",
            normalized_symptoms=normalized_symptoms,
            tongue=tongue_signs,
            pulse=pulse_signs,
            missing_information=missing_information,
            red_flags=red_flags,
            information_sufficient=information_sufficient,
        ),
        node2_location_nature=Node2LocationNature(
            locations=locations,
            natures=natures,
            summary=(
                f"规则证据目前主要指向{'、'.join(item.name for item in locations[:2]) or '病位未定'}，"
                f"病性以{'、'.join(item.name for item in natures[:3]) or '尚待补充'}为候选；"
                "以上为多项表现共同支持的教学判断。"
            ),
        ),
        node3_differential=Node3Differential(
            candidates=candidates,
            recommended_next_questions=questions,
        ),
        node4_conclusion=Node4Conclusion(
            final_syndrome=final_syndrome,
            confidence_level=confidence,
            pathogenesis=top_rule["pathogenesis"] if information_sufficient else f"候选病机：{top_rule['pathogenesis']}",
            treatment_principle=top_rule["treatment_principle"] if information_sufficient else "信息不足，暂不确定治法",
            uncertainty_note=uncertainty,
        ),
        node5_formula=Node5Formula(
            base_formula=top_rule["base_formula"] if formula_allowed else None,
            formula_target=top_rule["pathogenesis"] if formula_allowed else "待信息充分并排除危险信号后展示",
            formula_logic=formula_logic,
            modifications=modifications,
            safety_note=safety_note,
        ),
    )
