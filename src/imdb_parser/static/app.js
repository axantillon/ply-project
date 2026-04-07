const resultsList = document.getElementById("results-list");
const detailCard = document.getElementById("detail-card");
const resultsSummary = document.getElementById("results-summary");
const resultsMode = document.getElementById("results-mode");
const datasetLabel = document.getElementById("dataset-label");
const statsGrid = document.getElementById("stats-grid");

const queryForm = document.getElementById("query-form");
const filterPanel = document.getElementById("filter-panel");
const toggleFiltersButton = document.getElementById("toggle-filters");

toggleFiltersButton.addEventListener("click", () => {
  const expanded = toggleFiltersButton.getAttribute("aria-expanded") === "true";
  toggleFiltersButton.setAttribute("aria-expanded", String(!expanded));
  filterPanel.classList.toggle("is-hidden", expanded);
});

queryForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const query = document.getElementById("semantic-query").value.trim();
  const filters = collectFilters();

  if (!query && !hasAnyFilter(filters)) {
    renderEmpty("Enter a query or add a filter to search the dataset.");
    return;
  }

  setLoading("Searching...");

  try {
    if (query) {
      const params = new URLSearchParams({
        q: query,
        backend: document.getElementById("semantic-backend").value,
        limit: filters.limit || "8",
      });
      const payload = await fetchJson(`/api/search?${params.toString()}`);
      datasetLabel.textContent = payload.dataset;
      resultsMode.textContent = `Semantic · ${payload.backend}`;
      resultsSummary.textContent = query;

      let results = payload.results.map(({ movie, score }) => ({ movie, score }));
      results = applyClientFilters(results, filters);
      renderSemanticResults(results);
      return;
    }

    const params = new URLSearchParams({ limit: filters.limit || "12" });
    for (const [key, value] of Object.entries(filters)) {
      if (!value || key === "limit") {
        continue;
      }
      params.set(key, value);
    }
    const payload = await fetchJson(`/api/find?${params.toString()}`);
    datasetLabel.textContent = payload.dataset;
    resultsMode.textContent = "Structured";
    resultsSummary.textContent = summarizeFilters(filters);
    renderStructuredResults(payload.results);
  } catch (error) {
    renderEmpty(error.message);
  }
});

function collectFilters() {
  return {
    title: document.getElementById("find-title").value.trim(),
    genre: document.getElementById("find-genre").value.trim(),
    title_type: document.getElementById("find-title-type").value.trim(),
    year_from: document.getElementById("find-year-from").value.trim(),
    year_to: document.getElementById("find-year-to").value.trim(),
    limit: document.getElementById("semantic-limit").value.trim(),
  };
}

function hasAnyFilter(filters) {
  return Object.entries(filters).some(([key, value]) => key !== "limit" && value);
}

function applyClientFilters(results, filters) {
  return results.filter(({ movie }) => {
    if (filters.title) {
      const title = filters.title.toLowerCase();
      const primary = (movie.primaryTitle || "").toLowerCase();
      const original = (movie.originalTitle || "").toLowerCase();
      if (!primary.includes(title) && !original.includes(title)) {
        return false;
      }
    }
    if (filters.genre) {
      const genre = filters.genre.toLowerCase();
      const genres = (movie.genres || []).map((item) => item.toLowerCase());
      if (!genres.includes(genre)) {
        return false;
      }
    }
    if (filters.title_type) {
      if ((movie.titleType || "").toLowerCase() !== filters.title_type.toLowerCase()) {
        return false;
      }
    }
    if (filters.year_from) {
      if (!movie.startYear || movie.startYear < Number(filters.year_from)) {
        return false;
      }
    }
    if (filters.year_to) {
      if (!movie.startYear || movie.startYear > Number(filters.year_to)) {
        return false;
      }
    }
    return true;
  });
}

function summarizeFilters(filters) {
  const parts = [];
  if (filters.title) parts.push(`title contains "${filters.title}"`);
  if (filters.genre) parts.push(`genre ${filters.genre}`);
  if (filters.title_type) parts.push(`type ${filters.title_type}`);
  if (filters.year_from) parts.push(`from ${filters.year_from}`);
  if (filters.year_to) parts.push(`to ${filters.year_to}`);
  return parts.length ? parts.join(" · ") : "Structured results";
}

async function fetchStats() {
  const payload = await fetchJson("/api/stats");
  datasetLabel.textContent = payload.dataset;
  const yearRange = payload.yearRange ? `${payload.yearRange[0]}-${payload.yearRange[1]}` : "Unknown";
  const topGenres = payload.topGenres.length
    ? `<ul class="genre-list">${payload.topGenres
        .slice(0, 4)
        .map(([genre, count]) => `<li>${genre} · ${count}</li>`)
        .join("")}</ul>`
    : "<span class=\"stat-label\">No genres</span>";

  statsGrid.innerHTML = `
    <article class="stat-card">
      <span class="stat-label">Movies</span>
      <span class="stat-value">${payload.movieCount}</span>
    </article>
    <article class="stat-card">
      <span class="stat-label">Synopses</span>
      <span class="stat-value">${payload.withSynopsisCount}</span>
    </article>
    <article class="stat-card">
      <span class="stat-label">Years</span>
      <span class="stat-value">${yearRange}</span>
    </article>
    <article class="stat-card">
      <span class="stat-label">Top Genres</span>
      ${topGenres}
    </article>
  `;
}

function renderSemanticResults(results) {
  if (!results.length) {
    renderEmpty("No matches found. Try broader language or loosen the filters.");
    return;
  }

  resultsList.innerHTML = results
    .map(
      ({ movie, score }, index) => `
        <article class="result-card" data-movie-id="${movie.tconst}">
          <div class="result-topline">
            <div class="result-title">${index + 1}. ${movie.displayTitle} (${movie.displayYear})</div>
            <span class="result-score">${score.toFixed(3)}</span>
          </div>
          <p class="result-meta">${movie.tconst} · ${movie.genreText}</p>
          <p class="result-meta">${truncate(movie.synopsis || "No synopsis available.", 120)}</p>
        </article>
      `
    )
    .join("");
  bindResultSelection(results.map((item) => item.movie));
  renderMovieDetail(results[0].movie);
}

function renderStructuredResults(results) {
  if (!results.length) {
    renderEmpty("No matches found. Adjust the filters and try again.");
    return;
  }

  resultsList.innerHTML = results
    .map(
      (movie, index) => `
        <article class="result-card" data-movie-id="${movie.tconst}">
          <div class="result-topline">
            <div class="result-title">${index + 1}. ${movie.displayTitle} (${movie.displayYear})</div>
          </div>
          <p class="result-meta">${movie.tconst} · ${movie.genreText}</p>
          <p class="result-meta">${truncate(movie.synopsis || "No synopsis available.", 120)}</p>
        </article>
      `
    )
    .join("");
  bindResultSelection(results);
  renderMovieDetail(results[0]);
}

function bindResultSelection(movies) {
  const byId = new Map(movies.map((movie) => [movie.tconst, movie]));
  const cards = [...document.querySelectorAll(".result-card")];
  cards.forEach((card) => {
    card.addEventListener("click", () => {
      cards.forEach((item) => item.classList.remove("is-active"));
      card.classList.add("is-active");
      const movie = byId.get(card.dataset.movieId);
      if (movie) {
        renderMovieDetail(movie);
      }
    });
  });
  if (cards.length) {
    cards[0].classList.add("is-active");
  }
}

function renderMovieDetail(movie) {
  detailCard.classList.remove("detail-card-empty");
  detailCard.innerHTML = `
    <div class="detail-topline">
      <div class="detail-title">${movie.displayTitle} (${movie.displayYear})</div>
      <span class="mode-chip">${movie.tconst}</span>
    </div>
    <div class="detail-grid">
      <div class="detail-chip">
        <span class="stat-label">Type</span>
        <strong>${movie.titleType}</strong>
      </div>
      <div class="detail-chip">
        <span class="stat-label">Runtime</span>
        <strong>${movie.runtimeMinutes ? `${movie.runtimeMinutes} min` : "Unknown"}</strong>
      </div>
      <div class="detail-chip">
        <span class="stat-label">Genres</span>
        <strong>${movie.genreText}</strong>
      </div>
      <div class="detail-chip">
        <span class="stat-label">Adult</span>
        <strong>${movie.isAdult === null ? "Unknown" : movie.isAdult ? "Yes" : "No"}</strong>
      </div>
    </div>
    <div class="detail-copy">
      <span class="stat-label">Synopsis</span>
      <p>${movie.synopsis || "No synopsis available for this movie yet."}</p>
    </div>
  `;
}

function setLoading(message) {
  resultsList.innerHTML = `<div class="empty-state">${message}</div>`;
}

function renderEmpty(message) {
  resultsList.innerHTML = `<div class="empty-state">${message}</div>`;
  detailCard.classList.add("detail-card-empty");
  detailCard.textContent = "Search for something to inspect a parsed movie record.";
}

function truncate(text, limit) {
  return text.length <= limit ? text : `${text.slice(0, limit - 1)}…`;
}

async function fetchJson(url) {
  const response = await fetch(url);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Request failed");
  }
  return payload;
}

fetchStats().catch((error) => {
  renderEmpty(error.message);
});
