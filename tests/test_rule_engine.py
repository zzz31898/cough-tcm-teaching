from app.models.schemas import CaseInput
from app.services.rule_engine import analyze_case


def _top(case: CaseInput) -> str:
    return analyze_case(case).node3_differential.candidates[0].syndrome


def test_phlegm_heat_is_prioritized():
    result = analyze_case(
        CaseInput(
            symptoms=["咳嗽气粗", "痰黄黏稠", "痰难咯", "口渴"],
            tongue="舌红，苔黄腻",
            pulse="脉滑数",
        )
    )
    assert _top(CaseInput(symptoms=["痰黄黏稠", "口渴"], tongue="舌红苔黄腻", pulse="脉滑数")) == "痰热郁肺"
    assert result.node4_conclusion.final_syndrome == "痰热郁肺"


def test_wind_cold_is_prioritized():
    result = analyze_case(
        CaseInput(
            symptoms=["咳嗽声重", "痰白清稀", "恶寒", "无汗"],
            tongue="苔薄白",
            pulse="脉浮紧",
        )
    )
    assert _top(result_case := CaseInput(symptoms=["咳嗽声重", "痰白清稀", "恶寒", "无汗"], tongue="苔薄白", pulse="脉浮紧")) == "风寒袭肺"
    assert result.node3_differential.candidates[0].syndrome == "风寒袭肺"


def test_lung_yin_is_prioritized():
    result = analyze_case(
        CaseInput(
            symptoms=["干咳少痰", "咽干", "声音嘶哑"],
            tongue="舌红少苔",
            pulse="脉细数",
        )
    )
    assert _top(CaseInput(symptoms=["干咳少痰", "咽干"], tongue="舌红少苔", pulse="脉细数")) == "肺阴亏耗"
    assert result.node3_differential.candidates[0].syndrome == "肺阴亏耗"


def test_liver_fire_is_prioritized():
    result = analyze_case(
        CaseInput(
            symptoms=["咳嗽与情绪相关", "胸胁胀痛", "口苦"],
            tongue="舌红，苔薄黄",
            pulse="脉弦数",
        )
    )
    assert result.node3_differential.candidates[0].syndrome == "肝火犯肺"
    assert result.node4_conclusion.final_syndrome == "肝火犯肺"


def test_sparse_input_stays_differential_without_formula():
    result = analyze_case(CaseInput(symptoms=["咳嗽", "痰多"]))
    assert result.analysis_status in {"insufficient", "differential"}
    assert result.node4_conclusion.final_syndrome is None
    assert result.node5_formula.base_formula is None
    assert len(result.node3_differential.candidates) == 3


def test_red_flag_hides_formula():
    result = analyze_case(
        CaseInput(
            symptoms=["咳嗽气粗", "痰黄黏稠", "胸痛", "口渴"],
            tongue="舌红，苔黄腻",
            pulse="脉滑数",
        )
    )
    assert "胸痛" in result.node1_symptoms.red_flags
    assert result.node5_formula.base_formula is None
    assert result.node4_conclusion.confidence_level == "low"
