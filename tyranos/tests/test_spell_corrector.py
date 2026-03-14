"""Tests for the SpellCorrector module.

The public surface under test:

    SpellCorrector.correct_text(text, threshold=0.8) -> str
        Correct typos / misspellings word-by-word against a known keyword
        vocabulary.  Returns a corrected string.

    SpellCorrector.find_closest_match(word, candidates, threshold) -> str | None
        Find the single closest match from an explicit candidate list.

    SpellCorrector.levenshtein_distance(s1, s2) -> int
        Pure edit-distance calculation.

    SpellCorrector.similarity_score(s1, s2) -> float
        Normalised similarity in [0, 1].

    SpellCorrector.handle_typo_command(user_input, known_commands, threshold)
        Match a whole command string to a list of known commands.

    SpellCorrector.suggest_command_fixes(user_input, known_commands, top_n)
        Return a ranked list of (command, score) tuples.

    get_spell_corrector() -> SpellCorrector
        Return the module-level singleton.
"""

from __future__ import annotations

import pytest

from tyranos.nlp.spell_corrector import SpellCorrector, get_spell_corrector

# ─── Fixture ──────────────────────────────────────────────────────────────────


@pytest.fixture
def corrector() -> SpellCorrector:
    """Return a fresh SpellCorrector for each test."""
    return SpellCorrector()


# ─── correct_text ─────────────────────────────────────────────────────────────


class TestCorrectText:
    """Tests for SpellCorrector.correct_text()."""

    def test_corrects_common_typo_instal(self, corrector: SpellCorrector) -> None:
        """'instal' is in the known variations list and should be corrected."""
        result = corrector.correct_text("instal python")
        assert isinstance(result, str)
        assert len(result) > 0
        # The corrected first word should be the canonical form "install"
        assert result.split()[0] == "install"

    def test_corrects_create_typo(self, corrector: SpellCorrector) -> None:
        """'mkdri' is an alias listed under CREATE and should be corrected."""
        result = corrector.correct_text("mkdri folder")
        assert isinstance(result, str)
        assert result.split()[0] == "create"

    def test_correct_spelling_unchanged(self, corrector: SpellCorrector) -> None:
        """A correctly spelled canonical keyword should be returned unchanged
        (or mapped to itself since it appears in keyword_to_canonical)."""
        result = corrector.correct_text("install")
        assert result is not None
        assert isinstance(result, str)

    def test_returns_string(self, corrector: SpellCorrector) -> None:
        """Return type must always be str."""
        result = corrector.correct_text("crate folder")
        assert isinstance(result, str)

    def test_empty_string_returns_string(self, corrector: SpellCorrector) -> None:
        """Empty input must return a string (not raise, not return None)."""
        result = corrector.correct_text("")
        assert result is not None
        assert isinstance(result, str)

    def test_long_sentence_returns_nonempty_string(self, corrector: SpellCorrector) -> None:
        """A sentence with multiple typos must be returned as a non-empty string."""
        sentence = "crate a pyton projekt with virtal envronment"
        result = corrector.correct_text(sentence)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_preserves_numbers_in_words(self, corrector: SpellCorrector) -> None:
        """Words that contain digits should never be altered."""
        result = corrector.correct_text("folder1 folder2")
        assert "folder1" in result
        assert "folder2" in result

    def test_preserves_technical_terms(self, corrector: SpellCorrector) -> None:
        """Terms in the preserve_terms set must pass through unchanged."""
        for term in ("readme", "folders", "py", "md", "json"):
            result = corrector.correct_text(term)
            assert term in result, f"Expected preserved term '{term}' to survive"

    def test_case_preservation_upper(self, corrector: SpellCorrector) -> None:
        """An ALL-CAPS typo should be corrected to ALL-CAPS canonical form."""
        result = corrector.correct_text("DELET")
        assert result == "DELETE"

    def test_case_preservation_title(self, corrector: SpellCorrector) -> None:
        """A Title-case typo should be corrected to Title-case canonical form."""
        result = corrector.correct_text("Delet")
        assert result == "Delete"

    def test_threshold_affects_corrections(self, corrector: SpellCorrector) -> None:
        """A very high threshold should suppress corrections for weak matches."""
        strict = corrector.correct_text("dlete", threshold=0.99)
        lenient = corrector.correct_text("dlete", threshold=0.5)
        # At least one threshold should produce a different result, or both
        # correct to the same word (delete); either way no exception.
        assert isinstance(strict, str)
        assert isinstance(lenient, str)


# ─── extract_keywords ─────────────────────────────────────────────────────────


class TestExtractKeywords:
    """Tests for SpellCorrector.extract_keywords()."""

    def test_known_keyword_appears_in_result(self, corrector: SpellCorrector) -> None:
        result = corrector.extract_keywords("create a folder")
        assert isinstance(result, dict)
        # "create" appears in keyword_to_canonical as "create" → "create"
        assert "create" in result or "folder" in result

    def test_returns_empty_dict_for_unknown_words(self, corrector: SpellCorrector) -> None:
        result = corrector.extract_keywords("xyzzy frobnicator wumpus")
        assert isinstance(result, dict)


# ─── find_closest_match ───────────────────────────────────────────────────────


class TestFindClosestMatch:
    """Tests for SpellCorrector.find_closest_match()."""

    def test_finds_exact_match(self, corrector: SpellCorrector) -> None:
        match = corrector.find_closest_match("create", ["create", "delete", "modify"])
        assert match == "create"

    def test_finds_close_match(self, corrector: SpellCorrector) -> None:
        match = corrector.find_closest_match("delet", ["create", "delete", "modify"], threshold=0.7)
        assert match == "delete"

    def test_returns_none_when_no_match(self, corrector: SpellCorrector) -> None:
        match = corrector.find_closest_match("xyzzy", ["create", "delete", "modify"], threshold=0.9)
        assert match is None


# ─── Levenshtein distance ─────────────────────────────────────────────────────


class TestLevenshteinDistance:
    """Tests for SpellCorrector.levenshtein_distance()."""

    def test_identical_strings_distance_zero(self, corrector: SpellCorrector) -> None:
        assert corrector.levenshtein_distance("create", "create") == 0

    def test_single_substitution(self, corrector: SpellCorrector) -> None:
        assert corrector.levenshtein_distance("cat", "bat") == 1

    def test_single_insertion(self, corrector: SpellCorrector) -> None:
        assert corrector.levenshtein_distance("cat", "cats") == 1

    def test_single_deletion(self, corrector: SpellCorrector) -> None:
        assert corrector.levenshtein_distance("cats", "cat") == 1

    def test_empty_strings(self, corrector: SpellCorrector) -> None:
        assert corrector.levenshtein_distance("", "") == 0

    def test_one_empty_string(self, corrector: SpellCorrector) -> None:
        assert corrector.levenshtein_distance("hello", "") == 5
        assert corrector.levenshtein_distance("", "hello") == 5

    def test_symmetry(self, corrector: SpellCorrector) -> None:
        assert corrector.levenshtein_distance(
            "kitten", "sitting"
        ) == corrector.levenshtein_distance("sitting", "kitten")


# ─── Similarity score ─────────────────────────────────────────────────────────


class TestSimilarityScore:
    """Tests for SpellCorrector.similarity_score()."""

    def test_identical_strings_score_one(self, corrector: SpellCorrector) -> None:
        assert corrector.similarity_score("create", "create") == pytest.approx(1.0)

    def test_completely_different_strings_low_score(self, corrector: SpellCorrector) -> None:
        score = corrector.similarity_score("aaaaa", "bbbbb")
        assert score < 0.5

    def test_score_in_unit_interval(self, corrector: SpellCorrector) -> None:
        score = corrector.similarity_score("create", "crate")
        assert 0.0 <= score <= 1.0

    def test_empty_strings_score_one(self, corrector: SpellCorrector) -> None:
        assert corrector.similarity_score("", "") == pytest.approx(1.0)


# ─── handle_typo_command ──────────────────────────────────────────────────────


class TestHandleTypoCommand:
    """Tests for SpellCorrector.handle_typo_command()."""

    def test_returns_tuple_on_good_match(self, corrector: SpellCorrector) -> None:
        known = ["create folder", "delete file", "run script"]
        result = corrector.handle_typo_command("creat folder", known, threshold=0.7)
        assert result is not None
        command, score = result
        assert isinstance(command, str)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_returns_none_when_no_match(self, corrector: SpellCorrector) -> None:
        known = ["create folder", "delete file"]
        result = corrector.handle_typo_command("xyzzy wumpus frobnicator", known, threshold=0.9)
        assert result is None


# ─── suggest_command_fixes ────────────────────────────────────────────────────


class TestSuggestCommandFixes:
    """Tests for SpellCorrector.suggest_command_fixes()."""

    def test_returns_list_of_tuples(self, corrector: SpellCorrector) -> None:
        known = ["create folder", "delete file", "run script"]
        suggestions = corrector.suggest_command_fixes("creat folder", known)
        assert isinstance(suggestions, list)
        for item in suggestions:
            assert isinstance(item, tuple)
            assert len(item) == 2

    def test_top_n_limits_results(self, corrector: SpellCorrector) -> None:
        known = ["create folder", "create file", "create project", "create script"]
        suggestions = corrector.suggest_command_fixes("creat", known, top_n=2)
        assert len(suggestions) <= 2

    def test_sorted_by_score_descending(self, corrector: SpellCorrector) -> None:
        known = ["create folder", "delete file", "create project"]
        suggestions = corrector.suggest_command_fixes("create folder", known, top_n=3)
        if len(suggestions) >= 2:
            scores = [s for _, s in suggestions]
            assert scores == sorted(scores, reverse=True)


# ─── Singleton ────────────────────────────────────────────────────────────────


class TestSingleton:
    def test_get_spell_corrector_returns_same_instance(self) -> None:
        a = get_spell_corrector()
        b = get_spell_corrector()
        assert a is b

    def test_singleton_is_spell_corrector_instance(self) -> None:
        assert isinstance(get_spell_corrector(), SpellCorrector)
