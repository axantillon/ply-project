const appShell = document.getElementById("app-shell");
const datasetLabel = document.getElementById("dataset-label");
const resultsSection = document.getElementById("results-section");
const resultsList = document.getElementById("results-list");
const startupStatus = document.getElementById("startup-status");
const startupPill = document.getElementById("startup-pill");
const startupMessage = document.getElementById("startup-message");
const detailModal = document.getElementById("detail-modal");
const detailModalBackdrop = document.getElementById("detail-modal-backdrop");
const closeDetailModalButton = document.getElementById("close-detail-modal");
const detailCard = document.getElementById("detail-card");
const resultsSummary = document.getElementById("results-summary");
const resultsMode = document.getElementById("results-mode");
const activeTools = document.getElementById("active-tools");
const pagination = document.getElementById("pagination");
const paginationPrev = document.getElementById("pagination-prev");
const paginationNext = document.getElementById("pagination-next");
const paginationStatus = document.getElementById("pagination-status");

const composerForm = document.getElementById("composer-form");
const clearComposerButton = document.getElementById("clear-composer");

const fields = {
  query: document.getElementById("semantic-query"),
  title: document.getElementById("find-title"),
  genre: document.getElementById("find-genre"),
  titleType: document.getElementById("find-title-type"),
  yearFrom: document.getElementById("find-year-from"),
  yearTo: document.getElementById("find-year-to"),
};
const hasDetailModal =
  Boolean(detailModal) &&
  Boolean(detailModalBackdrop) &&
  Boolean(closeDetailModalButton);

const state = {
  lastResults: new Map(),
  loadingTimers: [],
  currentQuery: "",
  currentTools: null,
  currentPage: 1,
  currentMode: "structured",
  datasetReady: false,
  manualOverrides: false,
  syncingControls: false,
};

datasetLabel.textContent = formatDatasetLabel(datasetLabel.textContent);
resultsMode.textContent = "";
resultsSummary.textContent = "";
renderActiveTools();
pollStartupStatus();

document.querySelectorAll(".tool-card input, .tool-card select").forEach((control) => {
  const markManualOverride = () => {
    if (state.syncingControls) {
      return;
    }
    state.manualOverrides = true;
    renderActiveTools();
  };

  control.addEventListener("input", markManualOverride);
  control.addEventListener("change", markManualOverride);
});

activeTools.addEventListener("click", (event) => {
  const clearButton = event.target.closest("[data-clear-tool]");
  if (!clearButton) {
    return;
  }

  clearTool(clearButton.dataset.clearTool);
  state.manualOverrides = true;
  renderActiveTools();
});

resultsList.addEventListener("click", (event) => {
  const resultCard = event.target.closest(".result-card");
  if (!resultCard) {
    return;
  }

  activateResult(resultCard.dataset.movieId);
});

clearComposerButton.addEventListener("click", () => resetComposer(true));
paginationPrev.addEventListener("click", () => goToPage(state.currentPage - 1));
paginationNext.addEventListener("click", () => goToPage(state.currentPage + 1));

if (closeDetailModalButton) {
  closeDetailModalButton.addEventListener("click", closeDetailModal);
}

if (detailModalBackdrop) {
  detailModalBackdrop.addEventListener("click", closeDetailModal);
}

fields.query.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    composerForm.requestSubmit();
  }
});

fields.query.addEventListener("input", () => {
  if (fields.query.value.trim() !== state.currentQuery) {
    state.manualOverrides = false;
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && hasDetailModal && !detailModal.classList.contains("is-hidden")) {
    closeDetailModal();
  }
});

composerForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const query = fields.query.value.trim();
  const isNewQuery = Boolean(query) && query !== state.currentQuery;
  if (isNewQuery) {
    fields.title.value = "";
    state.manualOverrides = false;
  }
  const tools = collectTools();
  if (!query && !hasStructuredScope(tools)) {
    fields.query.focus();
    return;
  }
  if (!state.datasetReady) {
    renderError("The dataset is still preparing. Wait until startup finishes, then search again.");
    return;
  }

  state.currentQuery = query;
  state.currentTools = tools;
  state.currentPage = 1;
  state.currentMode = query ? "interpreted" : "structured";
  showLoading(query, tools);

  try {
    const payload = query
      ? await runInterpretedQuery(query, tools, state.currentPage)
      : await runStructuredQuery(tools, state.currentPage);
    clearLoadingState();
    datasetLabel.textContent = formatDatasetLabel(payload.dataset);
    renderResults(payload, query, tools);
  } catch (error) {
    clearLoadingState();
    renderError(error.message);
  }
});

async function runInterpretedQuery(query, tools, page) {
  const params = new URLSearchParams({
    q: query,
    page: String(page),
  });
  if (state.manualOverrides) {
    appendStructuredParams(params, tools, true);
  }
  return fetchJson(`/api/search?${params.toString()}`);
}

async function runStructuredQuery(tools, page) {
  const params = new URLSearchParams({
    page: String(page),
  });
  appendStructuredParams(params, tools, true);
  return fetchJson(`/api/find?${params.toString()}`);
}

function appendStructuredParams(params, tools, includeEmpty = false) {
  if (includeEmpty) {
    params.set("manual_filters", "1");
    params.set("title", tools.title || "");
    params.set("genre", tools.genre || "");
    params.set("title_type", tools.title_type || "");
    params.set("year_from", tools.year_from || "");
    params.set("year_to", tools.year_to || "");
    return;
  }

  if (tools.title) params.set("title", tools.title);
  if (tools.genre) params.set("genre", tools.genre);
  if (tools.title_type) params.set("title_type", tools.title_type);
  if (tools.year_from) params.set("year_from", tools.year_from);
  if (tools.year_to) params.set("year_to", tools.year_to);
}

function collectTools() {
  return {
    title: fields.title.value.trim(),
    genre: fields.genre.value.trim(),
    title_type: fields.titleType.value.trim(),
    year_from: fields.yearFrom.value.trim(),
    year_to: fields.yearTo.value.trim(),
  };
}

function hasStructuredScope(tools) {
  return Boolean(
    tools.title ||
      tools.genre ||
      tools.title_type ||
      tools.year_from ||
      tools.year_to
  );
}

function renderResults(payload, query, tools) {
  const semantic = Boolean(query);
  const normalized = normalizePayload(payload);
  const items = normalized.results.map((movie) => ({
    movie,
    score: movie.matchScore ?? null,
  }));

  state.lastResults = new Map(items.map((item) => [item.movie.tconst, item]));

  appShell.classList.add("has-results");
  resultsSection.classList.remove("is-hidden");
  resultsMode.textContent = semantic ? "Interpreted Search" : "Structured";
  resultsSummary.textContent = semantic
    ? buildInterpretedSummary(query, normalized)
    : buildStructuredSummary(tools, items.length);
  syncFilterControls(normalized.effectiveFilters || null, semantic);
  if (semantic) {
    state.manualOverrides = false;
  }
  state.currentTools = collectTools();
  renderPagination(normalized);

  resultsList.innerHTML = items.length
    ? items
        .map(({ movie, score }, index) => renderResultCard(movie, score, index))
        .join("")
    : `<div class="empty-state">No matches found. Broaden the prompt or loosen the active tools.</div>`;

  renderEmptyDetail();

  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderResultCard(movie, score, index) {
  const title = movie.displayTitle || movie.primaryTitle || movie.tconst;
  const year = movie.displayYear ?? "Unknown";

  return `
    <button type="button" class="result-card" data-movie-id="${escapeHtml(movie.tconst)}">
      <div class="result-topline">
        <div class="result-title">${index + 1}. ${escapeHtml(title)} (${escapeHtml(year)})</div>
      </div>
      <p class="result-meta">${escapeHtml(movie.tconst)} | ${escapeHtml(movie.genreText || "n/a")}</p>
    </button>
  `;
}

function activateResult(movieId) {
  const item = state.lastResults.get(movieId);
  if (!item) {
    return;
  }

  resultsList
    .querySelectorAll(".result-card")
    .forEach((card) => card.classList.toggle("is-active", card.dataset.movieId === movieId));

  renderMovieDetail(item.movie, item.score);
  openDetailModal();
}

function renderMovieDetail(movie, score) {
  if (!detailCard) {
    return;
  }

  const displayTitle = movie.displayTitle || movie.primaryTitle || movie.tconst;
  const displayYear = movie.displayYear ?? "Unknown";
  const originalTitle =
    movie.originalTitle && movie.originalTitle !== movie.primaryTitle
      ? movie.originalTitle
      : "Original title matches the primary title";
  const rawRecord = JSON.stringify(
    {
      tconst: movie.tconst,
      titleType: movie.titleType,
      primaryTitle: movie.primaryTitle,
      originalTitle: movie.originalTitle,
      isAdult: movie.isAdult,
      startYear: movie.startYear,
      endYear: movie.endYear,
      runtimeMinutes: movie.runtimeMinutes,
      genres: movie.genres,
    },
    null,
    2
  );

  detailCard.classList.remove("detail-card-empty");
  detailCard.innerHTML = `
    <div class="detail-head">
      <div>
        <div id="detail-modal-title" class="detail-title">${escapeHtml(displayTitle)} (${escapeHtml(displayYear)})</div>
        <p class="detail-subtitle">${escapeHtml(movie.tconst)} | ${escapeHtml(originalTitle)}</p>
      </div>
      <div class="detail-chips">
        <span class="detail-chip">type: ${escapeHtml(movie.titleType || "unknown")}</span>
        <span class="detail-chip">runtime: ${escapeHtml(movie.runtimeMinutes ? `${movie.runtimeMinutes} min` : "unknown")}</span>
        <span class="detail-chip">genres: ${escapeHtml(movie.genreText || "n/a")}</span>
        <span class="detail-chip">adult: ${escapeHtml(formatAdult(movie.isAdult))}</span>
      </div>
    </div>
    <div class="detail-json-wrap">
      <span class="detail-section-label">Parsed object</span>
      <pre class="detail-json">${escapeHtml(rawRecord)}</pre>
    </div>
  `;
}

function renderEmptyDetail() {
  if (!detailCard) {
    return;
  }

  detailCard.classList.add("detail-card-empty");
  detailCard.textContent = "Select a result to inspect the parsed record.";
  resultsList
    .querySelectorAll(".result-card")
    .forEach((card) => card.classList.remove("is-active"));
  closeDetailModal();
}

function renderError(message) {
  clearLoadingState();
  appShell.classList.add("has-results");
  resultsSection.classList.remove("is-hidden");
  resultsMode.textContent = "Error";
  resultsSummary.textContent = message;
  resultsList.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
  renderEmptyDetail();
  renderPagination(null);
  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderStartupState(payload) {
  if (!startupStatus) {
    return;
  }

  if (payload.status === "ready") {
    state.datasetReady = true;
    startupStatus.classList.add("is-hidden");
    setFormDisabled(false);
    return;
  }

  state.datasetReady = false;
  startupStatus.classList.remove("is-hidden");
  setFormDisabled(true);

  if (payload.status === "error") {
    startupPill.textContent = "Dataset Error";
    startupMessage.textContent = payload.error || "The dataset failed to load.";
    return;
  }

  startupPill.textContent = "Preparing Dataset";
  startupMessage.textContent = `Loading ${formatDatasetLabel(payload.dataset)}. Search will unlock automatically when the dataset is ready.`;
}

async function pollStartupStatus() {
  try {
    const payload = await fetchJson("/api/status");
    datasetLabel.textContent = formatDatasetLabel(payload.dataset);
    renderStartupState(payload);
    if (!state.datasetReady) {
      window.setTimeout(pollStartupStatus, 1000);
    }
  } catch (error) {
    startupStatus.classList.remove("is-hidden");
    startupPill.textContent = "Waiting for Server";
    startupMessage.textContent = "The web app is still starting. Retrying shortly.";
    state.datasetReady = false;
    window.setTimeout(pollStartupStatus, 1000);
  }
}

function showLoading(query, tools) {
  clearLoadingState();
  appShell.classList.add("has-results");
  composerForm.classList.add("is-loading");
  setFormDisabled(true);
  resultsSection.classList.remove("is-hidden");
  resultsMode.textContent = query ? "Interpreting Query" : "Structured";
  resultsSummary.textContent = query
    ? `Searching for "${query}"...`
    : buildStructuredSummary(tools, 0);
  resultsList.innerHTML = `
    <div class="loading-card" aria-live="polite">
      <div class="loading-spinner" aria-hidden="true"></div>
      <div class="loading-copy">
        <strong id="loading-headline">${escapeHtml(query ? "Searching the movie dataset" : "Filtering movie records")}</strong>
        <p id="loading-message">${escapeHtml(buildLoadingMessage(query, 0))}</p>
      </div>
    </div>
  `;
  scheduleLoadingUpdates(query);
  renderEmptyDetail();
  renderPagination(null);
}

function clearLoadingState() {
  composerForm.classList.remove("is-loading");
  setFormDisabled(false);
  state.loadingTimers.forEach((timer) => window.clearTimeout(timer));
  state.loadingTimers = [];
}

function scheduleLoadingUpdates(query) {
  const messageNode = document.getElementById("loading-message");
  if (!messageNode) {
    return;
  }

  [2000, 5000, 9000].forEach((delay, index) => {
    const timer = window.setTimeout(() => {
      const currentNode = document.getElementById("loading-message");
      if (!currentNode) {
        return;
      }
      currentNode.textContent = buildLoadingMessage(query, index + 1);
    }, delay);
    state.loadingTimers.push(timer);
  });
}

function buildLoadingMessage(query, phase) {
  const interpretedLoadingMessages = [
    "Interpreting your prompt into structured filters and query terms.",
    "Scanning the IMDb metadata with the interpreted constraints.",
    "Ranking the strongest matches from the filtered result set.",
    "Still working through the full dataset.",
  ];
  const loadingMessages = query
    ? interpretedLoadingMessages
    : [
        "Applying the active metadata filters.",
        "Sorting matching records.",
        "Still working through the filtered results.",
        "Almost there.",
      ];
  return loadingMessages[Math.min(phase, loadingMessages.length - 1)];
}

function setFormDisabled(disabled) {
  composerForm
    .querySelectorAll("button, input, select, textarea")
    .forEach((element) => {
      if (element.id === "close-detail-modal") {
        return;
      }
      element.disabled = disabled;
    });
}

function openDetailModal() {
  if (!hasDetailModal) {
    return;
  }

  detailModal.classList.remove("is-hidden");
  detailModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
}

function closeDetailModal() {
  if (!hasDetailModal) {
    return;
  }

  detailModal.classList.add("is-hidden");
  detailModal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
}

function renderActiveTools() {
  const tools = collectTools();
  const badges = [];

  if (tools.genre) badges.push({ key: "genre", label: `Genre: ${tools.genre}` });
  if (tools.year_from || tools.year_to) {
    const from = tools.year_from || "...";
    const to = tools.year_to || "...";
    badges.push({ key: "years", label: `Years: ${from} to ${to}` });
  }
  if (tools.title_type) badges.push({ key: "type", label: `Type: ${tools.title_type}` });
  if (tools.title) badges.push({ key: "title", label: `Title: ${tools.title}` });

  activeTools.innerHTML = badges
    .map(
      ({ key, label }) => `
        <span class="tool-badge">
          <span>${escapeHtml(label)}</span>
          <button type="button" data-clear-tool="${escapeHtml(key)}" aria-label="Clear ${escapeHtml(key)} tool">x</button>
        </span>
      `
    )
    .join("");
}

function clearTool(toolName) {
  switch (toolName) {
    case "genre":
      fields.genre.value = "";
      break;
    case "years":
      fields.yearFrom.value = "";
      fields.yearTo.value = "";
      break;
    case "type":
      fields.titleType.value = "";
      break;
    case "title":
      fields.title.value = "";
      break;
    default:
      break;
  }
}

function resetComposer(focusQuery) {
  fields.query.value = "";
  fields.title.value = "";
  fields.genre.value = "";
  fields.titleType.value = "";
  fields.yearFrom.value = "";
  fields.yearTo.value = "";
  renderActiveTools();
  renderPagination(null);
  resultsSection.classList.add("is-hidden");
  appShell.classList.remove("has-results");
  state.manualOverrides = false;

  if (focusQuery) {
    fields.query.focus();
  }
}

function buildInterpretedSummary(query, payload) {
  return `${payload.totalResults} matches, page ${payload.page} of ${payload.totalPages}.`;
}

function normalizePayload(payload) {
  const normalizedResults = (payload.results || []).map((item) => {
    if (item && item.movie) {
      const movie = item.movie;
      if (item.score !== undefined && movie.matchScore === undefined) {
        movie.matchScore = item.score;
      }
      return movie;
    }
    return item;
  });

  const interpretedQuery = payload.interpretedQuery || {
    genres: payload.appliedFilters?.genre ? [payload.appliedFilters.genre] : [],
    titleType: payload.appliedFilters?.titleType || null,
    yearFrom: payload.appliedFilters?.yearFrom ?? null,
    yearTo: payload.appliedFilters?.yearTo ?? null,
    keywords: [],
  };

  return {
    ...payload,
    results: normalizedResults,
    interpretedQuery,
    effectiveFilters: payload.effectiveFilters || null,
    page: payload.page ?? 1,
    totalPages: payload.totalPages ?? 1,
    totalResults: payload.totalResults ?? normalizedResults.length,
  };
}

function syncFilterControls(effectiveFilters, shouldSync) {
  if (!shouldSync || !effectiveFilters) {
    return;
  }
  state.syncingControls = true;
  fields.genre.value = effectiveFilters.genre || "";
  fields.titleType.value = effectiveFilters.titleType || "";
  fields.yearFrom.value = effectiveFilters.yearFrom ?? "";
  fields.yearTo.value = effectiveFilters.yearTo ?? "";
  fields.title.value = effectiveFilters.title || "";
  state.syncingControls = false;
  renderActiveTools();
}

function renderPagination(payload) {
  if (!payload || (payload.totalPages ?? 1) <= 1) {
    pagination.classList.add("is-hidden");
    paginationStatus.textContent = "";
    paginationPrev.disabled = true;
    paginationNext.disabled = true;
    return;
  }

  pagination.classList.remove("is-hidden");
  paginationStatus.textContent = `Page ${payload.page} of ${payload.totalPages}`;
  paginationPrev.disabled = payload.page <= 1;
  paginationNext.disabled = payload.page >= payload.totalPages;
}

async function goToPage(page) {
  if (!state.currentTools || page < 1) {
    return;
  }

  state.currentPage = page;
  const query = state.currentQuery;
  const tools = collectTools();
  state.currentTools = tools;
  showLoading(query, tools);

  try {
    const payload = query
      ? await runInterpretedQuery(query, tools, page)
      : await runStructuredQuery(tools, page);
    clearLoadingState();
    renderResults(payload, query, tools);
  } catch (error) {
    clearLoadingState();
    renderError(error.message);
  }
}

function buildStructuredSummary(tools, count) {
  const scope = describeScope(tools);
  if (!scope) {
    return `${count} structured matches on this page.`;
  }
  return `${count} structured matches on this page inside ${scope}.`;
}


function describeScope(tools) {
  const parts = [];
  if (tools.genre) parts.push(`genre ${tools.genre}`);
  if (tools.title_type) parts.push(`type ${tools.title_type}`);
  if (tools.title) parts.push(`title containing ${tools.title}`);
  if (tools.year_from || tools.year_to) {
    const from = tools.year_from || "the beginning";
    const to = tools.year_to || "the latest year";
    parts.push(`years ${from} to ${to}`);
  }
  return parts.join(", ");
}

function formatDatasetLabel(path) {
  const parts = String(path).split("/");
  return parts[parts.length - 1] || String(path);
}

function formatScore(score) {
  return Number(score).toFixed(3);
}

function formatAdult(value) {
  if (value === null || value === undefined) return "unknown";
  return value ? "yes" : "no";
}

function truncate(text, limit) {
  return text.length <= limit ? text : `${text.slice(0, limit - 3)}...`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => {
    switch (character) {
      case "&":
        return "&amp;";
      case "<":
        return "&lt;";
      case ">":
        return "&gt;";
      case '"':
        return "&quot;";
      case "'":
        return "&#39;";
      default:
        return character;
    }
  });
}

async function fetchJson(url) {
  const response = await fetch(url);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Request failed");
  }
  return payload;
}
