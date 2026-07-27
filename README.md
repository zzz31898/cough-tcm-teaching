# 咳辨 · 中医咳嗽辨证逻辑可视化教学系统

咳辨是一个面向中医学生、年轻医生和中医教师的教学辅助工具。它只聚焦”咳嗽”主诉，通过可复核的硬规则初筛和结构化解释，把症状、信息完整度、病位病性、候选证型、鉴别排除、病机治法与教材代表方串成一条可视化路径。

> 本系统仅用于中医辨证思维教学，不用于患者自诊或实际处方。系统不提供真实医疗诊断、不生成具体药物剂量，也不替代执业医师决策。

## 在线演示

🔗 **[https://cough-tcm-teaching.onrender.com](https://cough-tcm-teaching.onrender.com)**

在线版本运行在 Mock 模式下，完全基于规则引擎，无需 API Key 即可体验完整的辨证教学流程。

## 本地启动

需要 Python 3.11 或更高版本：

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

启动后打开 `http://127.0.0.1:8000`。

## Mock 模式与大模型 API

复制 `.env.example` 为 `.env`。默认 `MOCK_MODE=true`，无需 API Key 即可运行，结果完全来自规则引擎，便于课堂演示和单元测试。

如需启用 OpenAI-compatible API：

```env
MOCK_MODE=false
OPENAI_API_BASE=https://your-compatible-endpoint/v1
OPENAI_API_KEY=your-key
OPENAI_MODEL=your-model
LLM_TIMEOUT=30
```

如果服务端标注为 **OpenAI Responses API**（而不是 Chat Completions），补充：

```env
OPENAI_API_MODE=responses
```

例如 API Base URL 为 `https://example.com` 时，系统会请求 `https://example.com/v1/responses`。如 Base URL 已包含 `/v1` 或 `/responses`，系统会自动避免重复拼接路径。

后端先运行硬规则，再把前 3 个候选与允许使用的知识交给模型。模型返回值会经过 Pydantic Schema 校验；首次校验失败会执行一次 JSON 修复，仍失败则安全回退到硬规则结果。

## 知识库与规则

- `app/knowledge/cough_rules.py` 保存八个证型的知识规则、教材代表方、配伍说明和加减方向。
- `app/knowledge/symptom_aliases.py` 保存同义词与危险信号。
- `app/services/rule_engine.py` 负责标准化、匹配评分、证据提取、缺失信息和五节点结果生成。

增加新证型时，在 `COUGH_SYNDROMES` 中增加同样结构的字典即可。确保 `syndrome` 唯一，并补充病位、病性、核心/支持/矛盾证据、舌脉、治法、代表方和允许的加减规则。前端知识范围弹窗会自动读取新的证型。

## 增加演示病例

在 `app/knowledge/cough_rules.py` 的 `EXAMPLE_CASES` 中增加：

```python
{
    "id": "my-case",
    "title": "病例标题",
    "hint": "病例教学提示",
    "symptoms": ["咳嗽", "示例症状"],
    "tongue": "舌象",
    "pulse": "脉象",
    "other_information": "病程或诱因",
}
```

## 测试

```bash
pytest -q
```

测试覆盖四类典型证型、信息不足、危险信号拦截、API Schema、知识树和演示病例接口。

## API

- `GET /`：教学工作台。
- `GET /api/knowledge-tree`：八类证型的简化知识树。
- `GET /api/example-cases`：演示病例。
- `POST /api/rule-analyze`：仅运行硬规则。
- `POST /api/analyze`：硬规则 + 可选结构化模型解释。

请求体示例：

```json
{
  "symptoms": ["咳嗽", "痰黄黏稠", "口渴"],
  "tongue": "舌红，苔黄腻",
  "pulse": "脉滑数",
  "other_information": ""
}
```

## 安全边界

规则引擎会识别咯血、明显呼吸困难、胸痛、高热持续、意识异常、口唇发紫、明显喘憋，以及长期咳嗽伴明显消瘦。触发后页面显示提醒，仍可以继续查看教学型辨证路径，但 `node5_formula.base_formula` 必须为 `null`，并提示及时进行正规医学评估。
