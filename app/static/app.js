const state = {
  symptoms: [],
  result: null,
  activeNode: 1,
  selectedCandidate: 0,
  examples: [],
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setTags() {
  $("#tag-list").innerHTML = state.symptoms.map((item, index) => `
    <span class="tag">${escapeHtml(item)}<button type="button" aria-label="移除${escapeHtml(item)}" data-remove-tag="${index}">×</button></span>
  `).join("");
}

function addSymptom(raw) {
  const value = raw.trim().replace(/[，,、]+$/, "");
  if (!value || state.symptoms.includes(value)) return;
  state.symptoms.push(value);
  setTags();
}

function readCase() {
  return {
    symptoms: state.symptoms,
    tongue: $("#tongue").value.trim(),
    pulse: $("#pulse").value.trim(),
    other_information: $("#other-information").value.trim(),
  };
}

function setLoading(loading) {
  const button = $("#run-analysis");
  button.disabled = loading;
  button.querySelector("span:first-child").textContent = loading ? "推演中…" : "开始推演";
  $("#analysis-state").textContent = loading ? "正在拆解证据" : "待输入病例";
}

function evidenceList(items = [], kind = "") {
  if (!items.length) return `<div class="summary-copy">暂无直接证据记录。</div>`;
  return `<div class="evidence-list">${items.map((item) => `<div class="evidence-item ${kind}">${escapeHtml(item)}</div>`).join("")}</div>`;
}

function chips(items = [], kind = "") {
  if (!items.length) return `<span class="small-chip">暂无</span>`;
  return `<div class="chip-row">${items.map((item) => `<span class="small-chip ${kind}">${escapeHtml(item)}</span>`).join("")}</div>`;
}

function section(title, content, suffix = "") {
  return `<div class="subsection"><div class="subsection-heading"><strong>${title}</strong><span>${suffix}</span></div>${content}</div>`;
}

function renderNode1(result) {
  const node = result.node1_symptoms;
  const count = node.normalized_symptoms.length;
  const flagCount = node.red_flags.length;
  return `
    <div class="reasoning-flow">
      <div class="flow-step">
        <div class="flow-icon">1</div>
        <div class="flow-content">
          <div class="flow-label">输入症状标准化</div>
          <div class="flow-text">识别到 <span class="flow-highlight">${count} 个</span>症状特征</div>
        </div>
      </div>
      <div class="flow-step">
        <div class="flow-icon">2</div>
        <div class="flow-content">
          <div class="flow-label">信息完整度评估</div>
          <div class="flow-text">${node.information_sufficient ? '✓ 信息充足，可进入辨证' : '⚠ 需补充关键信息'}</div>
        </div>
      </div>
      ${flagCount > 0 ? `<div class="flow-step">
        <div class="flow-icon" style="background: #fdeaea; color: #c53030;">!</div>
        <div class="flow-content">
          <div class="flow-label">危险信号检测</div>
          <div class="flow-text">识别到 <span class="flow-highlight" style="background: #fdeaea; color: #c53030;">${flagCount} 个</span>危险信号</div>
        </div>
      </div>` : ''}
    </div>
    <div class="metric-strip">
      <div class="metric"><span>识别症状</span><strong>${count}</strong></div>
      <div class="metric"><span>补充项</span><strong>${node.missing_information.length}</strong></div>
      <div class="metric"><span>危险信号</span><strong class="${flagCount ? "danger-text" : ""}">${flagCount}</strong></div>
    </div>
    ${section("已识别症状", chips(node.normalized_symptoms, "red"), "NORMALIZED")}
    ${section("舌象", chips(node.tongue), "TONGUE")}
    ${section("脉象", chips(node.pulse), "PULSE")}
    ${section("信息完整度", `<div class="summary-copy">${node.information_sufficient ? "当前信息足够继续进入证型与治法判断。" : "当前不能唯一辨证，先保留候选路径并补充关键问诊信息。"}</div>`)}
    ${node.red_flags.length ? section("危险信号", evidenceList(node.red_flags, "contradictory"), "PRIORITY") : ""}
    ${section("建议补充", evidenceList(node.missing_information, "missing"), "NEXT")}
  `;
}

function renderNode2(result) {
  const node = result.node2_location_nature;
  const renderNamed = (items) => items.length ? `<div class="evidence-list">${items.map((item) => `<div class="evidence-item"><strong>${escapeHtml(item.name)}</strong><span>${escapeHtml(item.evidence.join(" · "))}</span></div>`).join("")}</div>` : `<div class="summary-copy">尚无足够证据。</div>`;

  // 构建推理链条
  const locations = node.locations.map(l => l.name).join(" / ");
  const natures = node.natures.slice(0, 3).map(n => n.name).join(" / ");

  return `
    <div class="reasoning-flow">
      <div class="flow-step">
        <div class="flow-icon">◎</div>
        <div class="flow-content">
          <div class="flow-label">多症状综合分析</div>
          <div class="flow-text">从症状群提取共同特征</div>
        </div>
      </div>
      <div class="flow-step">
        <div class="flow-icon">◒</div>
        <div class="flow-content">
          <div class="flow-label">病位定位</div>
          <div class="flow-text">证据指向 <span class="flow-highlight">${locations || "尚未明确"}</span></div>
        </div>
      </div>
      <div class="flow-step">
        <div class="flow-icon">◐</div>
        <div class="flow-content">
          <div class="flow-label">病性判断</div>
          <div class="flow-text">倾向于 <span class="flow-highlight">${natures || "待补充"}</span></div>
        </div>
      </div>
    </div>

    <div class="reasoning-chain">
      <span class="chain-node">症状群</span>
      <span class="chain-arrow">→</span>
      <span class="chain-node">${locations || "病位?"}</span>
      <span class="chain-arrow">→</span>
      <span class="chain-node">${natures || "病性?"}</span>
    </div>

    ${section("病位候选", renderNamed(node.locations), "LOCATION")}
    ${section("病性候选", renderNamed(node.natures), "NATURE")}
    ${section("共同证据摘要", `<div class="summary-copy">${escapeHtml(node.summary)}</div>`)}
  `;
}

function renderCandidateCard(candidate, index, active) {
  const width = Math.min(100, Math.max(4, candidate.rule_match_score * 6));
  return `
    <div class="candidate-card ${active ? "selected" : ""}" data-candidate-index="${index}" tabindex="0" role="button" aria-label="查看${escapeHtml(candidate.syndrome)}候选详情">
      <div class="candidate-head"><strong>${escapeHtml(candidate.syndrome)}</strong><span class="score">规则匹配度 ${candidate.rule_match_score}</span></div>
      <div class="score-track"><span style="width:${width}%"></span></div>
      <div class="candidate-preview">${escapeHtml((candidate.supporting_evidence || []).slice(0, 3).join(" · ") || "尚无直接支持证据")}</div>
      ${active ? `<div class="candidate-detail">
        ${section("支持证据", evidenceList(candidate.supporting_evidence), "SUPPORT")}
        ${section("反对证据", evidenceList(candidate.contradictory_evidence, "contradictory"), "CONTRA")}
        ${section("缺失关键证据", evidenceList(candidate.missing_key_evidence, "missing"), "MISSING")}
        ${section("鉴别排除", evidenceList((candidate.why_not_other_syndromes || []).map((item) => `${item.syndrome}：${item.reason}`), "missing"), "WHY NOT")}
      </div>` : ""}
    </div>
  `;
}

function renderNode3(result) {
  const node = result.node3_differential;

  // 生成对比表格
  const comparisonTable = node.candidates.length > 1 ? `
    <div class="subsection">
      <div class="subsection-heading"><strong>证型对比</strong><span>COMPARISON</span></div>
      <table class="comparison-table">
        <thead>
          <tr>
            <th>证型</th>
            <th>匹配分</th>
            <th>支持证据</th>
            <th>缺失关键</th>
          </tr>
        </thead>
        <tbody>
          ${node.candidates.map((c, idx) => `
            <tr style="cursor: pointer;" data-candidate-index="${idx}">
              <td><strong>${escapeHtml(c.syndrome)}</strong></td>
              <td><span class="evidence-score">${c.rule_match_score}</span></td>
              <td>${escapeHtml((c.supporting_evidence || []).slice(0, 2).join(", "))}</td>
              <td style="color: var(--muted); font-size: 10px;">${escapeHtml((c.missing_key_evidence || []).slice(0, 2).join(", "))}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  ` : '';

  // 生成证据对比卡片
  const evidenceCompare = node.candidates.length > 1 ? `
    <div class="subsection">
      <div class="subsection-heading"><strong>证据强度对比</strong><span>EVIDENCE</span></div>
      <div class="evidence-compare">
        ${node.candidates.slice(0, 3).map(c => `
          <div class="evidence-card">
            <div class="evidence-card-header">
              <span class="evidence-card-title">${escapeHtml(c.syndrome)}</span>
              <span class="evidence-score">${c.rule_match_score}</span>
            </div>
            <div class="evidence-items">
              ${(c.supporting_evidence || []).slice(0, 3).map(e => `<span class="evidence-tag support">${escapeHtml(e)}</span>`).join("")}
              ${(c.contradictory_evidence || []).slice(0, 2).map(e => `<span class="evidence-tag contra">${escapeHtml(e)}</span>`).join("")}
            </div>
          </div>
        `).join("")}
      </div>
    </div>
  ` : '';

  return `
    <div class="reasoning-flow">
      <div class="flow-step">
        <div class="flow-icon">⌁</div>
        <div class="flow-content">
          <div class="flow-label">硬规则初筛</div>
          <div class="flow-text">从 8 个证型中筛选出前 <span class="flow-highlight">${node.candidates.length}</span> 个候选</div>
        </div>
      </div>
      <div class="flow-step">
        <div class="flow-icon">⚖</div>
        <div class="flow-content">
          <div class="flow-label">证据权重计算</div>
          <div class="flow-text">核心症状×3 + 支持症状×1 + 舌脉×2 - 矛盾×3</div>
        </div>
      </div>
      <div class="flow-step">
        <div class="flow-icon">✓</div>
        <div class="flow-content">
          <div class="flow-label">首选证型</div>
          <div class="flow-text"><span class="flow-highlight">${escapeHtml(node.candidates[0]?.syndrome || "待定")}</span> (分数: ${node.candidates[0]?.rule_match_score || 0})</div>
        </div>
      </div>
    </div>

    ${comparisonTable}
    ${evidenceCompare}

    <div class="subsection"><div class="subsection-heading"><strong>候选证型详情</strong><span>TOP ${node.candidates.length}</span></div>
      <div id="candidate-list">${node.candidates.map((candidate, index) => renderCandidateCard(candidate, index, index === state.selectedCandidate)).join("")}</div>
    </div>
    ${section("下一步建议补充", `<div class="question-list">${node.recommended_next_questions.map((item) => `<div class="question-item">${escapeHtml(item)}</div>`).join("") || `<div class="summary-copy">当前没有额外问题。</div>`}</div>`, "QUESTIONS")}
  `;
}

function renderNode4(result) {
  const node = result.node4_conclusion;
  const status = node.final_syndrome ? "TEACHING CONCLUSION" : "NOT ENOUGH TO CONCLUDE";

  // 置信度百分比
  const confidencePercent = node.confidence_level === "high" ? 85 : node.confidence_level === "medium" ? 60 : 30;
  const confidenceColor = node.confidence_level === "high" ? "var(--jade)" : node.confidence_level === "medium" ? "#d4a853" : "var(--cinnabar)";

  return `
    <div class="reasoning-flow">
      <div class="flow-step">
        <div class="flow-icon">✦</div>
        <div class="flow-content">
          <div class="flow-label">辨证结论</div>
          <div class="flow-text">${node.final_syndrome ? `确定为 <span class="flow-highlight">${escapeHtml(node.final_syndrome)}</span>` : '信息不足，暂不收敛'}</div>
        </div>
      </div>
      <div class="flow-step">
        <div class="flow-icon">◉</div>
        <div class="flow-content">
          <div class="flow-label">病机分析</div>
          <div class="flow-text">${escapeHtml(node.pathogenesis)}</div>
        </div>
      </div>
      <div class="flow-step">
        <div class="flow-icon">⚕</div>
        <div class="flow-content">
          <div class="flow-label">治法确定</div>
          <div class="flow-text">${escapeHtml(node.treatment_principle)}</div>
        </div>
      </div>
    </div>

    <div class="confidence-meter">
      <span class="confidence-label">置信度</span>
      <div class="confidence-bar">
        <div class="confidence-fill" style="width: ${confidencePercent}%; background: ${confidenceColor};"></div>
      </div>
      <span class="confidence-label">${confidencePercent}%</span>
    </div>

    <div class="conclusion-box">
      <span class="big-label">${status}</span>
      <h3>${escapeHtml(node.final_syndrome || "暂不收敛")}</h3>
      <p>${escapeHtml(node.pathogenesis)}</p>
      <span class="confidence">${node.confidence_level === "high" ? "高" : node.confidence_level === "medium" ? "中" : "低"}置信等级 · 规则解释</span>
    </div>
    ${section("治法", `<div class="summary-copy">${escapeHtml(node.treatment_principle)}</div>`)}
    ${section("仍然存在的不确定性", `<div class="summary-copy">${escapeHtml(node.uncertainty_note)}</div>`, "UNCERTAINTY")}
  `;
}

function renderNode5(result) {
  const node = result.node5_formula;
  if (!node.base_formula) {
    return `
      <div class="reasoning-flow">
        <div class="flow-step">
          <div class="flow-icon" style="background: #fdeaea; color: #c53030;">⊘</div>
          <div class="flow-content">
            <div class="flow-label">方剂展示条件</div>
            <div class="flow-text">${escapeHtml(node.safety_note)}</div>
          </div>
        </div>
      </div>
      <div class="formula-card">
        <div class="formula-title"><span>REPRESENTATIVE FORMULA</span><strong>暂不展示</strong></div>
        <div class="formula-target">${escapeHtml(node.safety_note)}</div>
      </div>
      ${node.formula_logic.length ? section("配伍提示", evidenceList(node.formula_logic.map((item) => `${item.herb_or_group}：${item.reason}`)), "TEACHING") : ""}
    `;
  }

  // 方剂思维导图
  const mindMap = `
    <div class="mind-map">
      <div class="mind-center">${escapeHtml(node.base_formula)}</div>
      <div class="mind-branches">
        ${node.formula_logic.slice(0, 4).map(item => `
          <div class="mind-branch">
            <div class="mind-branch-label">${escapeHtml(item.role)}</div>
            <div class="mind-branch-value">${escapeHtml(item.herb_or_group)}</div>
          </div>
        `).join("")}
      </div>
    </div>
  `;

  return `
    <div class="reasoning-flow">
      <div class="flow-step">
        <div class="flow-icon">◈</div>
        <div class="flow-content">
          <div class="flow-label">方剂选择</div>
          <div class="flow-text">教材代表方 <span class="flow-highlight">${escapeHtml(node.base_formula)}</span></div>
        </div>
      </div>
      <div class="flow-step">
        <div class="flow-icon">⚗</div>
        <div class="flow-content">
          <div class="flow-label">针对病机</div>
          <div class="flow-text">${escapeHtml(node.formula_target)}</div>
        </div>
      </div>
      ${node.modifications.length > 0 ? `<div class="flow-step">
        <div class="flow-icon">±</div>
        <div class="flow-content">
          <div class="flow-label">加减变化</div>
          <div class="flow-text">检测到 <span class="flow-highlight">${node.modifications.length}</span> 个加减方向</div>
        </div>
      </div>` : ''}
    </div>

    ${mindMap}

    <div class="formula-card">
      <div class="formula-title"><span>TEXTBOOK REPRESENTATIVE FORMULA</span><strong>${escapeHtml(node.base_formula)}</strong></div>
      <div class="formula-target">${escapeHtml(node.formula_target)}</div>
      <table class="logic-table"><thead><tr><th>药组</th><th>角色</th><th>针对病机</th></tr></thead><tbody>
        ${node.formula_logic.map((item) => `<tr><td>${escapeHtml(item.herb_or_group)}</td><td>${escapeHtml(item.role)}</td><td>${escapeHtml(item.reason)}</td></tr>`).join("")}
      </tbody></table>
    </div>
    ${node.modifications.length ? section("兼症加减方向", evidenceList(node.modifications.map((item) => `${item.trigger_symptom} → ${item.adjustment}（${item.reason}）`), "missing"), "HARD RULE") : ""}
    ${section("安全边界", `<div class="summary-copy">${escapeHtml(node.safety_note)}</div>`, "SAFETY")}
  `;
}

const nodeMeta = {
  1: ["症状与信息完整度", "先从病例中提取可见证据", "NODE 01", renderNode1],
  2: ["病位与病性", "多项表现共同指向，而非一症一结论", "NODE 02", renderNode2],
  3: ["候选证型与鉴别排除", "保留最多三条可复核路径", "NODE 03", renderNode3],
  4: ["最终证型 · 病机 · 治法", "结论与不确定性同时呈现", "NODE 04", renderNode4],
  5: ["教材代表方与配伍", "只展示知识库允许的教学逻辑", "NODE 05", renderNode5],
};

function renderInsight() {
  if (!state.result) return;
  const [title, subtitle, badge, renderer] = nodeMeta[state.activeNode];
  $("#insight-title").textContent = title;
  $("#insight-subtitle").textContent = subtitle;
  $("#node-badge").textContent = badge;
  $("#insight-content").innerHTML = renderer(state.result);
  $$(".logic-node").forEach((node) => node.classList.toggle("active", Number(node.dataset.node) === state.activeNode));

  // 候选卡片点击
  $$(".candidate-card").forEach((card) => {
    card.addEventListener("click", () => {
      state.selectedCandidate = Number(card.dataset.candidateIndex);
      renderInsight();
    });
  });

  // 对比表格行点击
  $$(".comparison-table tr[data-candidate-index]").forEach((row) => {
    row.addEventListener("click", () => {
      state.selectedCandidate = Number(row.dataset.candidateIndex);
      renderInsight();
    });
  });
}

function updateResult(result, mode = "mock") {
  state.result = result;
  state.selectedCandidate = 0;
  const statusLabels = { insufficient: "信息不足 · 保留路径", differential: "鉴别中 · 等待补充", concluded: "已形成教学结论" };
  $("#analysis-state").textContent = statusLabels[result.analysis_status] || "已完成推演";

  // 更新模式标签
  const modePill = $("#mode-pill");
  if (mode === "llm") {
    modePill.textContent = "AI 增强解释";
    modePill.style.background = "var(--jade)";
    modePill.style.color = "white";
    $("#engine-status-text").textContent = "AI 结构化解释已启用";
    $(".status-dot").style.background = "var(--jade)";

    // 在顶部增加 LLM 提示
    const insightPanel = $(".insight-panel");
    if (!$("#llm-notice")) {
      const notice = document.createElement("div");
      notice.id = "llm-notice";
      notice.className = "llm-enhanced";
      notice.innerHTML = `
        <div class="llm-badge">AI 增强模式</div>
        <div style="font-size: 11px; line-height: 1.6;">
          当前结果由<strong>硬规则初筛</strong>后，通过<strong>大模型结构化解释</strong>生成。
          推理路径完全基于规则引擎，模型仅负责教学性解释。
        </div>
      `;
      insightPanel.insertBefore(notice, $(".insight-title-row"));
    }
  } else if (mode === "fallback") {
    modePill.textContent = "规则回退";
    modePill.style.background = "#d4a853";
    modePill.style.color = "white";
    $("#engine-status-text").textContent = "规则引擎在线（AI暂不可用）";
    const llmNotice = $("#llm-notice");
    if (llmNotice) llmNotice.remove();
  } else {
    modePill.textContent = "演示模式";
    modePill.style.background = "";
    modePill.style.color = "";
    $("#engine-status-text").textContent = "规则引擎在线";
    const llmNotice = $("#llm-notice");
    if (llmNotice) llmNotice.remove();
  }

  const flags = result.node1_symptoms.red_flags || [];
  if (flags.length) {
    $("#warning-text").textContent = `已识别：${flags.join("、")}。请及时进行正规医学评估；当前仅保留教学型辨证展示。`;
    $("#warning-banner").hidden = false;
  } else {
    $("#warning-banner").hidden = true;
  }
  renderInsight();
}

async function runAnalysis() {
  const payload = readCase();
  if (!payload.symptoms.length) {
    addSymptom("咳嗽");
  }
  setLoading(true);
  try {
    const response = await fetch("/api/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(readCase()) });
    if (!response.ok) throw new Error("分析接口暂不可用");
    const data = await response.json();
    updateResult(data.result, data.mode);
  } catch (error) {
    $("#analysis-state").textContent = "暂时无法连接";
    $("#insight-content").innerHTML = `<div class="empty-insight"><div class="empty-mark">!</div><h3>推演没有完成</h3><p>${escapeHtml(error.message)}。请确认本地服务已启动后重试。</p></div>`;
  } finally {
    setLoading(false);
  }
}

function fillExample(example) {
  state.symptoms = [...example.symptoms];
  setTags();
  $("#tongue").value = example.tongue || "";
  $("#pulse").value = example.pulse || "";
  $("#other-information").value = example.other_information || "";
  $("#analysis-state").textContent = "已载入演示病例";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function loadExamples() {
  try {
    const response = await fetch("/api/example-cases");
    const data = await response.json();
    state.examples = data.cases || [];
    $("#example-list").innerHTML = state.examples.map((item, index) => `
      <button type="button" class="example-card" data-example-id="${escapeHtml(item.id)}">
        <span class="example-number">${String(index + 1).padStart(2, "0")}</span>
        <span><span class="example-title">${escapeHtml(item.title)}</span><span class="example-hint">${escapeHtml(item.hint)}</span></span>
      </button>
    `).join("");
    $$(".example-card").forEach((button) => button.addEventListener("click", () => fillExample(state.examples.find((item) => item.id === button.dataset.exampleId))));
  } catch {
    $("#example-list").innerHTML = `<div class="summary-copy">演示病例加载失败，请直接输入。</div>`;
  }
}

async function loadKnowledge() {
  const response = await fetch("/api/knowledge-tree");
  const data = await response.json();
  $("#syndrome-grid").innerHTML = data.syndromes.map((item) => `
    <div class="syndrome-item"><strong>${escapeHtml(item.syndrome)}</strong><p>${escapeHtml(item.treatment_principle)} · ${escapeHtml(item.base_formula)}</p></div>
  `).join("");
}

function resetCase() {
  state.symptoms = [];
  state.result = null;
  setTags();
  $("#tongue").value = "";
  $("#pulse").value = "";
  $("#other-information").value = "";
  $("#analysis-state").textContent = "待输入病例";
  $("#mode-pill").textContent = "MOCK MODE";
  $("#insight-title").textContent = "症状与信息完整度";
  $("#insight-subtitle").textContent = "先从病例中提取可见证据";
  $("#node-badge").textContent = "NODE 01";
  $("#insight-content").innerHTML = `<div class="empty-insight"><div class="empty-mark">◌</div><h3>等待一份病例</h3><p>选择左侧演示病例，或输入症状后开始推演。每个节点都会保留“为什么”。</p></div>`;
  $("#warning-banner").hidden = true;
}

$("#add-tag").addEventListener("click", () => { addSymptom($("#symptom-input").value); $("#symptom-input").value = ""; $("#symptom-input").focus(); });
$("#symptom-input").addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === "、" || event.key === ",") { event.preventDefault(); addSymptom(event.target.value); event.target.value = ""; }
});
$("#tag-editor").addEventListener("click", (event) => {
  const index = event.target.dataset.removeTag;
  if (index !== undefined) { state.symptoms.splice(Number(index), 1); setTags(); }
});
$$("[data-symptom]").forEach((button) => button.addEventListener("click", () => addSymptom(button.dataset.symptom)));
$("#run-analysis").addEventListener("click", runAnalysis);
$("#reset-case").addEventListener("click", resetCase);
$$(".logic-node").forEach((node) => node.addEventListener("click", () => { state.activeNode = Number(node.dataset.node); renderInsight(); }));
$("#dismiss-warning").addEventListener("click", () => { $("#warning-banner").hidden = true; });
$("#knowledge-button").addEventListener("click", () => { $("#knowledge-modal").hidden = false; loadKnowledge(); });
$("#close-modal").addEventListener("click", () => { $("#knowledge-modal").hidden = true; });
$("#knowledge-modal").addEventListener("click", (event) => { if (event.target.id === "knowledge-modal") $("#knowledge-modal").hidden = true; });
$("#refresh-examples").addEventListener("click", () => loadExamples());

setTags();
loadExamples();
