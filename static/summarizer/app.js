const state = {
  document: null,
  jobId: null,
  pollTimer: null,
  renderedResults: 0,
  selectedPages: new Set(),
  language: localStorage.getItem("pdf-language") || "en",
};
const $ = (id) => document.getElementById(id);
const sourceUrl = JSON.parse($("source-url")?.textContent || '""');
const apiUrl = (path) => new URL(path, window.location.href).toString();

const i18n = {
  en: {
    languageToggle: "မြန်မာ",
    uploadHeading: "Upload and inspect",
    uploadHelp: "Analyze the document before choosing pages to summarize.",
    choosePdf: "Choose PDF",
    noDocument: "No document selected",
    analyzePdf: "Analyze PDF",
    analyzing: "Analyzing...",
    choosePdfFirst: "Choose a PDF file first.",
    choosePages: "Choose pages",
    totalPages: "Total pages",
    textCharacters: "Text characters",
    ocrNeeded: "OCR needed",
    ocrStatus: "OCR status",
    readyStatus: "Ready",
    unavailableStatus: "Unavailable",
    fromPage: "From page",
    toPage: "To page",
    applyRange: "Apply range",
    pages: "Pages",
    allPages: "All pages",
    contentOnly: "Content only",
    clearSelection: "Clear selection",
    summarizeSelected: "Summarize selected pages",
    content: "Content",
    toc: "TOC",
    short: "Short",
    ocr: "OCR",
    blank: "Blank",
    summarizing: "Summarizing",
    waiting: "Waiting to start",
    cancel: "Cancel",
    pageByPage: "Page-by-page output",
    summaries: "Summaries",
    ready: "Ready",
    startPdf: "Start with a PDF",
    startHelp: "Select a document to inspect its text, OCR needs, and page structure.",
    starting: "Starting...",
    device: "Device",
    ocrWarning: "{count} page(s) need OCR, but Tesseract is not installed. Those pages will be reported without summaries.",
    pageTitle: "Page {page}: {type}, {chars} characters",
    pageHeading: "Page {page}",
    ocrText: "OCR text",
    embeddedText: "Embedded text",
    chars: "chars",
    tokens: "tokens",
    truncated: "truncated",
  },
  my: {
    languageToggle: "English",
    uploadHeading: "PDF တင်ပြီး စစ်ဆေးရန်",
    uploadHelp: "အကျဉ်းချုပ်မလုပ်မီ စာမျက်နှာနှင့် စာသားအခြေအနေ စစ်ဆေးပါ။",
    choosePdf: "PDF ရွေးရန်",
    noDocument: "ဖိုင် မရွေးရသေးပါ",
    analyzePdf: "PDF စစ်ဆေးရန်",
    analyzing: "စစ်ဆေးနေသည်...",
    choosePdfFirst: "PDF ဖိုင် အရင်ရွေးပါ။",
    choosePages: "စာမျက်နှာ ရွေးရန်",
    totalPages: "စာမျက်နှာစုစုပေါင်း",
    textCharacters: "စာလုံးအရေအတွက်",
    ocrNeeded: "OCR လိုအပ်သည်",
    ocrStatus: "OCR အခြေအနေ",
    readyStatus: "အသင့်",
    unavailableStatus: "မရနိုင်ပါ",
    fromPage: "စမှတ် စာမျက်နှာ",
    toPage: "ဆုံးမှတ် စာမျက်နှာ",
    applyRange: "အပိုင်း ရွေးရန်",
    pages: "စာမျက်နှာများ",
    allPages: "အားလုံး",
    contentOnly: "အကြောင်းအရာသာ",
    clearSelection: "ရွေးထားသည်များ ဖယ်ရန်",
    summarizeSelected: "ရွေးထားသော စာမျက်နှာများ အကျဉ်းချုပ်ရန်",
    content: "အကြောင်းအရာ",
    toc: "မာတိကာ",
    short: "တိုတောင်း",
    ocr: "OCR",
    blank: "အလွတ်",
    summarizing: "အကျဉ်းချုပ်နေသည်",
    waiting: "စတင်ရန် စောင့်နေသည်",
    cancel: "ပယ်ဖျက်",
    pageByPage: "စာမျက်နှာအလိုက် ရလဒ်",
    summaries: "အကျဉ်းချုပ်များ",
    ready: "အသင့်",
    startPdf: "PDF ဖြင့် စတင်ပါ",
    startHelp: "စာသား၊ OCR လိုအပ်ချက်၊ စာမျက်နှာဖွဲ့စည်းပုံ စစ်ဆေးရန် ဖိုင်ရွေးပါ။",
    starting: "စတင်နေသည်...",
    device: "စက်",
    ocrWarning: "စာမျက်နှာ {count} ခု OCR လိုအပ်သော်လည်း Tesseract မတပ်ဆင်ထားပါ။ ထိုစာမျက်နှာများအတွက် အကျဉ်းချုပ် မထုတ်ပါ။",
    pageTitle: "စာမျက်နှာ {page}: {type}, စာလုံး {chars} လုံး",
    pageHeading: "စာမျက်နှာ {page}",
    ocrText: "OCR စာသား",
    embeddedText: "PDF စာသား",
    chars: "စာလုံး",
    tokens: "တိုကင်",
    truncated: "ဖြတ်ထားသည်",
  },
};

function t(key, values = {}) {
  return (i18n[state.language][key] || i18n.en[key] || key).replace(/\{(\w+)\}/g, (_, name) => values[name] ?? "");
}

function csrfToken() {
  return document.querySelector("[name=csrfmiddlewaretoken]").value;
}

function showError(message) {
  $("error").textContent = message;
  $("error").hidden = !message;
}

function setBusy(button, busy, label) {
  button.disabled = busy;
  button.textContent = busy ? label : t(button.dataset.i18n);
}

async function responseJson(response) {
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "The request could not be completed.");
  return data;
}

$("pdf-file").addEventListener("change", () => {
  const file = $("pdf-file").files[0];
  $("file-name").textContent = file ? file.name : t("noDocument");
});

$("upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  showError("");
  const file = $("pdf-file").files[0];
  if (!file) return showError(t("choosePdfFirst"));
  const body = new FormData();
  body.append("pdf_file", file);
  setBusy($("analyze-button"), true, t("analyzing"));
  try {
    const response = await fetch(apiUrl("api/analyze/"), { method: "POST", headers: { "X-CSRFToken": csrfToken() }, body });
    state.document = await responseJson(response);
    renderAnalysis(state.document);
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy($("analyze-button"), false, "");
  }
});

function renderAnalysis(data) {
  $("document-name").textContent = data.filename;
  $("page-count").textContent = data.page_count.toLocaleString();
  $("character-count").textContent = data.extracted_characters.toLocaleString();
  $("ocr-count").textContent = data.ocr_page_count.toLocaleString();
  $("ocr-status").textContent = data.ocr_available ? t("readyStatus") : t("unavailableStatus");
  setSelectedPages(rangeNumbers(1, data.page_count));
  $("range-start").value = 1;
  $("range-end").value = data.page_count;
  const warning = $("ocr-warning");
  warning.hidden = data.ocr_page_count === 0 || data.ocr_available;
  warning.textContent = t("ocrWarning", { count: data.ocr_page_count });
  const map = $("page-map");
  map.replaceChildren(...data.pages.map((page) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `page-chip ${page.page_type}`;
    button.dataset.page = page.page_number;
    button.textContent = page.page_number;
    button.title = t("pageTitle", { page: page.page_number, type: page.page_type_label, chars: page.char_count });
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", () => togglePage(page.page_number));
    return button;
  }));
  updateSelectedChips();
  $("analysis-section").hidden = false;
  $("empty-state").hidden = true;
  $("progress-section").hidden = true;
  $("results-section").hidden = true;
  $("analysis-section").scrollIntoView({ behavior: "smooth", block: "start" });
}

$("select-all").addEventListener("click", () => {
  if (state.document) setSelectedPages(rangeNumbers(1, state.document.page_count));
});

$("select-content").addEventListener("click", () => {
  if (!state.document) return;
  setSelectedPages(state.document.pages.filter((page) => page.page_type === "content").map((page) => page.page_number));
});

$("clear-selection").addEventListener("click", () => {
  setSelectedPages([]);
});

function rangeNumbers(start, end) {
  const max = state.document?.page_count || Math.max(start, end);
  const first = Math.min(Math.max(1, start), max);
  const last = Math.min(Math.max(1, end), max);
  const low = Math.min(first, last);
  const high = Math.max(first, last);
  return Array.from({ length: high - low + 1 }, (_, index) => low + index);
}

function setSelectedPages(numbers) {
  state.selectedPages = new Set(numbers.filter((number) => Number.isInteger(number)));
  $("page-selection").value = compressPages([...state.selectedPages].sort((a, b) => a - b));
  updateSelectedChips();
}

function togglePage(number) {
  if (state.selectedPages.has(number)) state.selectedPages.delete(number);
  else state.selectedPages.add(number);
  setSelectedPages([...state.selectedPages]);
}

function updateSelectedChips() {
  document.querySelectorAll(".page-chip").forEach((button) => {
    const selected = state.selectedPages.has(Number(button.dataset.page));
    button.classList.toggle("selected", selected);
    button.setAttribute("aria-pressed", selected ? "true" : "false");
  });
}

function parsePageSelection(value, maxPage) {
  const pages = new Set();
  for (const part of value.split(",")) {
    const trimmed = part.trim();
    if (!trimmed) continue;
    const [rawStart, rawEnd] = trimmed.split("-").map((item) => Number(item.trim()));
    if (!Number.isInteger(rawStart)) continue;
    const end = Number.isInteger(rawEnd) ? rawEnd : rawStart;
    for (const page of rangeNumbers(Math.max(1, rawStart), Math.min(maxPage, end))) pages.add(page);
  }
  return [...pages].sort((a, b) => a - b);
}

function compressPages(numbers) {
  if (!numbers.length) return "";
  const groups = [];
  let start = numbers[0], previous = numbers[0];
  for (const number of numbers.slice(1)) {
    if (number === previous + 1) {
      previous = number;
      continue;
    }
    groups.push(start === previous ? `${start}` : `${start}-${previous}`);
    start = previous = number;
  }
  groups.push(start === previous ? `${start}` : `${start}-${previous}`);
  return groups.join(", ");
}

$("page-selection").addEventListener("input", () => {
  if (!state.document) return;
  state.selectedPages = new Set(parsePageSelection($("page-selection").value, state.document.page_count));
  updateSelectedChips();
});

$("apply-range").addEventListener("click", () => {
  if (!state.document) return;
  const start = Number($("range-start").value);
  const end = Number($("range-end").value);
  if (!Number.isInteger(start) || !Number.isInteger(end)) return;
  setSelectedPages(rangeNumbers(start, end));
});

$("selection-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  showError("");
  if (state.selectedPages.size) $("page-selection").value = compressPages([...state.selectedPages].sort((a, b) => a - b));
  setBusy($("summarize-button"), true, t("starting"));
  try {
    const response = await fetch(apiUrl("api/jobs/"), {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
      body: JSON.stringify({ document_id: state.document.document_id, pages: $("page-selection").value }),
    });
    const job = await responseJson(response);
    state.jobId = job.job_id;
    state.renderedResults = 0;
    $("summary-list").replaceChildren();
    $("results-section").hidden = true;
    $("progress-section").hidden = false;
    updateProgress(job);
    pollJob();
    $("progress-section").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    showError(error.message);
    setBusy($("summarize-button"), false, "");
  }
});

async function pollJob() {
  clearTimeout(state.pollTimer);
  try {
    const job = await responseJson(await fetch(apiUrl(`api/jobs/${state.jobId}/`)));
    updateProgress(job);
    renderNewResults(job.results);
    if (["completed", "failed", "cancelled"].includes(job.status)) {
      setBusy($("summarize-button"), false, "");
      $("cancel-button").disabled = true;
      if (job.status === "failed") showError(job.error);
      return;
    }
    state.pollTimer = setTimeout(pollJob, 750);
  } catch (error) {
    showError(error.message);
    setBusy($("summarize-button"), false, "");
  }
}

function updateProgress(job) {
  $("progress-stage").textContent = job.stage;
  $("progress-pages").textContent = `${job.completed} of ${job.total} pages`;
  $("progress-percent").textContent = `${job.percent}%`;
  $("progress-fill").style.width = `${job.percent}%`;
  document.querySelector(".progress-track").setAttribute("aria-valuenow", job.percent);
  $("cancel-button").disabled = !["queued", "running"].includes(job.status);
  $("result-device").textContent = `${t("device")}: ${job.device}${job.elapsed_seconds ? ` - ${job.elapsed_seconds}s` : ""}`;
}

function renderNewResults(results) {
  if (!results.length) return;
  $("results-section").hidden = false;
  for (const item of results.slice(state.renderedResults)) {
    const article = document.createElement("article");
    article.className = "summary-card";
    const header = document.createElement("header");
    const title = document.createElement("h3");
    title.textContent = t("pageHeading", { page: item.page_number });
    const meta = document.createElement("p");
    const source = item.text_source === "ocr" ? t("ocrText") : t("embeddedText");
    const parts = [
      item.page_type_label,
      source,
      `${item.char_count} ${t("chars")}`,
      `${item.token_count} ${t("tokens")}`,
    ];
    if (item.truncated) parts.push(t("truncated"));
    meta.textContent = parts.join(" - ");
    header.append(title, meta);
    const summary = document.createElement("p");
    summary.textContent = item.summary;
    article.append(header, summary);
    if (item.warning) {
      const warning = document.createElement("p");
      warning.className = "summary-warning";
      warning.textContent = item.warning;
      article.append(warning);
    }
    $("summary-list").append(article);
  }
  state.renderedResults = results.length;
}

$("cancel-button").addEventListener("click", async () => {
  if (!state.jobId) return;
  $("cancel-button").disabled = true;
  try {
    await responseJson(await fetch(apiUrl(`api/jobs/${state.jobId}/cancel/`), { method: "POST", headers: { "X-CSRFToken": csrfToken() } }));
  } catch (error) {
    showError(error.message);
  }
});

const themes = ["system", "light", "dark"];
const themeLabels = { system: "System", light: "Light", dark: "Dark" };

function updateThemeLabel() {
  const theme = document.documentElement.dataset.theme || "system";
  $("theme-label").textContent = themeLabels[theme] || "System";
  $("theme-toggle").title = `Color theme: ${themeLabels[theme] || "System"}`;
  $("theme-toggle").setAttribute("aria-label", `Color theme: ${themeLabels[theme] || "System"}. Click to change.`);
}

$("theme-toggle").addEventListener("click", () => {
  const current = document.documentElement.dataset.theme || "system";
  const next = themes[(themes.indexOf(current) + 1) % themes.length];
  document.documentElement.dataset.theme = next;
  localStorage.setItem("pdf-theme", next);
  updateThemeLabel();
});

updateThemeLabel();

function applyLanguage() {
  document.documentElement.lang = state.language === "my" ? "my" : "en";
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  if (!$("pdf-file").files[0]) $("file-name").textContent = t("noDocument");
  if (state.document) $("ocr-status").textContent = state.document.ocr_available ? t("readyStatus") : t("unavailableStatus");
  $("language-label").textContent = t("languageToggle");
}

$("language-toggle").addEventListener("click", () => {
  state.language = state.language === "en" ? "my" : "en";
  localStorage.setItem("pdf-language", state.language);
  applyLanguage();
});

applyLanguage();

async function analyzeSourcePdf() {
  if (!sourceUrl) return;
  showError("");
  $("file-name").textContent = sourceUrl.split("/").pop() || "Linked PDF";
  setBusy($("analyze-button"), true, t("analyzing"));
  try {
    const response = await fetch(apiUrl("api/analyze-source/"), {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
      body: JSON.stringify({ source_url: sourceUrl }),
    });
    state.document = await responseJson(response);
    renderAnalysis(state.document);
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy($("analyze-button"), false, "");
  }
}

analyzeSourcePdf();
