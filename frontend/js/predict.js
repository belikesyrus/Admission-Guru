/**
 * predict.js — Drives the 3-step prediction flow.
 */

// Use absolute URL so it works whether page is opened via Flask or file://
const API = (location.protocol === "file:" || location.hostname === "")
  ? "http://localhost:5000/api"
  : "/api";

// ── Server health check ───────────────────────────────────────────────────────

async function checkServerHealth() {
  const banner = document.getElementById("serverOfflineBanner");
  if (!banner) return;
  try {
    // Try /health first (simplest), then /api/health as fallback
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4000);
    const res = await fetch(`${API.replace("/api", "")}/health`, { signal: controller.signal });
    clearTimeout(timeout);
    banner.style.display = res.ok ? "none" : "";
  } catch {
    banner.style.display = "";
  }
}
let currentExam      = null;
let metaData         = {};
let lastResults      = [];   // raw array from server, index = originalIdx
let lastInputSummary = {};
let removedRows      = new Set();  // set of originalIdx values

// ── Exam config ───────────────────────────────────────────────────────────────

const EXAM_CONFIG = {
  CET: {
    title:    "CET Engineering",
    subtitle: "Enter your MHT-CET details",
    scoreLabel: "CET Percentile",
    scoreField: "percentile",
    scoreMin: 0, scoreMax: 100, scoreStep: 0.0001,
    showRound: true, showTFWS: true, showGender: true,
    showCollegeType: true, showUniversity: true,
  },
  DSY_Engineering: {
    title:    "Direct 2nd Year Engineering",
    subtitle: "Diploma holders — enter your details",
    scoreLabel: "Diploma Percentage",
    scoreField: "percentile",
    scoreMin: 0, scoreMax: 100, scoreStep: 0.01,
    showRound: true, showTFWS: true, showGender: true,
    showCollegeType: false, showUniversity: true,
  },
  Diploma: {
    title:    "Diploma (Post SSC)",
    subtitle: "Post-SSC Diploma admission details",
    scoreLabel: "SSC / Entrance Marks (%)",
    scoreField: "percentile",
    scoreMin: 0, scoreMax: 100, scoreStep: 0.01,
    showRound: true, showTFWS: false, showGender: true,
    showCollegeType: false, showUniversity: false,
  },
  Pharmacy: {
    title:    "Pharmacy (B.Pharm / Pharm.D)",
    subtitle: "CET-based pharmacy admission",
    scoreLabel: "CET Percentile",
    scoreField: "percentile",
    scoreMin: 0, scoreMax: 100, scoreStep: 0.0001,
    showRound: true, showTFWS: false, showGender: true,
    showCollegeType: false, showUniversity: true,
  },
  DSY_Pharmacy: {
    title:    "Direct 2nd Year Pharmacy",
    subtitle: "Diploma → B.Pharmacy lateral entry",
    scoreLabel: "Diploma Percentage",
    scoreField: "percentile",
    scoreMin: 0, scoreMax: 100, scoreStep: 0.01,
    showRound: true, showTFWS: true, showGender: true,
    showCollegeType: false, showUniversity: false,
  },
};

const ROUND_OPTIONS = [
  { value: "",     label: "All Rounds" },
  { value: "CAP1", label: "CAP Round I" },
  { value: "CAP2", label: "CAP Round II" },
  { value: "CAP3", label: "CAP Round III" },
  { value: "CAP4", label: "CAP Round IV / Institute Level" },
];

const GENDER_OPTIONS = [
  { value: "",       label: "Any Gender" },
  { value: "Male",   label: "Male" },
  { value: "Female", label: "Female" },
];

const COLLEGE_TYPE_OPTIONS = [
  { value: "",                    label: "All Types" },
  { value: "Government Autonomous", label: "Government Autonomous" },
  { value: "Government Aided",    label: "Government Aided" },
  { value: "Government",          label: "Government" },
  { value: "Un-Aided",            label: "Un-Aided / Private" },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function qs(sel)  { return document.querySelector(sel); }
function qsa(sel) { return [...document.querySelectorAll(sel)]; }

function setStepUI(step) {
  qsa(".step-dot").forEach(d => {
    const n = parseInt(d.dataset.step);
    d.classList.remove("active", "done");
    if (n < step)   d.classList.add("done");
    if (n === step) d.classList.add("active");
  });
  qsa(".step-label").forEach(d => {
    const n = parseInt(d.dataset.step);
    d.classList.remove("active", "done");
    if (n < step)   d.classList.add("done");
    if (n === step) d.classList.add("active");
  });
  const line12 = document.getElementById("line-1-2");
  const line23 = document.getElementById("line-2-3");
  if (line12) line12.classList.toggle("done", step > 1);
  if (line23) line23.classList.toggle("done", step > 2);
}

function showStep(n) {
  qsa(".step-panel").forEach(p => p.classList.remove("active"));
  const el = document.getElementById(`step${n}`);
  if (el) el.classList.add("active");
  setStepUI(n);
  window.scrollTo({ top: 60, behavior: "smooth" });
}

function showAlert(msg, type = "error") {
  const box = document.getElementById("alertBox");
  if (!box) return;
  box.innerHTML = `<div class="alert alert-${type}">⚠️ ${msg}</div>`;
  box.style.display = "";
}

function clearAlert() {
  const box = document.getElementById("alertBox");
  if (box) { box.innerHTML = ""; box.style.display = "none"; }
}

function escHtml(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function makeSelect(id, label, options, hint = "") {
  return `
    <div class="form-group">
      <label class="form-label" for="${id}">${label}</label>
      <select class="form-select" id="${id}" name="${id}">
        ${options.map(o => `<option value="${escHtml(o.value)}">${escHtml(o.label)}</option>`).join("")}
      </select>
      ${hint ? `<span class="form-hint">${hint}</span>` : ""}
    </div>`;
}

function makeInput(id, label, type, min, max, step, placeholder, hint = "") {
  return `
    <div class="form-group">
      <label class="form-label" for="${id}">${label}</label>
      <input class="form-input" id="${id}" name="${id}"
             type="${type}" min="${min}" max="${max}" step="${step}"
             placeholder="${placeholder}" autocomplete="off" />
      ${hint ? `<span class="form-hint">${hint}</span>` : ""}
    </div>`;
}

function makeToggle(id, label, hint = "") {
  return `
    <div class="form-group full">
      <label class="form-label">${label}
        ${hint ? `<span class="tooltip">ℹ️<span class="tooltip-text">${hint}</span></span>` : ""}
      </label>
      <div class="toggle-switch">
        <input type="checkbox" id="${id}" name="${id}" />
        <label class="toggle-label" for="${id}">Apply TFWS filter</label>
      </div>
    </div>`;
}

// ── Load meta from backend ────────────────────────────────────────────────────

async function loadMeta(examType) {
  try {
    const res = await fetch(`${API}/meta/${examType}`);
    if (!res.ok) return {};
    return await res.json();
  } catch {
    return {};
  }
}

// ── Build form ────────────────────────────────────────────────────────────────

async function buildForm(examType) {
  const cfg = EXAM_CONFIG[examType];
  if (!cfg) return;

  document.getElementById("formTitle").textContent    = cfg.title;
  document.getElementById("formSubtitle").textContent = cfg.subtitle;

  // Show a loading skeleton while meta loads
  document.getElementById("formFields").innerHTML =
    `<div class="form-group full"><div class="loading-spinner" style="padding:1rem"><div class="spinner"></div></div></div>`;

  metaData = await loadMeta(examType);

  const branchOptions = [
    { value: "", label: "All Branches" },
    ...(metaData.branches || []).map(b => ({ value: b, label: b }))
  ];
  const categoryOptions = [
    { value: "", label: "All Categories" },
    ...(metaData.categories || []).map(c => ({ value: c, label: c }))
  ];
  const universityOptions = [
    { value: "", label: "All Universities" },
    ...(metaData.universities || []).filter(Boolean).map(u => ({ value: u, label: u }))
  ];

  let html = "";

  // Score input — always first, full width
  html += `<div class="form-group full">
      <label class="form-label" for="scoreInput">
        ${cfg.scoreLabel} <span style="color:var(--red-500)">*</span>
      </label>
      <input class="form-input" id="scoreInput" name="scoreInput"
             type="number" min="${cfg.scoreMin}" max="${cfg.scoreMax}" step="${cfg.scoreStep}"
             placeholder="e.g. ${examType === 'CET' ? '92.35' : '78.5'}" autocomplete="off" />
      <span class="form-hint">${
        examType === "CET" || examType === "Pharmacy"
          ? "Enter as shown on your score card (e.g. 92.35)"
          : "Enter your percentage (e.g. 78.5)"
      }</span>
    </div>`;

  // Branch
  html += makeSelect("branch", "Preferred Branch", branchOptions,
    "Leave as 'All Branches' to see all options");

  // Category
  html += makeSelect("category", "Your Category", categoryOptions,
    "Select your reservation category exactly");

  // Round
  if (cfg.showRound) {
    html += makeSelect("cap_round", "CAP Round", ROUND_OPTIONS,
      "Select a specific round or 'All Rounds' for the widest results");
  }

  // Gender
  if (cfg.showGender) {
    html += makeSelect("gender", "Gender", GENDER_OPTIONS,
      "Female students can see both General and Ladies seats");
  }

  // College type
  if (cfg.showCollegeType) {
    html += makeSelect("college_type", "College Type", COLLEGE_TYPE_OPTIONS);
  }

  // University
  if (cfg.showUniversity && universityOptions.length > 1) {
    html += makeSelect("home_university", "Home University", universityOptions,
      "Affects Home University vs. State Level seat eligibility");
  }

  // TFWS toggle — full width
  if (cfg.showTFWS) {
    html += makeToggle("tfws", "TFWS (Tuition Fee Waiver Scheme)",
      "Show only TFWS-eligible seats — these offer full tuition fee waiver regardless of category");
  }

  document.getElementById("formFields").innerHTML = html;
}

// ── Form submit ───────────────────────────────────────────────────────────────

async function handlePredict(e) {
  e.preventDefault();
  clearAlert();

  const cfg   = EXAM_CONFIG[currentExam];
  const score = parseFloat(qs("#scoreInput")?.value);
  if (isNaN(score) || score <= 0 || score > 100) {
    showAlert("Please enter a valid score/percentile between 0 and 100.");
    qs("#scoreInput")?.focus();
    return;
  }

  const params = {
    exam_type:       currentExam,
    [cfg.scoreField]: score,
    branch:          qs("#branch")?.value          || "",
    category:        qs("#category")?.value        || "",
    cap_round:       qs("#cap_round")?.value       || "",
    gender:          qs("#gender")?.value          || "",
    college_type:    qs("#college_type")?.value    || "",
    home_university: qs("#home_university")?.value || "",
    tfws:            qs("#tfws")?.checked          || false,
  };

  // Human-readable summary for PDF / display
  lastInputSummary = {};
  lastInputSummary["Exam Type"]     = EXAM_CONFIG[currentExam]?.title || currentExam;
  lastInputSummary[cfg.scoreLabel]  = score;
  if (params.branch)          lastInputSummary["Branch"]       = params.branch;
  if (params.category)        lastInputSummary["Category"]     = params.category;
  if (params.cap_round)       lastInputSummary["CAP Round"]    = params.cap_round;
  if (params.gender)          lastInputSummary["Gender"]       = params.gender;
  if (params.college_type)    lastInputSummary["College Type"] = params.college_type;
  if (params.home_university) lastInputSummary["University"]   = params.home_university;
  if (params.tfws)            lastInputSummary["TFWS"]         = "Yes";

  // Loading state
  const btn = qs("#predictBtn");
  btn.disabled = true;
  qs("#predictBtnText").style.display   = "none";
  qs("#predictBtnLoader").style.display = "";

  try {
    const res  = await fetch(`${API}/predict`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(params),
    });
    const data = await res.json();

    if (!res.ok) {
      showAlert(data.error || "Prediction failed. Please try again.");
      return;
    }

    lastResults = data.results || [];
    removedRows = new Set();
    renderResults(lastResults, lastInputSummary);
    showStep(3);

  } catch {
    showAlert("Network error — make sure the server is running at localhost:5000.");
  } finally {
    btn.disabled = false;
    qs("#predictBtnText").style.display   = "";
    qs("#predictBtnLoader").style.display = "none";
  }
}

// ── Render results (main results page) ───────────────────────────────────────

function renderResults(results, summary) {
  const step3 = document.getElementById("step3");

  if (results.length === 0) {
    step3.innerHTML = `
      <div class="card">
        <div class="results-header">
          <div><div class="results-title">Your College Preference List</div></div>
          <div class="results-actions">
            <button class="btn-ghost" onclick="showStep(2)">← Edit Inputs</button>
          </div>
        </div>
        <div class="empty-state" style="padding:3rem 1.5rem">
          <div class="empty-icon">🔍</div>
          <h3>No colleges found</h3>
          <p>No colleges matched your criteria. Try widening your filters —<br>
             select "All Branches", "All Categories", or "All Rounds".</p>
          <button class="btn-primary" onclick="showStep(2)" style="margin-top:1.25rem">← Adjust Filters</button>
        </div>
      </div>`;
    return;
  }

  // Count chance tiers (always from full results, ignoring removedRows for counts)
  const chanceCounts = { Safe: 0, Moderate: 0, Ambitious: 0 };
  results.forEach(r => { if (r.chance in chanceCounts) chanceCounts[r.chance]++; });

  // Active (non-removed) rows
  const visibleCount = results.filter((_, i) => !removedRows.has(i)).length;

  step3.innerHTML = `
    <div class="card">
      <!-- Header -->
      <div class="results-header">
        <div>
          <div class="results-title">Your College Preference List</div>
          <div class="results-count">
            <span id="visibleCountLabel">${visibleCount} of ${results.length} colleges shown</span>
            &nbsp;—&nbsp;
            <span class="badge badge-safe">${chanceCounts.Safe} Safe</span>&nbsp;
            <span class="badge badge-moderate">${chanceCounts.Moderate} Moderate</span>&nbsp;
            <span class="badge badge-ambitious">${chanceCounts.Ambitious} Ambitious</span>
          </div>
        </div>
        <div class="results-actions">
          <button class="btn-ghost" onclick="showStep(2)">← Edit Inputs</button>
          <button class="btn-outline" id="saveListBtn">💾 Save List</button>
          <button class="btn-orange"  id="pdfBtn">⬇ Download PDF</button>
        </div>
      </div>

      <!-- Input summary strip -->
      <div class="summary-card">
        <strong>Your inputs:</strong>
        <div class="summary-grid">
          ${Object.entries(summary).map(([k, v]) =>
            `<div class="summary-item"><span class="summary-key">${escHtml(k)}:</span><span>${escHtml(String(v))}</span></div>`
          ).join("")}
        </div>
      </div>

      <!-- Filter / sort bar -->
      <div class="filter-bar">
        <div class="form-group">
          <label class="form-label">Filter by Chance</label>
          <select class="form-select" id="filterChance">
            <option value="">All</option>
            <option value="Safe">Safe</option>
            <option value="Moderate">Moderate</option>
            <option value="Ambitious">Ambitious</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Sort by</label>
          <select class="form-select" id="sortBy">
            <option value="chance">Admission Chance</option>
            <option value="cutoff_desc">Cutoff % (High → Low)</option>
            <option value="cutoff_asc">Cutoff % (Low → High)</option>
            <option value="college_name">College Name (A–Z)</option>
            <option value="college_type">College Type</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Search</label>
          <input class="form-select" id="searchCollege"
                 placeholder="College or branch name…"
                 style="font-size:.82rem;padding:.45rem .7rem" autocomplete="off" />
        </div>
      </div>

      <!-- Results table -->
      <div class="table-wrapper" id="resultsTableWrapper"></div>

      <!-- Save prompt for guests -->
      ${!AuthState.isLoggedIn() ? `
        <div class="save-prompt" style="margin-top:1.25rem">
          <span>💡 <strong>Sign up free</strong> to save this list and access it anytime.</span>
          <div style="display:flex;gap:.5rem">
            <a href="signup.html" class="btn-primary-sm">Sign Up</a>
            <a href="login.html"  class="btn-outline-sm">Login</a>
          </div>
        </div>` : ""}
    </div>`;

  // Attach events
  document.getElementById("filterChance")?.addEventListener("change", refreshTable);
  document.getElementById("sortBy")?.addEventListener("change",       refreshTable);
  document.getElementById("searchCollege")?.addEventListener("input", refreshTable);
  document.getElementById("pdfBtn")?.addEventListener("click",        downloadPDF);
  document.getElementById("saveListBtn")?.addEventListener("click",   saveList);

  // Initial table render
  refreshTable();
}

// ── Table render (applies current filters/sort) ───────────────────────────────

function refreshTable() {
  const chanceF = (document.getElementById("filterChance")?.value || "").trim();
  const sortKey = (document.getElementById("sortBy")?.value       || "chance");
  const searchQ = (document.getElementById("searchCollege")?.value || "").toLowerCase().trim();

  const chanceOrder = { Safe: 0, Moderate: 1, Ambitious: 2, Unknown: 3 };

  // Start from full results, add originalIdx, filter removed rows
  let rows = lastResults
    .map((r, i) => ({ ...r, _oi: i }))           // _oi = original index
    .filter(r => !removedRows.has(r._oi));

  // Apply filters
  if (chanceF) rows = rows.filter(r => r.chance === chanceF);
  if (searchQ) rows = rows.filter(r =>
    (r.college_name || "").toLowerCase().includes(searchQ) ||
    (r.branch_name  || "").toLowerCase().includes(searchQ)
  );

  // Sort
  rows.sort((a, b) => {
    if (sortKey === "chance") {
      const cd = (chanceOrder[a.chance] ?? 3) - (chanceOrder[b.chance] ?? 3);
      if (cd !== 0) return cd;
      return parseFloat(b.cutoff_percentile || 0) - parseFloat(a.cutoff_percentile || 0);
    }
    if (sortKey === "cutoff_desc") return parseFloat(b.cutoff_percentile || 0) - parseFloat(a.cutoff_percentile || 0);
    if (sortKey === "cutoff_asc")  return parseFloat(a.cutoff_percentile || 0) - parseFloat(b.cutoff_percentile || 0);
    if (sortKey === "college_name") return (a.college_name || "").localeCompare(b.college_name || "");
    if (sortKey === "college_type") return (a.college_type || "").localeCompare(b.college_type || "");
    return 0;
  });

  // Update visible count label
  const countLabel = document.getElementById("visibleCountLabel");
  if (countLabel) {
    const nonRemoved = lastResults.filter((_, i) => !removedRows.has(i)).length;
    countLabel.textContent = `${rows.length} of ${nonRemoved} colleges shown`;
  }

  const wrapper = document.getElementById("resultsTableWrapper");
  if (!wrapper) return;

  if (rows.length === 0) {
    wrapper.innerHTML = `
      <div class="empty-state" style="padding:2.5rem">
        <div class="empty-icon">😔</div>
        <h3>No results match your filters</h3>
        <p>Try clearing the search or changing the chance/sort filters above.</p>
      </div>`;
    return;
  }

  let tableHtml = `
    <table>
      <thead>
        <tr>
          <th style="width:2.5rem">#</th>
          <th>College</th>
          <th>Branch</th>
          <th>Category</th>
          <th style="white-space:nowrap">Cutoff %</th>
          <th style="white-space:nowrap">Rank</th>
          <th>Type</th>
          <th style="white-space:nowrap">Chance</th>
          <th style="width:2.5rem"></th>
        </tr>
      </thead>
      <tbody>`;

  rows.forEach((r, displayIdx) => {
    const chanceLower = (r.chance || "unknown").toLowerCase();
    tableHtml += `
      <tr class="college-row">
        <td style="text-align:center;color:var(--gray-400);font-weight:700">${displayIdx + 1}</td>
        <td>
          <div class="college-name">${escHtml(r.college_name)}</div>
          ${r.college_code ? `<div class="college-code">${escHtml(r.college_code)}</div>` : ""}
          ${r.cap_round    ? `<div class="college-code">${escHtml(r.cap_round)}</div>` : ""}
        </td>
        <td>${escHtml(r.branch_name)}</td>
        <td style="font-size:.8rem">${escHtml(r.category)}</td>
        <td style="font-weight:600;white-space:nowrap">
          ${r.cutoff_percentile ? parseFloat(r.cutoff_percentile).toFixed(2) : "—"}
        </td>
        <td style="white-space:nowrap">${r.cutoff_rank || "—"}</td>
        <td style="font-size:.8rem">${escHtml(r.college_type)}</td>
        <td><span class="badge badge-${chanceLower}">${escHtml(r.chance)}</span></td>
        <td>
          <button class="btn-remove" data-oi="${r._oi}" title="Remove from list">✕</button>
        </td>
      </tr>`;
  });

  tableHtml += `</tbody></table>`;
  wrapper.innerHTML = tableHtml;

  // Attach remove button events
  wrapper.querySelectorAll(".btn-remove").forEach(btn => {
    btn.addEventListener("click", () => {
      removedRows.add(parseInt(btn.dataset.oi));
      // Update count label and re-render table; don't rebuild whole results panel
      refreshTable();
      // Also update the top count
      const nonRemoved = lastResults.filter((_, i) => !removedRows.has(i)).length;
      const countLabel = document.getElementById("visibleCountLabel");
      if (countLabel) countLabel.textContent = `${nonRemoved} of ${lastResults.length} colleges shown`;
    });
  });
}

// ── PDF Download ──────────────────────────────────────────────────────────────

async function downloadPDF() {
  const btn = document.getElementById("pdfBtn");
  if (btn) { btn.textContent = "⏳ Generating..."; btn.disabled = true; }

  // Only send the non-removed, currently-visible rows in their sorted order
  const chanceOrder = { Safe: 0, Moderate: 1, Ambitious: 2, Unknown: 3 };
  const visibleResults = lastResults
    .map((r, i) => ({ ...r, _oi: i }))
    .filter(r => !removedRows.has(r._oi))
    .sort((a, b) =>
      (chanceOrder[a.chance] ?? 3) - (chanceOrder[b.chance] ?? 3) ||
      parseFloat(b.cutoff_percentile || 0) - parseFloat(a.cutoff_percentile || 0)
    );

  try {
    const res = await fetch(`${API}/pdf`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        results:       visibleResults,
        input_summary: lastInputSummary,
        exam_type:     EXAM_CONFIG[currentExam]?.title || currentExam,
      }),
    });

    if (!res.ok) throw new Error("PDF generation failed");

    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = "AdmissionGuru_CollegeList.pdf";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

  } catch {
    alert("PDF generation failed. Please try again.");
  } finally {
    if (btn) { btn.textContent = "⬇ Download PDF"; btn.disabled = false; }
  }
}

// ── Save List ─────────────────────────────────────────────────────────────────

async function saveList() {
  if (!AuthState.isLoggedIn()) {
    // Store current state in sessionStorage so we can restore after login
    sessionStorage.setItem("ag_pending_save", JSON.stringify({
      exam_type:     currentExam,
      input_summary: lastInputSummary,
      results:       lastResults.filter((_, i) => !removedRows.has(i)),
    }));
    window.location.href = "login.html?redirect=predict.html";
    return;
  }

  const btn = document.getElementById("saveListBtn");
  if (btn) { btn.textContent = "💾 Saving..."; btn.disabled = true; }

  const visibleResults = lastResults.filter((_, i) => !removedRows.has(i));

  try {
    const res = await AuthState.authFetch(`${API}/lists`, {
      method: "POST",
      body: JSON.stringify({
        exam_type:     currentExam,
        input_summary: lastInputSummary,
        results:       visibleResults,
      }),
    });

    if (res.ok) {
      if (btn) btn.textContent = "✅ Saved!";
      setTimeout(() => {
        if (btn) { btn.textContent = "💾 Save List"; btn.disabled = false; }
      }, 2500);
    } else {
      const d = await res.json().catch(() => ({}));
      throw new Error(d.error || "Save failed");
    }
  } catch (err) {
    alert(`Save failed: ${err.message}`);
    if (btn) { btn.textContent = "💾 Save List"; btn.disabled = false; }
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  // Check server connectivity
  checkServerHealth();
  const urlParams = new URLSearchParams(window.location.search);
  const preselect  = urlParams.get("exam");
  if (preselect && EXAM_CONFIG[preselect]) {
    selectExam(preselect);
  }

  // Exam card clicks
  document.querySelectorAll(".exam-select-card:not([disabled])").forEach(btn => {
    btn.addEventListener("click", () => {
      if (!btn.dataset.exam) return;
      selectExam(btn.dataset.exam);
    });
  });

  // Form submit
  document.getElementById("predictForm")?.addEventListener("submit", handlePredict);

  // Back button
  document.getElementById("backBtn")?.addEventListener("click", () => showStep(1));

  // Restore pending save (after login redirect)
  const pending = sessionStorage.getItem("ag_pending_save");
  if (pending && AuthState.isLoggedIn()) {
    sessionStorage.removeItem("ag_pending_save");
    try {
      const data = JSON.parse(pending);
      AuthState.authFetch(`${API}/lists`, {
        method: "POST",
        body: JSON.stringify(data),
      }).then(res => {
        if (res.ok) {
          // Brief toast notification
          const toast = document.createElement("div");
          toast.className = "alert alert-success";
          toast.style.cssText = "position:fixed;top:80px;right:1rem;z-index:9999;max-width:300px";
          toast.textContent = "✅ Your college list was saved!";
          document.body.appendChild(toast);
          setTimeout(() => toast.remove(), 4000);
        }
      });
    } catch {}
  }
});

async function selectExam(examType) {
  currentExam = examType;
  document.querySelectorAll(".exam-select-card").forEach(btn => {
    btn.classList.toggle("selected", btn.dataset.exam === examType);
  });
  showStep(2);
  await buildForm(examType);
}
