# TravelAssistantAI

BSc Computing Dissertation Project — Rodica Musteata (2026)

## About

A controlled research experiment that tests how three chatbot communication styles (Empathetic, Neutral, Non-Empathetic) affect user perception, emotional trust, and data privacy concerns during travel planning interactions.

## Tech Stack

- **Python 3.10+**
- **Flet** — Desktop UI framework
- **Ollama** — Local LLM inference (llama3.2:3b)

## Prerequisites

1. Install [Ollama](https://ollama.com)
2. Pull the required model:
   ```bash
   ollama pull llama3.2:3b
   ```
3. Make sure Ollama is running:
   ```bash
   ollama serve
   ```

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

## Experiment Flow

1. Participant reads study information and gives informed consent
2. Randomly assigned one of 3 communication tones
3. Chatbot asks 10 sequential travel planning questions
4. Bot provides 3 destination recommendations
5. Participant completes a 6-question Likert scale questionnaire
6. Anonymous responses saved to CSV

## Data Files

- `questionnaire_responses.csv` — Likert scale survey responses
- `chat_logs/` — Timestamped conversation transcripts (JSON)

## Project Structure

```
TravelAssistantAI/
├── app.py              # Main application
├── config.py           # Configuration settings
├── prompts.py          # System prompts for 3 tones
├── analysis.py         # Statistical analysis script
├── requirements.txt    # Python dependencies
├── chat_logs/          # Saved conversation transcripts
├── questionnaire_responses.csv
└── tests/
    └── test_core.py    # Unit tests
```
