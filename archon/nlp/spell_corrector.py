#!/usr/bin/env python3
"""
Spell Correction & Typo Tolerance Module for Archon
Handles fuzzy matching for commands, keywords, and user input
Uses Levenshtein distance and fuzzy matching
"""

from difflib import get_close_matches

from ..utils.logger import get_logger


class SpellCorrector:
    """Intelligent spell correction with fuzzy matching"""

    def __init__(self):
        self.logger = get_logger("SpellCorrector")

        # Technical terms to NEVER correct
        self.preserve_terms = {
            "readme",
            "folders",
            "folder1",
            "folder2",
            "subfolders",
            "numbered",
            "naming",
            "inside",
            "within",
            "each",
            "txt",
            "md",
            "py",
            "js",
            "html",
            "css",
            "json",
        }

        # Command keywords and their *misspellings* only.
        #
        # These lists must contain the canonical word plus genuine typos — never
        # valid synonyms. correct_text() rewrites any listed variation to the
        # canonical, so putting real words here (e.g. "document" → "file",
        # "get" → "download") silently corrupts the user's meaning and produces
        # nonsense like "write a doc file" → "write a file file". Synonym →
        # intent mapping is the NLP classifier's job, not the spell corrector's.
        self.command_keywords = {
            "create": ["create", "mkdri"],
            "delete": ["delete", "delet", "dlete"],
            "copy": ["copy", "copi", "copu"],
            "move": ["move", "moev", "muve"],
            "rename": ["rename", "renam", "renme"],
            "folder": ["folder", "fodler", "foldr"],
            "file": ["file", "flie", "fil"],
            "project": ["project", "projeect", "prject"],
            "test": ["test", "tst", "tess", "tesst"],
            "run": ["run", "runn"],
            "install": ["install", "instal", "instll"],
            "download": ["download", "dwld", "downlaod"],
            "upload": ["upload", "upld", "uplod"],
            "web": ["web", "weeb", "wbe"],
            "automation": ["automation", "automtion", "automatoin"],
            "script": ["script", "scirpt", "skript"],
            "configure": ["configure", "configue", "configre"],
            "monitor": ["monitor", "moniter", "montior"],
        }

        # Flatten the dictionary for reverse lookup
        self.keyword_to_canonical = {}
        for canonical, variations in self.command_keywords.items():
            for variation in variations:
                self.keyword_to_canonical[variation.lower()] = canonical

    def correct_text(self, text: str, threshold: float = 0.8) -> str:
        """
        Correct typos and grammatical errors in text

        Args:
            text: Input text to correct
            threshold: Fuzzy match threshold (0-1)

        Returns:
            Corrected text
        """
        words = text.split()
        corrected = []

        for word in words:
            # Try to find canonical form for this word
            corrected_word = self._correct_word(word, threshold)
            corrected.append(corrected_word)

        return " ".join(corrected)

    def _correct_word(self, word: str, threshold: float) -> str:
        """Correct a single word"""
        word_lower = word.lower()

        # Never correct words with numbers
        if any(c.isdigit() for c in word):
            return word

        # Never correct preserved technical terms
        if word_lower in self.preserve_terms:
            return word

        # Exact match
        if word_lower in self.keyword_to_canonical:
            canonical = self.keyword_to_canonical[word_lower]
            # Preserve case
            if word.isupper():
                return canonical.upper()
            elif word[0].isupper():
                return canonical.capitalize()
            return canonical

        # Fuzzy match — but only accept it when the word really looks like a
        # typo of the keyword, not a different valid word that happens to be
        # somewhat similar. Without this guard, get_close_matches maps real
        # words to keywords ("latest" → "test", "kconfig" → "configure"),
        # corrupting the user's meaning. Requiring the same first letter and a
        # small length delta keeps genuine typos (crate→create, projekt→project)
        # while rejecting distinct words.
        matches = get_close_matches(
            word_lower, self.keyword_to_canonical.keys(), n=1, cutoff=threshold
        )
        if matches:
            candidate = matches[0]
            same_start = candidate[:1] == word_lower[:1]
            close_length = abs(len(candidate) - len(word_lower)) <= 2
            if same_start and close_length:
                canonical = self.keyword_to_canonical[candidate]
                if word.isupper():
                    return canonical.upper()
                elif word[0].isupper():
                    return canonical.capitalize()
                return canonical

        return word

    def extract_keywords(self, text: str) -> dict[str, str]:
        """
        Extract and correct keywords from text

        Returns:
            Dictionary mapping keyword types to corrected values
        """
        keywords = {}
        words = text.lower().split()

        for word in words:
            if word in self.keyword_to_canonical:
                canonical = self.keyword_to_canonical[word]
                keywords[canonical] = word

        return keywords

    def find_closest_match(
        self, word: str, candidates: list[str], threshold: float = 0.7
    ) -> str | None:
        """Find closest match from a list of candidates"""
        matches = get_close_matches(word, candidates, n=1, cutoff=threshold)
        return matches[0] if matches else None

    def levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def similarity_score(self, s1: str, s2: str) -> float:
        """Calculate similarity score between two strings (0-1)"""
        distance = self.levenshtein_distance(s1.lower(), s2.lower())
        max_len = max(len(s1), len(s2))
        return 1 - (distance / max_len) if max_len > 0 else 1.0

    def handle_typo_command(
        self, user_input: str, known_commands: list[str], threshold: float = 0.75
    ) -> tuple[str, float] | None:
        """
        Find the closest command if user input has typos

        Returns:
            Tuple of (corrected_command, confidence_score) or None
        """
        best_match = None
        best_score = 0

        for command in known_commands:
            score = self.similarity_score(user_input, command)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = command

        return (best_match, best_score) if best_match else None

    def suggest_command_fixes(
        self, user_input: str, known_commands: list[str], top_n: int = 3
    ) -> list[tuple[str, float]]:
        """
        Suggest multiple command fixes

        Returns:
            List of (command, score) tuples sorted by score
        """
        suggestions = []

        for command in known_commands:
            score = self.similarity_score(user_input, command)
            if score > 0.5:  # Only include reasonable matches
                suggestions.append((command, score))

        return sorted(suggestions, key=lambda x: x[1], reverse=True)[:top_n]


# Global instance
_spell_corrector = None


def get_spell_corrector() -> SpellCorrector:
    """Get or create global spell corrector instance"""
    global _spell_corrector
    if _spell_corrector is None:
        _spell_corrector = SpellCorrector()
    return _spell_corrector
