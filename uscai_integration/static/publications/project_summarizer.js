(() => {
  const app = document.getElementById("pdf-summary-app");
  if (!app) return;

  const state = {
    document: null,
    selectedPages: new Set(),
    jobId: null,
    pollTimer: null,
    renderedResults: 0,
    language: localStorage.getItem("uscai-pdf-language") || "en",
  };
  const $ = (id) => document.getElementById(id);

  const i18n = {
    en: {
      language: "မြန်မာ", back: "Back to project", title: "PDF Summarizer",
      sourceHeading: "Project document", analyzing: "Analyzing document", ready: "Ready",
      choosePages: "Choose pages", selected: "{count} page(s) selected",
      totalPages: "Total pages", textCharacters: "Text characters", ocrNeeded: "OCR needed",
      ocrStatus: "OCR status", ocrUnavailable: "Not enabled", fromPage: "From page",
      toPage: "To page", applyRange: "Apply range", pages: "Pages", allPages: "All pages",
      contentOnly: "Content only", clearSelection: "Clear selection",
      summarizeSelected: "Summarize selected pages", content: "Content", toc: "TOC", short: "Short",
      summarizing: "Summarizing", cancel: "Cancel", pageOutput: "Page-by-page output",
      summaries: "Summaries", waiting: "Waiting to start", preparing: "Preparing selected pages",
      completed: "Completed", cancelled: "Cancelled", cancellation: "Cancellation requested",
      pageStage: "Summarizing page {page}", pageProgress: "{done} of {total} pages",
      pageHeading: "Page {page}", chars: "chars", tokens: "tokens", truncated: "truncated",
      ocrWarning: "{count} page(s) have no extractable text. OCR is not enabled for this demo.",
      start: "Starting...", device: "Device",
    },
    my: {
      language: "English", back: "ပရောဂျက်သို့ ပြန်ရန်", title: "PDF အကျဉ်းချုပ်",
      sourceHeading: "ပရောဂျက် စာရွက်စာတမ်း", analyzing: "စာရွက်စာတမ်း စစ်ဆေးနေသည်", ready: "အသင့်ဖြစ်ပြီ",
      choosePages: "စာမျက်နှာများ ရွေးချယ်ရန်", selected: "စာမျက်နှာ {count} ခု ရွေးထားသည်",
      totalPages: "စာမျက်နှာ စုစုပေါင်း", textCharacters: "စာလုံး အရေအတွက်", ocrNeeded: "OCR လိုအပ်",
      ocrStatus: "OCR အခြေအနေ", ocrUnavailable: "မဖွင့်ထားပါ", fromPage: "စာမျက်နှာမှ",
      toPage: "စာမျက်နှာအထိ", applyRange: "အပိုင်း ရွေးရန်", pages: "စာမျက်နှာများ", allPages: "အားလုံး",
      contentOnly: "အကြောင်းအရာသာ", clearSelection: "ရွေးချယ်မှု ဖျက်ရန်",
      summarizeSelected: "ရွေးထားသော စာမျက်နှာများကို အကျဉ်းချုပ်ရန်", content: "အကြောင်းအရာ", toc: "မာတိကာ", short: "စာတို",
      summarizing: "အကျဉ်းချုပ်နေသည်", cancel: "ရပ်ရန်", pageOutput: "စာမျက်နှာအလိုက် ရလဒ်",
      summaries: "အကျဉ်းချုပ်များ", waiting: "စတင်ရန် စောင့်နေသည်", preparing: "ရွေးထားသော စာမျက်နှာများ ပြင်ဆင်နေသည်",
      completed: "ပြီးပါပြီ", cancelled: "ရပ်လိုက်ပါပြီ", cancellation: "ရပ်ရန် တောင်းဆိုထားသည်",
      pageStage: "စာမျက်နှာ {page} ကို အကျဉ်းချုပ်နေသည်", pageProgress: "စာမျက်နှာ {total} ခုမှ {done} ခု ပြီးပါပြီ",
      pageHeading: "စာမျက်နှာ {page}", chars: "စာလုံး", tokens: "တိုကင်", truncated: "ဖြတ်တောက်ထားသည်",
      ocrWarning: "စာမျက်နှာ {count} ခုတွင် ထုတ်ယူနိုင်သော စာသားမရှိပါ။ ယခုစမ်းသပ်မှုတွင် OCR မဖွင့်ထားပါ။",
      start: "စတင်နေသည်...", device: "စက်",
    },
  };

  function t(key, values = {}) {
    const value = i18n[state.language][key] || i18n.en[key] || key;
    return value.replace(/\{(\w+)\}/g, (_, name) => values[name] ?? "");
  }

  function csrfToken() {
    return app.querySelector("[name=csrfmiddlewaretoken]").value;
  }

  function showError(message) {
    $("error").textContent = message || "";
    $("error").hidden = !message;
  }

  async function responseJson(response) {
    let data;
    try {
      data = await response.json();
    } catch (_) {
      throw new Error(`Request failed (${response.status}).`);
    }
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status}).`);
    return data;
  }

  function rangeNumbers(start, end) {
    const max = state.document?.page_count || Math.max(start, end);
    const first = Math.min(Math.max(1, start), max);
    const last = Math.min(Math.max(1, end), max);
    const low = Math.min(first, last);
    const high = Math.max(first, last);
    return Array.from({ length: high - low + 1 }, (_, index) => low + index);
  }

  function compressPages(numbers) {
    if (!numbers.length) return "";
    const groups = [];
    let start = numbers[0];
    let previous = numbers[0];
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

  function parsePages(value) {
    const pages = new Set();
    for (const part of value.split(",")) {
      const trimmed = part.trim();
      if (!trimmed) continue;
      const pieces = trimmed.split("-").map((item) => Number(item.trim()));
      if (!Number.isInteger(pieces[0])) continue;
      const end = Number.isInteger(pieces[1]) ? pieces[1] : pieces[0];
      for (const page of rangeNumbers(pieces[0], end)) pages.add(page);
    }
    return [...pages].sort((a, b) => a - b);
  }

  function updateSelectedChips() {
    document.querySelectorAll(".kls-page-chip").forEach((button) => {
      const selected = state.selectedPages.has(Number(button.dataset.page));
      button.classList.toggle("selected", selected);
      button.setAttribute("aria-pressed", selected ? "true" : "false");
    });
    $("selection-count").textContent = t("selected", { count: state.selectedPages.size });
  }

  function setSelectedPages(numbers) {
    state.selectedPages = new Set(numbers.filter(Number.isInteger));
    $("page-selection").value = compressPages([...state.selectedPages].sort((a, b) => a - b));
    updateSelectedChips();
  }

  function togglePage(page) {
    if (state.selectedPages.has(page)) state.selectedPages.delete(page);
    else state.selectedPages.add(page);
    setSelectedPages([...state.selectedPages]);
  }

  function renderAnalysis(data) {
    $("page-count").textContent = data.page_count.toLocaleString();
    $("character-count").textContent = data.extracted_characters.toLocaleString();
    $("ocr-count").textContent = data.ocr_page_count.toLocaleString();
    $("range-start").value = 1;
    $("range-end").value = data.page_count;
    $("range-start").max = data.page_count;
    $("range-end").max = data.page_count;
    $("ocr-warning").hidden = data.ocr_page_count === 0;
    $("ocr-warning").textContent = t("ocrWarning", { count: data.ocr_page_count });
    const buttons = data.pages.map((page) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `kls-page-chip ${page.page_type}`;
      button.dataset.page = page.page_number;
      button.textContent = page.page_number;
      button.title = `${page.page_type_label}: ${page.char_count} ${t("chars")}`;
      button.setAttribute("aria-pressed", "false");
      button.addEventListener("click", () => togglePage(page.page_number));
      return button;
    });
    $("page-map").replaceChildren(...buttons);
    setSelectedPages(rangeNumbers(1, data.page_count));
    $("analysis-state").classList.add("ready");
    $("analysis-state").innerHTML = `<i class="fa-solid fa-circle-check" aria-hidden="true"></i><span>${t("ready")}</span>`;
    $("analysis-section").hidden = false;
  }

  async function analyze() {
    showError("");
    try {
      const response = await fetch(app.dataset.analyzeUrl, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken() },
      });
      state.document = await responseJson(response);
      renderAnalysis(state.document);
    } catch (error) {
      $("analysis-state").innerHTML = `<i class="fa-solid fa-circle-exclamation" aria-hidden="true"></i><span>Failed</span>`;
      showError(error.message);
    }
  }

  $("select-all").addEventListener("click", () => {
    if (state.document) setSelectedPages(rangeNumbers(1, state.document.page_count));
  });

  $("select-content").addEventListener("click", () => {
    if (state.document) {
      setSelectedPages(state.document.pages.filter((page) => page.page_type === "content").map((page) => page.page_number));
    }
  });

  $("clear-selection").addEventListener("click", () => setSelectedPages([]));

  $("apply-range").addEventListener("click", () => {
    const start = Number($("range-start").value);
    const end = Number($("range-end").value);
    if (Number.isInteger(start) && Number.isInteger(end)) setSelectedPages(rangeNumbers(start, end));
  });

  $("page-selection").addEventListener("input", () => {
    if (!state.document) return;
    state.selectedPages = new Set(parsePages($("page-selection").value));
    updateSelectedChips();
  });

  function jobUrl(template, jobId) {
    return template.replace("JOB_ID", jobId);
  }

  function translatedStage(stage) {
    if (stage === "Waiting to start") return t("waiting");
    if (stage === "Preparing selected pages") return t("preparing");
    if (stage === "Completed") return t("completed");
    if (stage === "Cancelled") return t("cancelled");
    if (stage === "Cancellation requested") return t("cancellation");
    const match = /^Summarizing page (\d+)$/.exec(stage);
    return match ? t("pageStage", { page: match[1] }) : stage;
  }

  function updateProgress(job) {
    $("progress-stage").textContent = translatedStage(job.stage);
    $("progress-pages").textContent = t("pageProgress", { done: job.completed, total: job.total });
    $("progress-percent").textContent = `${job.percent}%`;
    $("progress-fill").style.width = `${job.percent}%`;
    document.querySelector(".kls-progress-track").setAttribute("aria-valuenow", job.percent);
    $("cancel-button").disabled = !["queued", "running"].includes(job.status);
    $("result-device").textContent = `${t("device")}: ${job.device}${job.elapsed_seconds ? ` - ${job.elapsed_seconds}s` : ""}`;
  }

  function renderNewResults(results) {
    if (!results.length) return;
    $("results-section").hidden = false;
    for (const item of results.slice(state.renderedResults)) {
      const article = document.createElement("article");
      article.className = "kls-summary-card";
      const header = document.createElement("header");
      const title = document.createElement("h3");
      title.textContent = t("pageHeading", { page: item.page_number });
      const meta = document.createElement("p");
      const parts = [item.page_type_label, `${item.char_count} ${t("chars")}`, `${item.token_count} ${t("tokens")}`];
      if (item.truncated) parts.push(t("truncated"));
      meta.textContent = parts.join(" · ");
      header.append(title, meta);
      const summary = document.createElement("p");
      summary.textContent = item.summary;
      article.append(header, summary);
      if (item.warning) {
        const warning = document.createElement("p");
        warning.className = "kls-summary-warning";
        warning.textContent = item.warning;
        article.append(warning);
      }
      $("summary-list").append(article);
    }
    state.renderedResults = results.length;
  }

  async function pollJob() {
    clearTimeout(state.pollTimer);
    try {
      const response = await fetch(jobUrl(app.dataset.jobUrlTemplate, state.jobId));
      const job = await responseJson(response);
      updateProgress(job);
      renderNewResults(job.results);
      if (["completed", "failed", "cancelled"].includes(job.status)) {
        $("summarize-button").disabled = false;
        if (job.status === "failed") showError(job.error);
        return;
      }
      state.pollTimer = setTimeout(pollJob, 900);
    } catch (error) {
      $("summarize-button").disabled = false;
      showError(error.message);
    }
  }

  $("selection-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    showError("");
    if (!state.selectedPages.size) return showError("Choose at least one page.");
    const button = $("summarize-button");
    button.disabled = true;
    button.querySelector("span").textContent = t("start");
    try {
      const response = await fetch(app.dataset.createJobUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
        body: JSON.stringify({
          document_id: state.document.document_id,
          pages: compressPages([...state.selectedPages].sort((a, b) => a - b)),
        }),
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
      button.disabled = false;
      showError(error.message);
    } finally {
      button.querySelector("span").textContent = t("summarizeSelected");
    }
  });

  $("cancel-button").addEventListener("click", async () => {
    if (!state.jobId) return;
    $("cancel-button").disabled = true;
    try {
      const response = await fetch(jobUrl(app.dataset.cancelUrlTemplate, state.jobId), {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken() },
      });
      await responseJson(response);
    } catch (error) {
      showError(error.message);
    }
  });

  function applyLanguage() {
    document.documentElement.lang = state.language === "my" ? "my" : "en";
    app.querySelectorAll("[data-i18n]").forEach((node) => {
      node.textContent = t(node.dataset.i18n);
    });
    $("language-label").textContent = t("language");
    if (state.document) {
      $("selection-count").textContent = t("selected", { count: state.selectedPages.size });
      $("ocr-warning").textContent = t("ocrWarning", { count: state.document.ocr_page_count });
    }
  }

  $("language-toggle").addEventListener("click", () => {
    state.language = state.language === "en" ? "my" : "en";
    localStorage.setItem("uscai-pdf-language", state.language);
    applyLanguage();
  });

  const themes = ["system", "light", "dark"];
  const themeLabels = { system: "System", light: "Light", dark: "Dark" };

  function applyTheme(theme) {
    document.documentElement.dataset.pdfTheme = theme;
    $("theme-label").textContent = themeLabels[theme];
  }

  $("theme-toggle").addEventListener("click", () => {
    const current = document.documentElement.dataset.pdfTheme || "system";
    const next = themes[(themes.indexOf(current) + 1) % themes.length];
    localStorage.setItem("uscai-pdf-theme", next);
    applyTheme(next);
  });

  applyTheme(localStorage.getItem("uscai-pdf-theme") || "system");
  applyLanguage();
  analyze();
})();
