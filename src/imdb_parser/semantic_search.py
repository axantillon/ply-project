from __future__ import annotations

import json
import math
import os
import re
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .models import Movie


TOKEN_RE = re.compile(r"[a-z0-9]+")
GEMINI_BATCH_EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents"
)


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(text.lower())


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


class TfidfSemanticIndex:
    def __init__(self, movies: Iterable[Movie]):
        self.movies = list(movies)
        self.doc_tokens = [tokenize(movie.text_for_semantic_search()) for movie in self.movies]
        self.idf = self._build_idf(self.doc_tokens)
        self.doc_vectors = [self._vectorize(tokens) for tokens in self.doc_tokens]

    @staticmethod
    def _build_idf(doc_tokens: List[List[str]]) -> Dict[str, float]:
        doc_count = len(doc_tokens)
        document_frequency: Counter[str] = Counter()
        for tokens in doc_tokens:
            document_frequency.update(set(tokens))

        idf: Dict[str, float] = {}
        for token, frequency in document_frequency.items():
            idf[token] = math.log((1 + doc_count) / (1 + frequency)) + 1.0
        return idf

    def _vectorize(self, tokens: List[str]) -> Dict[str, float]:
        counts = Counter(tokens)
        total = sum(counts.values())
        if total == 0:
            return {}
        return {
            token: (count / total) * self.idf.get(token, 1.0)
            for token, count in counts.items()
        }

    @staticmethod
    def _cosine_sparse(left: Dict[str, float], right: Dict[str, float]) -> float:
        if not left or not right:
            return 0.0
        numerator = sum(left[token] * right[token] for token in left.keys() & right.keys())
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        return numerator / (left_norm * right_norm)

    def search(self, query: str, limit: int = 5) -> List[Tuple[Movie, float]]:
        query_vector = self._vectorize(tokenize(query))
        scored: List[Tuple[Movie, float]] = []
        for movie, vector in zip(self.movies, self.doc_vectors):
            score = self._cosine_sparse(query_vector, vector)
            if score > 0:
                scored.append((movie, score))
        scored.sort(key=lambda item: (-item[1], item[0].primary_title.lower()))
        return scored[:limit]


class GeminiEmbeddingSemanticIndex:
    def __init__(
        self,
        movies: Iterable[Movie],
        *,
        api_key: Optional[str] = None,
        cache_path: Optional[Path] = None,
        output_dimensionality: Optional[int] = None,
    ):
        self.movies = list(movies)
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY must be set to use Gemini semantic search")
        self.cache_path = cache_path
        self.output_dimensionality = output_dimensionality
        self.cache = self._load_cache(cache_path)
        self.doc_vectors = self._build_document_vectors()

    def search(self, query: str, limit: int = 5) -> List[Tuple[Movie, float]]:
        query_vector = self._embed_query(query)
        scored: List[Tuple[Movie, float]] = []
        for movie, vector in zip(self.movies, self.doc_vectors):
            score = cosine_similarity(query_vector, vector)
            if score > 0:
                scored.append((movie, score))
        scored.sort(key=lambda item: (-item[1], item[0].primary_title.lower()))
        return scored[:limit]

    def _build_document_vectors(self) -> List[List[float]]:
        missing_movies: List[Movie] = []
        for movie in self.movies:
            key = self._movie_cache_key(movie)
            if key not in self.cache:
                missing_movies.append(movie)

        if missing_movies:
            texts = [movie.text_for_semantic_search() for movie in missing_movies]
            embeddings = self._batch_embed(texts, task_type="RETRIEVAL_DOCUMENT", titles=[
                movie.primary_title for movie in missing_movies
            ])
            for movie, embedding in zip(missing_movies, embeddings):
                self.cache[self._movie_cache_key(movie)] = embedding
            self._save_cache()

        return [self.cache[self._movie_cache_key(movie)] for movie in self.movies]

    def _embed_query(self, query: str) -> List[float]:
        key = "query::" + query
        if key not in self.cache:
            self.cache[key] = self._batch_embed([query], task_type="RETRIEVAL_QUERY")[0]
            self._save_cache()
        return self.cache[key]

    def _batch_embed(
        self,
        texts: List[str],
        *,
        task_type: str,
        titles: Optional[List[str]] = None,
    ) -> List[List[float]]:
        requests = []
        for index, text in enumerate(texts):
            request = {
                "model": "models/gemini-embedding-001",
                "content": {"parts": [{"text": text}]},
                "taskType": task_type,
            }
            if titles is not None:
                request["title"] = titles[index]
            if self.output_dimensionality is not None:
                request["outputDimensionality"] = self.output_dimensionality
            requests.append(request)

        payload = json.dumps({"requests": requests}).encode("utf-8")
        request = urllib.request.Request(
            GEMINI_BATCH_EMBED_URL,
            data=payload,
            headers={
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = json.load(response)
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini embedding request failed: {details}") from exc

        embeddings = body.get("embeddings", [])
        return [item["values"] for item in embeddings]

    @staticmethod
    def _movie_cache_key(movie: Movie) -> str:
        return "movie::" + movie.tconst

    @staticmethod
    def _load_cache(path: Optional[Path]) -> Dict[str, List[float]]:
        if path is None or not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_cache(self) -> None:
        if self.cache_path is None:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(self.cache, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def semantic_search(
    movies: List[Movie],
    query: str,
    limit: int = 5,
    backend: str = "tfidf",
    cache_path: Optional[Path] = None,
    gemini_api_key: Optional[str] = None,
    output_dimensionality: Optional[int] = None,
) -> List[Tuple[Movie, float]]:
    if backend == "tfidf":
        return TfidfSemanticIndex(movies).search(query, limit=limit)
    if backend == "gemini":
        return GeminiEmbeddingSemanticIndex(
            movies,
            api_key=gemini_api_key,
            cache_path=cache_path,
            output_dimensionality=output_dimensionality,
        ).search(query, limit=limit)
    raise ValueError(f"Unsupported semantic backend: {backend}")
