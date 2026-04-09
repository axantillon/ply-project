from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from imdb_parser.parser import MovieParseError, parse_movie_json, parse_movie_json_raw


class ParserTests(unittest.TestCase):
    def test_parse_valid_movie_file_into_movie_object(self) -> None:
        sample = (ROOT / "samples" / "sample1.json").read_text(encoding="utf-8")

        movie = parse_movie_json(sample)

        self.assertEqual(movie.tconst, "tt0133093")
        self.assertEqual(movie.primary_title, "The Matrix")
        self.assertEqual(movie.start_year, 1999)
        self.assertEqual(movie.genres, ["Action", "Sci-Fi"])
        self.assertIn("simulation", movie.synopsis or "")

    def test_parse_raw_json_preserves_nested_json_values(self) -> None:
        text = """
        {
          "tconst": "tt9999999",
          "titleType": "movie",
          "primaryTitle": "Nested Example",
          "genres": ["Drama"],
          "extra": {
            "rating": 8.5,
            "flags": [true, false, null, -3, 1.2e3],
            "label": "Caf\\u00e9"
          }
        }
        """

        payload = parse_movie_json_raw(text)

        self.assertEqual(payload["extra"]["rating"], 8.5)
        self.assertEqual(payload["extra"]["flags"], [True, False, None, -3, 1200.0])
        self.assertEqual(payload["extra"]["label"], "Café")

    def test_invalid_schema_raises_parse_error(self) -> None:
        invalid = (ROOT / "samples" / "invalid_sample.json").read_text(encoding="utf-8")

        with self.assertRaises(MovieParseError) as context:
            parse_movie_json(invalid)

        self.assertIn("genres", str(context.exception))

    def test_missing_required_field_raises_parse_error(self) -> None:
        text = """
        {
          "tconst": "tt1111111",
          "titleType": "movie",
          "genres": ["Drama"]
        }
        """

        with self.assertRaises(MovieParseError) as context:
            parse_movie_json(text)

        self.assertIn("Missing required field", str(context.exception))

    def test_malformed_json_raises_parse_error(self) -> None:
        text = """
        {
          "tconst": "tt1111111",
          "titleType": "movie",
          "primaryTitle": "Broken",
          "genres": ["Drama",]
        }
        """

        with self.assertRaises(MovieParseError):
            parse_movie_json(text)


if __name__ == "__main__":
    unittest.main()
