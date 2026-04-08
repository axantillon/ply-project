const appShell = document.getElementById("app-shell");
const datasetLabel = document.getElementById("dataset-label");
const resultsSection = document.getElementById("results-section");
const resultsList = document.getElementById("results-list");
const detailModal = document.getElementById("detail-modal");
const detailModalBackdrop = document.getElementById("detail-modal-backdrop");
const closeDetailModalButton = document.getElementById("close-detail-modal");
const detailCard = document.getElementById("detail-card");
const resultsSummary = document.getElementById("results-summary");
const resultsMode = document.getElementById("results-mode");
const activeTools = document.getElementById("active-tools");
const toolDrawer = document.getElementById("tool-drawer");

const composerForm = document.getElementById("composer-form");
const clearComposerButton = document.getElementById("clear-composer");
const closeToolsButton = document.getElementById("close-tools");

const fields = {
  query: document.getElementById("semantic-query"),
  title: document.getElementById("find-title"),
  genre: document.getElementById("find-genre"),
  titleType: document.getElementById("find-title-type"),
  yearFrom: document.getElementById("find-year-from"),
  yearTo: document.getElementById("find-year-to"),
  limit: document.getElementById("semantic-limit"),
};

const DEFAULT_BACKEND = "tfidf";
const DEFAULT_LIMIT = "8";
const hasDetailModal =
  Boolean(detailModal) &&
  Boolean(detailModalBackdrop) &&
  Boolean(closeDetailModalButton);

const TOOL_CONFIG = {
  genre: { button: '[data-tool="genre"]', panel: "genre", focus: fields.genre },
  years: { button: '[data-tool="years"]', panel: "years", focus: fields.yearFrom },
  type: { button: '[data-tool="type"]', panel: "type", focus: fields.titleType },
  title: { button: '[data-tool="title"]', panel: "title", focus: fields.title },
  limit: { button: '[data-tool="limit"]', panel: "limit", focus: fields.limit },
};

const state = {
  activeTool: null,
  lastResults: new Map(),
};

datasetLabel.textContent = formatDatasetLabel(datasetLabel.textContent);
resultsMode.textContent = "";
resultsSummary.textContent = "";
renderActiveTools();

for (const [toolName, config] of Object.entries(TOOL_CONFIG)) {
  const button = document.querySelector(config.button);
  button.addEventListener("click", () => toggleToolDrawer(toolName));
}

document.querySelectorAll(".tool-card input, .tool-card select").forEach((control) => {
  control.addEventListener("input", renderActiveTools);
  control.addEventListener("change", renderActiveTools);
  control.addEventListener("focus", () => {
    const panel = control.closest(".tool-card")?.dataset.toolPanel;
    if (!panel) {
      return;
    }

    const toolName = Object.keys(TOOL_CONFIG).find((item) => TOOL_CONFIG[item].panel === panel);
    if (toolName) {
      openToolDrawer(toolName, false);
    }
  });
});

activeTools.addEventListener("click", (event) => {
  const clearButton = event.target.closest("[data-clear-tool]");
  if (!clearButton) {
    return;
  }

  clearTool(clearButton.dataset.clearTool);
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
closeToolsButton.addEventListener("click", closeToolDrawer);

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

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && hasDetailModal && !detailModal.classList.contains("is-hidden")) {
    closeDetailModal();
  }
});

composerForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const query = fields.query.value.trim();
  const tools = collectTools();
  if (!query && !hasStructuredScope(tools)) {
    fields.query.focus();
    return;
  }

  closeToolDrawer();
  showLoading(query, tools);

  try {
    const payload = query ? await runSemanticQuery(query, tools) : await runStructuredQuery(tools);
    datasetLabel.textContent = formatDatasetLabel(payload.dataset);
    renderResults(payload, query, tools);
  } catch (error) {
    renderError(error.message);
  }
});

async function runSemanticQuery(query, tools) {
  const params = new URLSearchParams({
    q: query,
    backend: tools.backend || DEFAULT_BACKEND,
    limit: tools.limit || DEFAULT_LIMIT,
  });
  appendStructuredParams(params, tools);
  return fetchJson(`/api/search?${params.toString()}`);
}

async function runStructuredQuery(tools) {
  const params = new URLSearchParams({
    limit: tools.limit || DEFAULT_LIMIT,
  });
  appendStructuredParams(params, tools);
  return fetchJson(`/api/find?${params.toString()}`);
}

function appendStructuredParams(params, tools) {
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
    backend: DEFAULT_BACKEND,
    limit: fields.limit.value.trim() || DEFAULT_LIMIT,
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
  const items = semantic
    ? payload.results.map(({ movie, score }) => ({ movie, score }))
    : payload.results.map((movie) => ({ movie, score: null }));

  state.lastResults = new Map(items.map((item) => [item.movie.tconst, item]));

  appShell.classList.add("has-results");
  resultsSection.classList.remove("is-hidden");
  resultsMode.textContent = semantic ? `Semantic / ${formatBackend(payload.backend)}` : "Structured";
  resultsSummary.textContent = semantic
    ? buildSemanticSummary(query, tools, payload)
    : buildStructuredSummary(tools, items.length);

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
  const synopsis = truncate(movie.synopsis || "No synopsis available for this record.", 180);

  return `
    <button type="button" class="result-card" data-movie-id="${escapeHtml(movie.tconst)}">
      <div class="result-topline">
        <div class="result-title">${index + 1}. ${escapeHtml(title)} (${escapeHtml(year)})</div>
        ${score === null ? "" : `<span class="result-score">${escapeHtml(formatScore(score))}</span>`}
      </div>
      <p class="result-meta">${escapeHtml(movie.tconst)} | ${escapeHtml(movie.genreText || "n/a")}</p>
      <p class="result-meta">${escapeHtml(synopsis)}</p>
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
      synopsis: movie.synopsis,
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
        ${score === null ? "" : `<span class="detail-chip">score: ${escapeHtml(formatScore(score))}</span>`}
      </div>
    </div>
    <div class="detail-copy">
      <span class="detail-section-label">Synopsis</span>
      <p>${escapeHtml(movie.synopsis || "No synopsis available for this record yet.")}</p>
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
  appShell.classList.add("has-results");
  resultsSection.classList.remove("is-hidden");
  resultsMode.textContent = "Error";
  resultsSummary.textContent = message;
  resultsList.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
  renderEmptyDetail();
  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function showLoading(query, tools) {
  appShell.classList.add("has-results");
  resultsSection.classList.remove("is-hidden");
  resultsMode.textContent = query ? "Searching" : "Filtering";
  resultsSummary.textContent = query
    ? `Searching for "${query}"...`
    : buildStructuredSummary(tools, 0);
  resultsList.innerHTML = `<div class="empty-state">Working...</div>`;
  renderEmptyDetail();
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
  if (tools.limit !== DEFAULT_LIMIT) badges.push({ key: "limit", label: `Limit: ${tools.limit}` });

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
    case "limit":
      fields.limit.value = DEFAULT_LIMIT;
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
  fields.limit.value = DEFAULT_LIMIT;
  renderActiveTools();
  closeToolDrawer();

  if (focusQuery) {
    fields.query.focus();
  }
}

function toggleToolDrawer(toolName) {
  if (!toolDrawer.classList.contains("is-hidden") && state.activeTool === toolName) {
    closeToolDrawer();
    return;
  }

  openToolDrawer(toolName, true);
}

function openToolDrawer(toolName, focusField) {
  state.activeTool = toolName;
  toolDrawer.classList.remove("is-hidden");
  syncToolUI();

  if (focusField) {
    TOOL_CONFIG[toolName].focus.focus();
  }
}

function closeToolDrawer() {
  state.activeTool = null;
  toolDrawer.classList.add("is-hidden");
  syncToolUI();
}

function syncToolUI() {
  for (const [toolName, config] of Object.entries(TOOL_CONFIG)) {
    const button = document.querySelector(config.button);
    const panel = document.querySelector(`[data-tool-panel="${config.panel}"]`);
    const active = state.activeTool === toolName;
    button.classList.toggle("is-active", active);
    panel.classList.toggle("is-focused", active);
  }
}

function buildSemanticSummary(query, tools, payload) {
  const scope = describeScope(tools);
  if (!scope) {
    return `${formatBackend(payload.backend)} returned ${payload.results.length} results for "${query}".`;
  }
  return `${formatBackend(payload.backend)} returned ${payload.results.length} results for "${query}" inside ${scope}.`;
}

function buildStructuredSummary(tools, count) {
  const scope = describeScope(tools);
  if (!scope) {
    return `${count} structured matches.`;
  }
  return `${count} structured matches inside ${scope}.`;
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

function formatBackend(backend) {
  if (backend === "tfidf") return "TF-IDF";
  return "Auto";
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
