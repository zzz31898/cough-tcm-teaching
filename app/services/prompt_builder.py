from __future__ import annotations

import json

from app.knowledge.cough_rules import SYNDROME_BY_NAME
from app.models.schemas import AnalysisResponse, CaseInput


SYSTEM_PROMPT = """你是“咳嗽中医辨证思维教学助手”。
你的任务不是替患者诊断，也不是生成真实临床处方，而是在教学系统中对咳嗽病例做结构化辨证展示。
分析范围仅限：风寒袭肺、风热犯肺、风燥伤肺、痰湿蕴肺、痰热郁肺、肝火犯肺、肺阴亏耗、肺气虚。
以硬规则候选为推理锚点，只可使用给定知识。不得新增证型、方剂、药物、剂量、古籍引文或疗效结论。
信息不足时不得强行收敛，final_syndrome 与 base_formula 必须为 null。
有危险信号时 base_formula 必须为 null，并明确建议正规医学评估。
只输出严格合法、符合给定 Schema 的 JSON，不输出 Markdown、注释或额外文字。"""


REPAIR_PROMPT = """上一次输出未通过 JSON Schema 校验。
错误：
{validation_errors}

原始输出：
{invalid_output}

只修复格式与字段一致性。不得改变病例事实，不得增加症状、证型、方剂或药物。
只输出一个合法 JSON 对象；删除未定义字段；补齐必填字段；不确定时用 null、空数组或明确说明。
信息不足或存在危险信号时 base_formula 必须为 null。"""


def build_user_prompt(case: CaseInput, rule_result: AnalysisResponse) -> str:
    allowed_knowledge: list[dict] = []
    for candidate in rule_result.node3_differential.candidates:
        rule = SYNDROME_BY_NAME[candidate.syndrome]
        allowed_knowledge.append(
            {
                "syndrome": rule["syndrome"],
                "treatment_principle": rule["treatment_principle"],
                "base_formula": rule["base_formula"],
                "formula_explanation": rule["formula_explanation"],
                "modification_rules": rule["modification_rules"],
            }
        )

    schema_hint = {
        "case_scope": "cough",
        "analysis_status": "insufficient | differential | concluded",
        "node1_symptoms": "按系统 Schema 完整返回",
        "node2_location_nature": "按系统 Schema 完整返回",
        "node3_differential": "最多3个候选",
        "node4_conclusion": "信息不足时 final_syndrome=null",
        "node5_formula": "信息不足或危险信号时 base_formula=null",
    }
    return f"""请根据病例、硬规则结果和允许知识，生成五节点教学分析。

【病例原始输入】
{json.dumps(case.model_dump(), ensure_ascii=False)}

【硬规则初筛结果】
{rule_result.model_dump_json()}

【允许使用的知识】
{json.dumps(allowed_knowledge, ensure_ascii=False)}

【返回结构提示】
{json.dumps(schema_hint, ensure_ascii=False)}

最多保留3个候选；逐一说明支持、矛盾、缺失证据及鉴别理由。
代表方和加减仅可来自允许知识；不输出剂量；只输出 JSON。"""
