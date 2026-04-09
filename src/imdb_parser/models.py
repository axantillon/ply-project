from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Tuple, Union


class MovieValidationError(ValueError):
    """Raised when parsed JSON does not satisfy the expected movie schema."""


def _require_type(name: str, value: Any, expected_type: Union[type, Tuple[type, ...]]) -> Any:
    if not isinstance(value, expected_type):
        expected = (
            ", ".join(item.__name__ for item in expected_type)
            if isinstance(expected_type, tuple)
            else expected_type.__name__
        )
        raise MovieValidationError(f"Field {name!r} must be of type {expected}")
    return value


def _optional_int(name: str, value: Any) -> Optional[int]:
    if value is None:
        return None
    return _require_type(name, value, int)


def _optional_bool(name: str, value: Any) -> Optional[bool]:
    if value is None:
        return None
    return _require_type(name, value, bool)


def _optional_str(name: str, value: Any) -> Optional[str]:
    if value is None:
        return None
    return _require_type(name, value, str)


@dataclass
class Movie:
    tconst: str
    title_type: str
    primary_title: str
    original_title: Optional[str]
    is_adult: Optional[bool]
    start_year: Optional[int]
    end_year: Optional[int]
    runtime_minutes: Optional[int]
    genres: list[str]
    synopsis: Optional[str] = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "Movie":
        required_fields = ("tconst", "titleType", "primaryTitle", "genres")
        missing = [field for field in required_fields if field not in payload]
        if missing:
            joined = ", ".join(missing)
            raise MovieValidationError(f"Missing required field(s): {joined}")

        genres_value = _require_type("genres", payload["genres"], list)
        genres: list[str] = []
        for index, genre in enumerate(genres_value):
            if not isinstance(genre, str):
                raise MovieValidationError(f"genres[{index}] must be a string")
            genres.append(genre)

        tconst = _require_type("tconst", payload["tconst"], str)
        if not tconst.startswith("tt"):
            raise MovieValidationError("Field 'tconst' must start with 'tt'")

        return cls(
            tconst=tconst,
            title_type=_require_type("titleType", payload["titleType"], str),
            primary_title=_require_type("primaryTitle", payload["primaryTitle"], str),
            original_title=_optional_str("originalTitle", payload.get("originalTitle")),
            is_adult=_optional_bool("isAdult", payload.get("isAdult")),
            start_year=_optional_int("startYear", payload.get("startYear")),
            end_year=_optional_int("endYear", payload.get("endYear")),
            runtime_minutes=_optional_int("runtimeMinutes", payload.get("runtimeMinutes")),
            genres=genres,
            synopsis=_optional_str("synopsis", payload.get("synopsis")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tconst": self.tconst,
            "titleType": self.title_type,
            "primaryTitle": self.primary_title,
            "originalTitle": self.original_title,
            "isAdult": self.is_adult,
            "startYear": self.start_year,
            "endYear": self.end_year,
            "runtimeMinutes": self.runtime_minutes,
            "genres": self.genres,
            "synopsis": self.synopsis,
        }
