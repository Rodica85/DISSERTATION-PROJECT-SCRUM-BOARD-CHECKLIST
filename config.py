"""Configuration settings for TravelAssistantAI."""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# LLM settings
MODEL_NAME = "llama3.2:3b"
TEMPERATURE = 0.3
MAX_TOKENS = 100

# UI settings
WINDOW_WIDTH = 520
WINDOW_HEIGHT = 820
WINDOW_TITLE = "Travel Desktop Assistant"

# Data paths
CSV_PATH = os.path.join(BASE_DIR, "questionnaire_responses.csv")
CHAT_LOGS_DIR = os.path.join(BASE_DIR, "chat_logs")

# Chat settings
MAX_HISTORY = 20
