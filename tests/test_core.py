"""Unit tests for core TravelAssistantAI functionality."""

import csv
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Mock external dependencies that may not be installed in test environment
for mod_name in ["flet", "ollama"]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import append_response, save_chat_transcript
from prompts import EMPATHETIC_PROMPT, NEUTRAL_PROMPT, NON_EMPATHETIC_PROMPT


class TestPickTone(unittest.TestCase):
    """Test tone selection logic."""

    def test_all_tones_available(self):
        """All three prompts should be non-empty strings."""
        self.assertIsInstance(EMPATHETIC_PROMPT, str)
        self.assertIsInstance(NEUTRAL_PROMPT, str)
        self.assertIsInstance(NON_EMPATHETIC_PROMPT, str)
        self.assertTrue(len(EMPATHETIC_PROMPT) > 100)
        self.assertTrue(len(NEUTRAL_PROMPT) > 100)
        self.assertTrue(len(NON_EMPATHETIC_PROMPT) > 100)

    def test_prompts_contain_trigger_phrase(self):
        """All prompts must instruct the bot to include the survey trigger phrase."""
        trigger = "Now a survey about your experience should start"
        self.assertIn(trigger, EMPATHETIC_PROMPT)
        self.assertIn(trigger, NEUTRAL_PROMPT)
        self.assertIn(trigger, NON_EMPATHETIC_PROMPT)

    def test_prompts_contain_question_sequence(self):
        """All prompts should reference the 10-question sequence."""
        for prompt in [EMPATHETIC_PROMPT, NEUTRAL_PROMPT, NON_EMPATHETIC_PROMPT]:
            self.assertIn("climate", prompt.lower())
            self.assertIn("budget", prompt.lower())
            self.assertIn("duration", prompt.lower())


class TestAppendResponse(unittest.TestCase):
    """Test CSV response writing."""

    def test_creates_file_with_header(self):
        """Should create CSV with header row on first write."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            tmp_path = f.name

        os.unlink(tmp_path)  # Ensure file doesn't exist

        with patch("app.CSV_PATH", tmp_path):
            append_response("Empathetic", "5", "4", "3", "2", "1", "5", "Great!", "abc123")

        with open(tmp_path, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)

        self.assertEqual(rows[0][0], "timestamp")
        self.assertEqual(rows[0][1], "session_id")
        self.assertEqual(rows[0][2], "bot_tone")
        self.assertEqual(rows[1][2], "Empathetic")
        self.assertEqual(rows[1][3], "5")
        self.assertEqual(rows[1][9], "Great!")
        os.unlink(tmp_path)

    def test_appends_without_duplicate_header(self):
        """Second write should not duplicate header."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            tmp_path = f.name

        os.unlink(tmp_path)

        with patch("app.CSV_PATH", tmp_path):
            append_response("Neutral", "1", "2", "3", "4", "5", "3", "", "sess1")
            append_response("Empathetic", "5", "5", "5", "5", "5", "5", "Good", "sess2")

        with open(tmp_path, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)

        self.assertEqual(len(rows), 3)  # 1 header + 2 data rows
        os.unlink(tmp_path)

    def test_newlines_removed_from_comments(self):
        """Comments with newlines should have them replaced with spaces."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            tmp_path = f.name

        os.unlink(tmp_path)

        with patch("app.CSV_PATH", tmp_path):
            append_response("Neutral", "1", "2", "3", "4", "5", "3", "line1\nline2", "sess1")

        with open(tmp_path, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)

        self.assertNotIn("\n", rows[1][9])
        os.unlink(tmp_path)


class TestSaveChatTranscript(unittest.TestCase):
    """Test chat transcript saving."""

    def test_saves_json_transcript(self):
        """Should save a valid JSON file with session metadata."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("app.CHAT_LOGS_DIR", tmp_dir):
                import time
                start = time.time()
                history = [
                    {"role": "system", "content": "You are a bot."},
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there!"},
                ]
                save_chat_transcript("test123", "Empathetic", history, start, 1)

                filepath = os.path.join(tmp_dir, "test123.json")
                self.assertTrue(os.path.exists(filepath))

                with open(filepath, "r") as f:
                    data = json.load(f)

                self.assertEqual(data["session_id"], "test123")
                self.assertEqual(data["bot_tone"], "Empathetic")
                self.assertEqual(data["turn_count"], 1)
                # System messages should be filtered out
                self.assertEqual(len(data["messages"]), 2)
                self.assertEqual(data["messages"][0]["role"], "user")


class TestConfig(unittest.TestCase):
    """Test configuration values."""

    def test_config_values(self):
        from config import MODEL_NAME, TEMPERATURE, MAX_TOKENS, MAX_HISTORY
        self.assertEqual(MODEL_NAME, "llama3.2:3b")
        self.assertGreater(TEMPERATURE, 0)
        self.assertLessEqual(TEMPERATURE, 1)
        self.assertGreater(MAX_TOKENS, 0)
        self.assertGreater(MAX_HISTORY, 0)


if __name__ == "__main__":
    unittest.main()
