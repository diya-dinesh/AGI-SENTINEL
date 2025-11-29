const $ = (s) => document.querySelector(s);

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// Surface unexpected JS errors in the UI so they don't silently break init
window.addEventListener("error", (e) => {
  try { setStatus(`UI error: ${e.message}`, "error"); } catch { }
});

function setStatus(msg, variant = "info") {
  const el = $("#status");
  if (!msg) {
    el.className = "hidden mb-6";
    el.textContent = "";
    return;
  }

  // Enhanced status with glassmorphism and icons
  const icons = {
    info: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`,
    success: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`,
    error: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`,
    loading: `<svg class="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>`
  };

  const base = "glass mb-6 rounded-2xl px-5 py-4 text-sm font-medium shadow-lg border-2 flex items-center gap-3";
  let cls = " border-blue-200 text-blue-800";
  if (variant === "success") cls = " border-emerald-200 text-emerald-800";
  if (variant === "error") cls = " border-rose-200 text-rose-800";
  if (variant === "loading") cls = " border-indigo-200 text-indigo-800 loading";

  el.className = base + cls;
  el.innerHTML = `${icons[variant] || icons.info}<span>${msg}</span>`;
}

function updateStats(data) {
  const statsContainer = $("#stats-container");
  if (!data) {
    statsContainer.classList.add("hidden");
    return;
  }

  statsContainer.classList.remove("hidden");

  // Extract stats from response
  const signals = data.analysis?.signals?.length || 0;
  const reports = data.ingest?.stored || 0;

  // Calculate duration
  let duration = "--";
  if (data.pipeline_start && data.pipeline_end) {
    const start = new Date(data.pipeline_start);
    const end = new Date(data.pipeline_end);
    const seconds = Math.round((end - start) / 1000);
    duration = seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  }

  // Animate counter updates
  animateValue("stat-signals", 0, signals, 800);
  animateValue("stat-reports", 0, reports, 800);
  $("#stat-time").textContent = duration;
}

function animateValue(id, start, end, duration) {
  const el = $("#" + id);
  if (!el) return;

  const range = end - start;
  const increment = range / (duration / 16); // 60fps
  let current = start;

  const timer = setInterval(() => {
    current += increment;
    if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
      current = end;
      clearInterval(timer);
    }
    el.textContent = Math.round(current);
  }, 16);
}

function renderSignals(result) {
  const container = $("#signals");
  container.innerHTML = "";
  if (!result || !Array.isArray(result.signals) || result.signals.length === 0) {
    container.innerHTML = `
      <div class="text-center py-12 text-slate-400">
        <svg class="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <p class="font-medium">No signals detected</p>
        <p class="text-sm mt-1">This indicates normal safety profile</p>
      </div>
    `;
    return;
  }

  // Apply search and sort
  const q = ($("#signals-search")?.value || "").toLowerCase();
  const sort = $("#signals-sort")?.value || "count_desc";
  let items = result.signals.slice();
  if (q) items = items.filter(s => (s.reaction || "").toLowerCase().includes(q));
  const num = v => (v == null || isNaN(Number(v)) ? -Infinity : Number(v));
  const cmp = {
    count_desc: (a, b) => num(b.current_count) - num(a.current_count),
    z_desc: (a, b) => num(b.zscore) - num(a.zscore),
    rel_desc: (a, b) => num(b.relative) - num(a.relative),
    week_desc: (a, b) => String(b.week).localeCompare(String(a.week)),
    reaction_asc: (a, b) => String(a.reaction || "").localeCompare(String(b.reaction || ""))
  }[sort] || ((a, b) => 0);
  items.sort(cmp);

  container.innerHTML = `
    <div class="overflow-auto">
      <table class="min-w-full text-left text-sm">
        <thead class="text-xs uppercase text-slate-500">
          <tr>
            <th class="px-3 py-2">Reaction</th>
            <th class="px-3 py-2">Count</th>
            <th class="px-3 py-2">z-score</th>
            <th class="px-3 py-2">Relative</th>
            <th class="px-3 py-2">Week</th>
            <th class="px-3 py-2">Reason</th>
          </tr>
        </thead>
        <tbody id="signals-rows" class="divide-y divide-slate-100"></tbody>
      </table>
    </div>
  `;
  const tbody = document.getElementById("signals-rows");
  items.forEach((s, index) => {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-indigo-50 transition-colors";
    tr.style.animationDelay = `${index * 50}ms`;

    const count = Number.isFinite(s.current_count) ? s.current_count : (s.current_count ?? "?");
    const z = (s.zscore == null || isNaN(Number(s.zscore))) ? "—" : Number(s.zscore).toFixed(2);
    const rel = (s.relative == null || isNaN(Number(s.relative))) ? "—" : Number(s.relative).toFixed(2);
    const weekRaw = s.week ?? "?";
    const week = typeof weekRaw === "string" ? (weekRaw.split(" ")[0] || weekRaw) : weekRaw;

    // Color code high z-scores
    const zClass = Number(z) >= 3 ? "text-red-600 font-bold" : Number(z) >= 2 ? "text-orange-600 font-semibold" : "";

    tr.innerHTML = `
      <td class="px-3 py-3 font-semibold text-slate-900">${s.reaction || "?"}</td>
      <td class="px-3 py-3"><span class="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-100 to-purple-100 text-indigo-700 font-bold text-sm">${count}</span></td>
      <td class="px-3 py-3 ${zClass}">${z}</td>
      <td class="px-3 py-3">${rel}</td>
      <td class="px-3 py-3 text-slate-600 text-xs">${week}</td>
      <td class="px-3 py-3">${s.reason ? `<span class="signal-badge inline-flex items-center rounded-full bg-gradient-to-r from-red-100 to-pink-100 px-3 py-1 text-xs font-semibold text-red-700">${s.reason}</span>` : ""}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderReport(resp) {
  const metaEl = $("#report-meta");
  const reportEl = $("#report");
  metaEl.textContent = resp?.filename ? `File: ${resp.filename}` : "";
  const md = (resp?.content || "").trim();
  if (!md) {
    reportEl.innerHTML = `<div class="text-slate-500 text-sm">No report found.</div>`;
    return;
  }
  // Persist original for export
  window.lastReportMd = md;
  window.lastReportFilename = resp?.filename || 'report.md';
  const cleanedMd = cleanReportMd(md);
  console.log('[renderReport] ========== RENDERING REPORT ==========');
  console.log('[renderReport] Raw markdown length:', md.length);

  try {
    const parsed = parseReportMarkdown(cleanedMd);
    console.log('[renderReport] Parsed data:', JSON.stringify(parsed, null, 2));

    window.lastParsedReport = parsed;

    console.log('[renderReport] Calling renderReportCards...');
    const cardsHtml = renderReportCards(parsed);
    console.log('[renderReport] ✓ Generated HTML length:', cardsHtml.length);
    console.log('[renderReport] First 500 chars:', cardsHtml.substring(0, 500));

    reportEl.innerHTML = cardsHtml;
    console.log('[renderReport] ✓ HTML inserted into DOM');

    // Initialize accordion
    initializeReportAccordion();

    wireReportActions();
    console.log('[renderReport] ✓ Actions wired');
    console.log('[renderReport] ========== REPORT RENDERED SUCCESSFULLY ==========');
  } catch (error) {
    console.error('[renderReport] ✗✗✗ ERROR ✗✗✗');
    console.error('[renderReport] Error message:', error.message);
    console.error('[renderReport] Error stack:', error.stack);
    console.error('[renderReport] Falling back to plain markdown');
    reportEl.innerHTML = `
      <div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
        <p class="text-red-800 font-semibold">⚠️ Report rendering error</p>
        <p class="text-red-600 text-sm mt-1">${error.message}</p>
      </div>
      ${marked.parse(cleanedMd)}
    `;
    wireReportActions(true);
  }
}

function stripSignalsBlocks(text) {
  // Remove header tokens wherever they appear
  let out = text.replace(/Reaction[\sA-Za-z]*z-?score[\sA-Za-z]*Relative[\sA-Za-z]*Week[\sA-Za-z]*Reason/gi, '');
  const lines = out.split(/\r?\n/);
  const kept = [];
  for (let i = 0; i < lines.length; i++) {
    const L = lines[i].trim();
    if (!L) { kept.push(lines[i]); continue; }

    // Drop obvious header-like single line again (safety)
    if (/Reaction/i.test(L) && /Relative/i.test(L) && /Reason/i.test(L)) {
      // skip until a blank or heading-like line
      while (i + 1 < lines.length && lines[i + 1].trim() && !/^##\s/.test(lines[i + 1]) && !/^\*\*.+\*\*:/.test(lines[i + 1])) i++;
      continue;
    }

    // Detect a signals row block: a wordy reaction line followed by several numeric/date/keyword lines
    const isWordy = /^[A-Za-z].{2,}$/.test(L) && !/:$/.test(L) && !/^\*\*/.test(L);
    if (isWordy) {
      let j = i + 1, score = 0, total = 0;
      while (j < lines.length && total < 6) {
        const t = lines[j].trim();
        if (!t) break;
        if (/^\d{1,4}(?:\.\d+)?$/.test(t) || /^\d{4}-\d{2}-\d{2}$/.test(t) || /^(zscore\+relative|relative|zscore)$/i.test(t)) {
          score++;
        }
        total++;
        j++;
      }
      if (score >= 2 && total >= 3) { i = j - 1; continue; }
    }
    kept.push(lines[i]);
  }
  return kept.join('\n').replace(/\n{3,}/g, '\n\n');
}

function cleanReportMd(md) {
  let out = md;
  // 1) Drop the 'Detected Signals' section if present by heading
  out = out.replace(/(^|\n)##\s*Detected Signals[\s\S]*?(?=\n##\s|$)/mi, '$1');

  // 2) Also drop any inline signals table/list block using heuristics
  out = stripSignalsBlocks(out);
  return out;
}

function parseReportMarkdown(md) {
  // Remove the 'Detected Signals' section entirely to avoid duplication in the report cards
  const cleaned = cleanReportMd(md);
  const lines = cleaned.split(/\r?\n/);
  const out = { title: "", summary: {}, signals: [], llm: "" };
  let section = "";
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.startsWith("# ADSIO Report")) {
      out.title = line.replace(/^#\s*/, "");
      continue;
    }
    if (line.startsWith("## ")) {
      const h = line.slice(3).toLowerCase();
      if (h.startsWith("summary")) section = "summary";
      else if (h.startsWith("detected signals")) section = "signals";
      else if (h.startsWith("llm analysis")) section = "llm";
      else section = "";
      continue;
    }
    if (!section) continue;

    if (section === "summary") {
      const m = line.match(/^[-*]\s*(.+?):\s*(.+)$/);
      if (m) {
        const key = m[1].trim().toLowerCase();
        const val = m[2].trim();
        out.summary[key] = val;
      }
      continue;
    }

    if (section === "signals") {
      const m = line.match(/^[-*]\s*(.+?)\s+—\s+count=(\d+),\s*z=([^,]+),\s*rel=([^,]+),\s*week=(.+)$/);
      if (m) {
        const reaction = m[1].trim();
        const count = parseInt(m[2], 10);
        const z = parseFloat(m[3]);
        const rel = parseFloat(m[4]);
        const weekRaw = m[5].trim();
        const week = weekRaw.split(" ")[0];
        out.signals.push({ reaction, current_count: count, zscore: isFinite(z) ? z : null, relative: isFinite(rel) ? rel : null, week });
      }
      continue;
    }

    if (section === "llm") {
      out.llm += (out.llm ? "\n" : "") + line;
      continue;
    }
  }
  return out;
}

function mdInline(s) {
  if (s == null) return '';
  // Basic HTML escape
  const esc = String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  // Convert **bold** to <strong>bold</strong>
  const bold = esc.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  // Convert *italic* to <em>italic</em>
  const ital = bold.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  return ital;
}

function mdParagraphs(text) {
  if (!text) return [];
  let t = String(text).trim();

  // Strip leading/trailing ** more aggressively (including with whitespace)
  t = t.replace(/^\*\*\s*/g, '').replace(/\s*\*\*$/g, '');

  // Also strip ** from middle if they wrap entire text
  if (t.startsWith('**') && t.endsWith('**')) {
    t = t.slice(2, -2).trim();
  }

  const cleaned = t;

  // Prefer blank-line paragraphs; fall back to sentence-based split
  let blocks = cleaned.split(/\n{2,}/).filter(Boolean);
  if (blocks.length <= 1) {
    blocks = cleaned.split(/(?<=[.!?])\s+(?=[A-Z0-9])/).filter(Boolean);
  }
  return blocks.map(b => mdInline(b.trim())).filter(Boolean);
}

// REPLACEMENT: improved Report Cards UI generator with TABS
function renderReportCards(data) {
  const summary = data.summary || {};
  const toInt = (v) => {
    const n = parseInt(String(v).replace(/[^0-9.-]/g, ''), 10);
    return Number.isFinite(n) ? n : null;
  };
  const fetched = toInt(summary['fetched']);
  const stored = toInt(summary['stored']);
  const sigs = toInt(summary['signals found']);

  // Parse LLM analysis into sections
  const llmSections = parseLlmSectionsRobust(data.llm || "");

  // Icon mapping for each section
  const sectionIcons = {
    'Summary': `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>`,
    'Key Evidence': `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" /></svg>`,
    'Possible Causes': `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>`,
    'Risk Assessment': `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>`,
    'Recommended Next Steps': `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" /></svg>`,
    'Confidence Score': `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>`
  };

  // Build accordion sections
  const accordionItems = llmSections.map((section, index) => {
    if (!section || !section.title) return '';

    const sectionId = `accordion-${index}`;
    const isFirst = index === 0;
    const icon = sectionIcons[section.title] || sectionIcons['Summary'];

    // Build content
    let content = '';
    if (section.items && section.items.length) {
      if (section.title === 'Recommended Next Steps') {
        content = `<ol class="space-y-3">${section.items.map((it, i) => `
          <li class="flex gap-3 p-3 rounded-lg bg-slate-50 hover:bg-slate-100 transition-colors">
            <span class="flex-shrink-0 w-7 h-7 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 text-white flex items-center justify-center text-sm font-bold shadow-md">${i + 1}</span>
            <span class="text-sm text-slate-700 leading-relaxed">${mdInline(it)}</span>
          </li>
        `).join('')}</ol>`;
      } else {
        content = `<ul class="space-y-2">${section.items.map(it => `
          <li class="flex gap-2 text-sm text-slate-700 p-2 rounded hover:bg-slate-50 transition-colors">
            <span class="text-indigo-500 mt-1 font-bold">•</span>
            <span class="leading-relaxed">${mdInline(it)}</span>
          </li>
        `).join('')}</ul>`;
      }
    } else if (section.text) {
      // Enhanced text rendering with automatic bullet points for sentences
      let text = section.text.trim();

      // Strip leading/trailing ** aggressively
      text = text.replace(/^\*\*\s*/g, '').replace(/\s*\*\*$/g, '');
      if (text.startsWith('**') && text.endsWith('**')) {
        text = text.slice(2, -2).trim();
      }

      // Check if text contains multiple sentences
      const sentences = text.split(/(?<=[.!?])\s+(?=[A-Z])/).filter(Boolean);

      if (sentences.length > 1 && section.title !== 'Summary') {
        // Render as bullet points for multi-sentence sections (except Summary)
        content = `
          <ul class="space-y-3">
            ${sentences.map(sentence => {
          // Strip ** from individual sentences too
          const clean = sentence.trim().replace(/^\*\*\s*/, '').replace(/\s*\*\*$/, '');
          return `
                <li class="flex gap-3 p-3 rounded-lg bg-gradient-to-r from-slate-50 to-white hover:from-slate-100 hover:to-slate-50 transition-all duration-200 border-l-3 border-indigo-200">
                  <span class="text-indigo-500 mt-1 font-bold text-lg">•</span>
                  <span class="text-sm text-slate-700 leading-relaxed">${mdInline(clean)}</span>
                </li>
              `;
        }).join('')}
          </ul>
        `;
      } else {
        // Render as paragraph for Summary or single-sentence content (reduced spacing)
        const paragraphs = mdParagraphs(text);
        content = paragraphs.map(p => `
          <p class="text-sm text-slate-700 leading-relaxed mb-2 p-3 rounded-lg bg-gradient-to-br from-slate-50 to-white border border-slate-100">
            ${p}
          </p>
        `).join('');
      }
    } else {
      content = `<p class="text-sm text-slate-400 italic">No content available</p>`;
    }

    // Add confidence bar if present
    if (typeof section.confidence === 'number') {
      content += `
        <div class="mt-6 pt-4 border-t border-slate-200">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-semibold text-slate-600 uppercase tracking-wide">Confidence Level</span>
            <span class="text-lg font-bold text-indigo-600">${section.confidence}%</span>
          </div>
          <div class="w-full h-3 rounded-full bg-slate-100 overflow-hidden shadow-inner">
            <div class="h-full bg-gradient-to-r from-indigo-500 to-purple-600 transition-all duration-500 shadow-sm" style="width:${Math.max(0, Math.min(100, section.confidence))}%"></div>
          </div>
        </div>
      `;
    }

    return `
      <div class="accordion-item border-b border-slate-200 last:border-b-0">
        <button class="accordion-header w-full flex items-center justify-between p-4 hover:bg-slate-50 transition-colors ${isFirst ? 'active' : ''}" data-target="${sectionId}">
          <div class="flex items-center gap-3">
            <div class="text-indigo-600">${icon}</div>
            <h3 class="text-base font-semibold text-slate-900">${section.title}</h3>
          </div>
          <svg class="accordion-chevron w-5 h-5 text-slate-400 transition-transform duration-200 ${isFirst ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        <div class="accordion-content ${isFirst ? 'active' : ''}" id="${sectionId}">
          <div class="p-6 pt-2 bg-slate-50">
            ${content}
          </div>
        </div>
      </div>
    `;
  }).join('');

  const accordionHtml = accordionItems ? `
    <div class="bg-white rounded-xl border border-slate-200 shadow-lg overflow-hidden">
      ${accordionItems}
    </div>
  ` : `
    <div class="text-center py-12 text-slate-400 bg-white rounded-xl border border-slate-200">
      <svg class="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      <p class="font-medium">No LLM analysis available</p>
      <p class="text-sm mt-1">Enable Gemini to generate AI-powered insights</p>
    </div>
  `;

  // Final layout
  return `
    <div class="space-y-5">
      <!-- Report Header -->
      <div class="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl p-6 text-white shadow-lg">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-2xl font-bold">${data.title || "Safety Analysis Report"}</h2>
            <p class="text-indigo-100 text-sm mt-1">AI-Powered Pharmacovigilance Intelligence</p>
          </div>
          <div class="flex gap-2">
            <button id="btn-export-md" class="px-4 py-2 rounded-lg bg-white/20 hover:bg-white/30 backdrop-blur text-white text-sm font-medium transition-all">
              <svg class="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
              Export MD
            </button>
            <button id="btn-export-pdf" class="px-4 py-2 rounded-lg bg-white/20 hover:bg-white/30 backdrop-blur text-white text-sm font-medium transition-all">
              <svg class="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>
              Export PDF
            </button>
          </div>
        </div>
      </div>

      <!-- Summary Stats -->
      <div class="grid grid-cols-3 gap-4">
        <div class="bg-white rounded-xl p-5 border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide">Reports Fetched</p>
              <p class="text-3xl font-black text-indigo-600 mt-2">${fetched ?? '—'}</p>
            </div>
            <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-100 to-purple-100 flex items-center justify-center">
              <svg class="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
            </div>
          </div>
        </div>
        
        <div class="bg-white rounded-xl p-5 border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide">Reports Stored</p>
              <p class="text-3xl font-black text-blue-600 mt-2">${stored ?? '—'}</p>
            </div>
            <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-100 to-cyan-100 flex items-center justify-center">
              <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" /></svg>
            </div>
          </div>
        </div>
        
        <div class="bg-white rounded-xl p-5 border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide">Signals Detected</p>
              <p class="text-3xl font-black text-red-600 mt-2">${sigs ?? '—'}</p>
            </div>
            <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-red-100 to-pink-100 flex items-center justify-center">
              <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
            </div>
          </div>
        </div>
      </div>

      <!-- Accordion Analysis -->
      ${accordionHtml}
    </div>
    
    <style>
      .accordion-content {
        max-height: 0;
        overflow: hidden;
        transition: max-height 0.3s ease-out;
      }
      .accordion-content.active {
        max-height: 2000px;
        transition: max-height 0.5s ease-in;
      }
      .accordion-header.active {
        background-color: #f8fafc;
      }
      .accordion-chevron {
        transition: transform 0.2s ease;
      }
    </style>
  `;
}

// Initialize accordion after report is rendered
function initializeReportAccordion() {
  console.log('[initializeReportAccordion] Setting up accordion event listeners...');
  const accordionHeaders = document.querySelectorAll('.accordion-header');
  console.log('[initializeReportAccordion] Found', accordionHeaders.length, 'accordion items');

  accordionHeaders.forEach(header => {
    header.addEventListener('click', () => {
      const targetId = header.dataset.target;
      const content = document.getElementById(targetId);
      const chevron = header.querySelector('.accordion-chevron');

      console.log('[initializeReportAccordion] Accordion clicked:', targetId);

      // Toggle active state
      const isActive = content.classList.contains('active');

      if (isActive) {
        // Close this section
        content.classList.remove('active');
        header.classList.remove('active');
        chevron.classList.remove('rotate-180');
      } else {
        // Open this section
        content.classList.add('active');
        header.classList.add('active');
        chevron.classList.add('rotate-180');
      }

      console.log('[initializeReportAccordion] Toggled:', targetId, isActive ? 'closed' : 'opened');
    });
  });

  console.log('[initializeReportAccordion] Accordion initialization complete');
}

function parseLlmSections(text) {
  // Normalize inline bold headings appearing in the same paragraph by forcing line breaks
  const known = ['Summary', 'Key Evidence', 'Possible Causes', 'Risk Assessment', 'Recommended Next Steps', 'Confidence Score'];
  let normalized = String(text || '');
  known.forEach(h => {
    // Escape heading text for use in RegExp
    const esc = h.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

    // 1) If a heading appears with trailing content on the same line, split it into
    //    a heading line and a new body line preserving the trailing content.
    //    Bold form: **Heading:** some text -> \n**Heading:**\nsome text\n
    const boldWithTail = new RegExp("\\*\\*" + esc + "\\*\\*:?\\s*([^\\n]+)", 'gi');
    normalized = normalized.replace(boldWithTail, (_m, tail) => "\n**" + h + ":**\n" + tail.trim() + "\n");

    //    Plain form: Heading: some text -> \n**Heading:**\nsome text\n
    const plainWithTail = new RegExp("(?:(?:^)|[\\s\\u00A0])" + esc + "\\s*:\\s*([^\\n]+)", 'gi');
    normalized = normalized.replace(plainWithTail, (_m, tail) => "\n**" + h + ":**\n" + tail.trim() + "\n");

    // 2) Normalize standalone headings anywhere (inline or standalone) with no tail
    const boldOnly = new RegExp("\\n?\\s*\\*\\*" + esc + "\\*\\*:?\\s*", 'gi');
    normalized = normalized.replace(boldOnly, "\n**" + h + ":**\n");
  });

  const lines = normalized.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
  const sections = [];
  let current = null;
  const push = () => { if (current) { sections.push(current); current = null; } };

  const headingRe = /^\*\*(.+?)\*\*:?\s*$/; // **Heading** or **Heading:**
  for (const raw of lines) {
    // Drop leading non-word symbols (handles emoji/bullets without Unicode props)
    const line = raw.replace(/^[^\w*]+/, '').trim();
    const hm = line.match(headingRe);
    if (hm) {
      push();
      const title = hm[1].replace(/^Intelligence Note: /i, '').trim();
      current = { title, items: [], text: '' };
      continue;
    }
    // bullet item like '- foo' or numbered '1. bar'
    if (/^[-*]\s+/.test(line)) {
      if (!current) current = { title: 'Notes', items: [], text: '' };
      current.items.push(line.replace(/^[-*]\s+/, ''));
      continue;
    }
    if (/^\d+\.\s+/.test(line)) {
      if (!current) current = { title: 'Recommended Next Steps', items: [], text: '' };
      current.items.push(line.replace(/^\d+\.\s+/, ''));
      continue;
    }
    // plain paragraph
    if (!current) current = { title: 'Notes', items: [], text: '' };
    current.text += (current.text ? ' ' : '') + line;
  }
  push();

  // Attempt to parse confidence score like "Confidence Score: 75" or "75%"
  sections.forEach(s => {
    if (s.title.toLowerCase().includes('confidence')) {
      const m = (s.text || '').match(/(\d{1,3})(?:\s*%|\b)/);
      if (m) {
        const n = Math.max(0, Math.min(100, parseInt(m[1], 10)));
        s.confidence = n;
      }
    }
  });

  // Reorder to preferred sequence when present
  const order = ['Summary', 'Key Evidence', 'Possible Causes', 'Risk Assessment', 'Recommended Next Steps', 'Confidence Score'];
  sections.sort((a, b) => order.indexOf(a.title) - order.indexOf(b.title));
  return sections;
}

function parseLlmSectionsRobust(text) {
  if (!text || typeof text !== 'string') return [];

  const src = text.trim();
  const labels = ['Summary', 'Key Evidence', 'Possible Causes', 'Risk Assessment', 'Recommended Next Steps', 'Confidence Score'];

  if (!src) return [];

  // Build a regex that matches section labels at the start of a line or after newline
  // Handles formats like:
  // "Summary: text here"
  // "**Summary:** text here"
  // "Summary:\ntext here"
  const sections = [];

  // Split by section headers
  const pattern = new RegExp(`(${labels.join('|')}):`, 'gi');
  const parts = src.split(pattern);

  // parts will be: [before, label1, content1, label2, content2, ...]
  for (let i = 1; i < parts.length; i += 2) {
    const label = parts[i].trim();
    const content = parts[i + 1] ? parts[i + 1].trim() : '';

    if (!content) continue;

    // Parse content into items or text
    const lines = content.split(/\n/).map(l => l.trim()).filter(Boolean);
    const items = [];
    const textLines = [];

    for (const line of lines) {
      // Check if it's a list item (starts with number, dash, or bullet)
      if (/^(\d+\.|[-•*])\s+/.test(line)) {
        items.push(line.replace(/^(\d+\.|[-•*])\s+/, '').trim());
      } else if (!labels.some(l => line.startsWith(l + ':'))) {
        // Not a new section header, add to text
        textLines.push(line);
      } else {
        // Hit a new section, stop
        break;
      }
    }

    // Extract confidence score if this is the Confidence Score section
    let confidence = null;
    if (label.toLowerCase().includes('confidence')) {
      const scoreMatch = content.match(/(\d+)(?:\/100)?/);
      if (scoreMatch) {
        confidence = parseInt(scoreMatch[1], 10);
      }
    }

    sections.push({
      title: label,
      items: items.length > 0 ? items : undefined,
      text: textLines.length > 0 ? textLines.join(' ') : content,
      confidence: confidence
    });
  }

  return sections.length > 0 ? sections : [];
}

function downloadBlob(filename, data, mime) {
  const blob = new Blob([data], { type: mime });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function toCsvRow(cells) {
  return cells.map(c => {
    if (c == null) return '';
    const s = String(c).replace(/"/g, '""');
    return /[",\n]/.test(s) ? `"${s}"` : s;
  }).join(',');
}

function exportSignalsCsv() {
  const rows = [];
  const header = ['reaction', 'current_count', 'zscore', 'relative', 'week', 'reason'];
  rows.push(toCsvRow(header));
  const src = (window.lastSignals && Array.isArray(window.lastSignals.signals)) ? window.lastSignals.signals
    : (window.lastParsedReport && Array.isArray(window.lastParsedReport.signals)) ? window.lastParsedReport.signals
      : [];
  src.forEach(s => {
    rows.push(toCsvRow([
      s.reaction ?? '',
      s.current_count ?? '',
      (s.zscore != null && isFinite(+s.zscore)) ? Number(s.zscore).toFixed(2) : '',
      (s.relative != null && isFinite(+s.relative)) ? Number(s.relative).toFixed(2) : '',
      s.week ?? '',
      s.reason ?? ''
    ]));
  });
  const csv = rows.join('\n');
  const base = (window.lastReportFilename || 'report').replace(/\.[^.]+$/, '');
  downloadBlob(`${base}_signals.csv`, csv, 'text/csv;charset=utf-8');
}

function exportReportMd() {
  const md = window.lastReportMd || '';
  const name = window.lastReportFilename || 'report.md';
  downloadBlob(name, md, 'text/markdown;charset=utf-8');
}

function exportReportPdf() {
  const md = window.lastReportMd || '';
  const html = `<!doctype html><html><head><meta charset="utf-8" />
    <title>Report</title>
    <style>body{font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI; margin:24px; color:#0f172a}
      h1{font-size:20px;margin:0 0 8px;font-weight:700}
      h2{font-size:16px;margin:16px 0 8px;font-weight:600}
      h3{font-size:14px;margin:12px 0 6px;font-weight:600}
      p,li{font-size:12px; line-height:1.5}
      table{border-collapse:collapse;width:100%} td,th{border:1px solid #e2e8f0;padding:6px}
    </style></head><body>
    ${marked.parse(md)}
  </body></html>`;
  const printWin = window.open('', '_blank');
  if (!printWin) return alert('Popup blocked. Please allow popups to export PDF.');
  printWin.document.open();
  printWin.document.write(html);
  printWin.document.close();
  printWin.focus();
  // Give browser a tick to render before printing
  setTimeout(() => { printWin.print(); printWin.close(); }, 300);
}

function wireReportActions(isFallback = false) {
  document.getElementById('btn-export-md')?.addEventListener('click', exportReportMd);
  document.getElementById('btn-export-pdf')?.addEventListener('click', exportReportPdf);
  document.getElementById('btn-export-csv')?.addEventListener('click', exportSignalsCsv);
}

function openCompareDrawer() {
  $('#compare-overlay').classList.remove('hidden');
  $('#compare-drawer').classList.remove('hidden');
}
function closeCompareDrawer() {
  $('#compare-overlay').classList.add('hidden');
  $('#compare-drawer').classList.add('hidden');
}

function renderCompare(drugA, sigA, drugB, sigB) {
  const byReaction = (arr) => {
    const m = new Map();
    arr.forEach(s => { m.set((s.reaction || '').toLowerCase(), s); });
    return m;
  };
  const A = byReaction(sigA || []);
  const B = byReaction(sigB || []);
  const shared = [];
  const uniqueA = [];
  const uniqueB = [];
  A.forEach((v, k) => {
    if (B.has(k)) shared.push([v, B.get(k)]);
    else uniqueA.push(v);
  });
  B.forEach((v, k) => { if (!A.has(k)) uniqueB.push(v); });

  const rowShared = shared.map(([a, b]) => `
    <tr>
      <td class="px-3 py-2">${a.reaction}</td>
      <td class="px-3 py-2 text-right">${a.current_count ?? ''}</td>
      <td class="px-3 py-2 text-right">${isFinite(+a.zscore) ? (+a.zscore).toFixed(2) : ''}</td>
      <td class="px-3 py-2 text-right">${isFinite(+a.relative) ? (+a.relative).toFixed(2) : ''}</td>
      <td class="px-3 py-2 text-right">${b.current_count ?? ''}</td>
      <td class="px-3 py-2 text-right">${isFinite(+b.zscore) ? (+b.zscore).toFixed(2) : ''}</td>
      <td class="px-3 py-2 text-right">${isFinite(+b.relative) ? (+b.relative).toFixed(2) : ''}</td>
    </tr>`).join('');
  const rowUniq = (arr) => arr.map(s => `
    <tr>
      <td class="px-3 py-2">${s.reaction}</td>
      <td class="px-3 py-2 text-right">${s.current_count ?? ''}</td>
      <td class="px-3 py-2 text-right">${isFinite(+s.zscore) ? (+s.zscore).toFixed(2) : ''}</td>
      <td class="px-3 py-2 text-right">${isFinite(+s.relative) ? (+s.relative).toFixed(2) : ''}</td>
    </tr>`).join('');

  // Simple clusters: group by first token (e.g., body system keyword if present)
  const clusterKey = (name) => (name || '').split(' ')[0].toLowerCase();
  const clusters = new Map();
  [...(sigA || []), ...(sigB || [])].forEach(s => {
    const key = clusterKey(s.reaction);
    if (!key) return;
    if (!clusters.has(key)) clusters.set(key, []);
    clusters.get(key).push(s);
  });
  const clusterHtml = [...clusters.entries()].filter(([k, v]) => v.length > 1).map(([k, v]) => `
    <div class="rounded border p-2"><div class="font-semibold mb-1">${k}</div>
      <ul class="list-disc pl-5 text-sm">${v.map(s => `<li>${s.reaction} (${s.current_count ?? '?'}; z=${isFinite(+s.zscore) ? (+s.zscore).toFixed(1) : '—'})</li>`).join('')}</ul>
    </div>
  `).join('');

  $('#compare-content').innerHTML = `
    <div class="space-y-4">
      <div>
        <div class="font-semibold mb-2">Shared signals</div>
        <div class="overflow-auto">
          <table class="min-w-full text-left text-sm">
            <thead class="text-xs uppercase text-slate-500">
              <tr>
                <th class="px-3 py-2">Reaction</th>
                <th class="px-3 py-2 text-right">${drugA} Count</th>
                <th class="px-3 py-2 text-right">${drugA} z</th>
                <th class="px-3 py-2 text-right">${drugA} Rel</th>
                <th class="px-3 py-2 text-right">${drugB} Count</th>
                <th class="px-3 py-2 text-right">${drugB} z</th>
                <th class="px-3 py-2 text-right">${drugB} Rel</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">${rowShared || '<tr><td colspan="7" class="px-3 py-6 text-center text-slate-500">None</td></tr>'}</tbody>
          </table>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <div class="font-semibold mb-2">Unique to ${drugA}</div>
          <div class="overflow-auto"><table class="min-w-full text-left text-sm"><tbody class="divide-y divide-slate-100">${rowUniq(uniqueA) || '<tr><td class="px-3 py-6 text-center text-slate-500">None</td></tr>'}</tbody></table></div>
        </div>
        <div>
          <div class="font-semibold mb-2">Unique to ${drugB}</div>
          <div class="overflow-auto"><table class="min-w-full text-left text-sm"><tbody class="divide-y divide-slate-100">${rowUniq(uniqueB) || '<tr><td class="px-3 py-6 text-center text-slate-500">None</td></tr>'}</tbody></table></div>
        </div>
      </div>

      <div>
        <div class="font-semibold mb-2">Simple clusters</div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-2">${clusterHtml || '<div class="text-slate-500">No clusters found.</div>'}</div>
      </div>
    </div>`;
}

async function handleCompareClick() {
  const drugA = $('#drug-input').value.trim();
  const drugB = $('#compare-input').value.trim();
  if (!drugA || !drugB) return setStatus('Enter both drugs to compare', 'warning');
  try {
    setStatus('Comparing...', 'info');
    // Fetch signals for both
    const [a, b] = await Promise.all([
      api(`/api/signals?drug=${encodeURIComponent(drugA)}`),
      api(`/api/signals?drug=${encodeURIComponent(drugB)}`)
    ]);
    openCompareDrawer();
    renderCompare(drugA, a.signals || [], drugB, b.signals || []);
    $('#compare-close').onclick = closeCompareDrawer;
    $('#compare-overlay').onclick = closeCompareDrawer;
    setStatus('Comparison ready', 'success');
  } catch (e) {
    console.error(e);
    setStatus('Compare failed', 'error');
  }
}

async function loadSignals(drug) {
  try {
    const result = await api(`/api/signals?drug=${encodeURIComponent(drug)}`);
    window.lastSignals = result;
    renderSignals(result);

    // Update the signals count in the stats card
    const signalsCount = result?.signals?.length || 0;
    const statSignalsEl = $("#stat-signals");
    if (statSignalsEl) {
      animateValue("stat-signals", parseInt(statSignalsEl.textContent) || 0, signalsCount, 800);
    }
  } catch (e) {
    console.error(e);
    $("#signals").innerHTML = `<div class="text-slate-500 text-sm">No signals for ${drug}.</div>`;
  }
}

async function loadLatestReport(drug) {
  try {
    const resp = await api(`/api/reports/latest?drug=${encodeURIComponent(drug)}`);
    renderReport(resp);
  } catch (e) {
    $("#report").innerHTML = `<div class="text-slate-500 text-sm">No report for ${drug} yet.</div>`;
    $("#report-meta").textContent = "";
  }
}

async function renderWeeklyChart(drug) {
  const canvas = document.getElementById('weeklyChart');
  if (!canvas || !window.Chart) return;
  try {
    const dbg = await api(`/api/debug/weekly_counts?drug=${encodeURIComponent(drug)}`);
    const rows = dbg.counts || [];
    if (rows.length === 0) return;
    // Gather reactions totals and weeks
    const totals = {};
    const weeksSet = new Set();
    rows.forEach(r => {
      totals[r.reaction] = (totals[r.reaction] || 0) + (r.count || 0);
      weeksSet.add(r.week);
    });
    const weeks = Array.from(weeksSet).sort();
    // Pick top 5 reactions by total
    const topReactions = Object.entries(totals).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([name]) => name);

    // Build dataset per reaction
    const colors = ['#4f46e5', '#06b6d4', '#f59e0b', '#10b981', '#ef4444'];
    const datasets = topReactions.map((rx, i) => {
      const series = weeks.map(w => {
        const row = rows.find(r => r.week === w && r.reaction === rx);
        return row ? row.count : 0;
      });
      return {
        label: rx,
        data: series,
        borderColor: colors[i % colors.length],
        backgroundColor: colors[i % colors.length] + '33',
        tension: 0.25
      };
    });

    // Destroy prior chart if exists
    if (window._weeklyChart) {
      window._weeklyChart.destroy();
    }
    window._weeklyChart = new Chart(canvas.getContext('2d'), {
      type: 'line',
      data: { labels: weeks, datasets },
      options: {
        responsive: true,
        plugins: { legend: { position: 'bottom' } },
        scales: { x: { ticks: { autoSkip: true, maxTicksLimit: 8 } }, y: { beginAtZero: true, title: { display: true, text: 'Count' } } }
      }
    });
  } catch (e) {
    console.warn('weekly chart failed', e);
  }
}

async function runPipeline(drug, limit) {
  console.log('[run] start', { drug, limit });
  setStatus("🚀 Running analysis pipeline...", "loading");

  // Prevent double submit
  const runBtn = document.querySelector("#run-btn");
  const refreshBtn = document.querySelector("#refresh-btn");
  if (runBtn) {
    runBtn.disabled = true;
    runBtn.innerHTML = `
      <span class="flex items-center gap-2">
        <svg class="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Analyzing...
      </span>
    `;
  }
  if (refreshBtn) refreshBtn.disabled = true;

  try {
    const body = JSON.stringify({ drug, limit: Number(limit) || 100 });
    console.log('[run] POST /api/run', body);

    const result = await api("/api/run", { method: "POST", body });
    console.log('[run] ok', result);

    // Extract data from new response format
    const trace = result.data || result;

    // Update stats display
    updateStats(trace);

    setStatus(`✅ Analysis complete! Fetched ${trace?.ingest?.fetched ?? "?"} reports, stored ${trace?.ingest?.stored ?? "?"}`, "success");

    await loadSignals(drug);
    await loadLatestReport(drug);

    // Auto-clear success message after 5 seconds
    setTimeout(() => setStatus(""), 5000);

  } catch (e) {
    console.error('[run] failed', e);
    setStatus(`❌ Pipeline failed: ${e.message || "Unknown error"}`, "error");
    updateStats(null); // Hide stats on error
  } finally {
    if (runBtn) {
      runBtn.disabled = false;
      runBtn.innerHTML = `
        <span class="flex items-center gap-2">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Run Analysis
        </span>
      `;
    }
    if (refreshBtn) refreshBtn.disabled = false;
  }
}

// Expose for manual triggering from console
window.runPipeline = runPipeline;

// Global click handlers as a final fallback (used by inline onclick attrs)
window.handleRunClick = async function () {
  const drug = document.querySelector('#drug-input')?.value?.trim();
  const limit = document.querySelector('#limit-input')?.value;
  if (!drug) return setStatus('Enter a drug name', 'error');
  console.log('[onclick] run');
  await runPipeline(drug, limit);
};
window.handleRefreshClick = async function () {
  const drug = document.querySelector('#drug-input')?.value?.trim();
  if (!drug) return setStatus('Enter a drug name', 'error');
  console.log('[onclick] refresh');
  await loadSignals(drug);
  await loadLatestReport(drug);
};

$("#run-btn").addEventListener("click", async () => {
  const drug = $("#drug-input").value.trim();
  const limit = $("#limit-input").value;
  if (!drug) return;
  localStorage.setItem("agi_last_drug", drug);
  await runPipeline(drug, limit);
});

$("#refresh-btn").addEventListener("click", async () => {
  const drug = $("#drug-input").value.trim();
  if (!drug) return;
  localStorage.setItem("agi_last_drug", drug);
  setStatus("Refreshing...", "info");
  await loadSignals(drug);
  await loadLatestReport(drug);
  setStatus("");
});

function bindControls() {
  try {
    const runBtn = document.querySelector('#run-btn');
    if (runBtn && !runBtn.dataset.bound) {
      runBtn.addEventListener('click', async () => {
        console.log('[bind] run clicked');
        const drug = document.querySelector('#drug-input')?.value?.trim();
        const limit = document.querySelector('#limit-input')?.value;
        if (!drug) return setStatus('Enter a drug name', 'error');
        await runPipeline(drug, limit);
      });
      runBtn.dataset.bound = '1';
      console.log('[bind] run attached');
    }
    const refreshBtn = document.querySelector('#refresh-btn');
    if (refreshBtn && !refreshBtn.dataset.bound) {
      refreshBtn.addEventListener('click', async () => {
        console.log('[bind] refresh clicked');
        const drug = document.querySelector('#drug-input')?.value?.trim();
        if (!drug) return setStatus('Enter a drug name', 'error');
        await loadSignals(drug);
        await loadLatestReport(drug);
      });
      refreshBtn.dataset.bound = '1';
      console.log('[bind] refresh attached');
    }
    // Enter key to run
    const inputs = ['#drug-input', '#limit-input'].map(s => document.querySelector(s)).filter(Boolean);
    inputs.forEach(inp => {
      if (!inp.dataset.boundEnter) {
        inp.addEventListener('keydown', (e) => {
          if (e.key === 'Enter') {
            document.querySelector('#run-btn')?.click();
          }
        });
        inp.dataset.boundEnter = '1';
      }
    });
  } catch (e) {
    console.error('bindControls failed', e);
    try { setStatus('Failed to bind UI controls', 'error'); } catch { }
  }
}

// Attach binders on several lifecycle events
window.addEventListener('DOMContentLoaded', bindControls);
window.addEventListener('load', bindControls);
window.addEventListener('pageshow', bindControls);

// Initial load
window.addEventListener("DOMContentLoaded", async () => {
  const saved = localStorage.getItem("agi_last_drug");
  if (saved) $("#drug-input").value = saved;
  const drug = $("#drug-input").value.trim();

  // Wire filters
  $("#signals-search")?.addEventListener("input", () => window.lastSignals && renderSignals(window.lastSignals));
  $("#signals-sort")?.addEventListener("change", () => window.lastSignals && renderSignals(window.lastSignals));

  await loadSignals(drug);
  await loadLatestReport(drug);
});