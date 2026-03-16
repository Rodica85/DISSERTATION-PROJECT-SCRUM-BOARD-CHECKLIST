"""TravelAssistantAI - Main application for the travel chatbot research experiment."""

import asyncio
import csv
import json
import os
import random
import time
import uuid
from datetime import datetime, timezone

import flet as ft
import ollama
import threading

from prompts import EMPATHETIC_PROMPT, NEUTRAL_PROMPT, NON_EMPATHETIC_PROMPT
from config import (
    MODEL_NAME, TEMPERATURE, MAX_TOKENS,
    WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE,
    CSV_PATH, CHAT_LOGS_DIR, MAX_HISTORY,
)


def append_response(bot_tone: str, q1, q2, q3, q4, q5, q6, comments, session_id=""):
    """Write a questionnaire response row to the CSV file."""
    file_exists = os.path.isfile(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(
                [
                    "timestamp",
                    "session_id",
                    "bot_tone",
                    "q1_understanding",
                    "q2_care",
                    "q3_trust_info",
                    "q4_human_like",
                    "q5_privacy_confidence",
                    "q6_satisfaction",
                    "comments",
                ]
            )
        writer.writerow(
            [
                datetime.now(timezone.utc).isoformat(),
                session_id,
                bot_tone,
                q1,
                q2,
                q3,
                q4,
                q5,
                q6,
                (comments or "").replace("\n", " "),
            ]
        )


def save_chat_transcript(session_id: str, tone_label: str, chat_history: list,
                         start_time: float, turn_count: int):
    """Save conversation transcript as a JSON file in chat_logs/."""
    os.makedirs(CHAT_LOGS_DIR, exist_ok=True)
    end_time = time.time()
    transcript = {
        "session_id": session_id,
        "bot_tone": tone_label,
        "start_time": datetime.fromtimestamp(start_time).isoformat(),
        "end_time": datetime.fromtimestamp(end_time).isoformat(),
        "duration_seconds": round(end_time - start_time, 1),
        "turn_count": turn_count,
        "messages": [
            msg for msg in chat_history if msg["role"] != "system"
        ],
    }
    filename = f"{session_id}.json"
    filepath = os.path.join(CHAT_LOGS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(transcript, f, indent=2, ensure_ascii=False)


def create_message_bubble(text: str, is_user: bool, text_ref: ft.Ref[ft.Text] = None) -> ft.Container:
    """Create a styled chat message bubble."""
    text_control = ft.Text(
        text,
        selectable=True,
        color=ft.Colors.WHITE if is_user else ft.Colors.BLACK87,
        ref=text_ref,
    )
    return ft.Container(
        content=text_control,
        padding=12,
        margin=ft.Margin(
            left=60 if is_user else 0,
            right=0 if is_user else 60,
            top=0,
            bottom=0,
        ),
        bgcolor=ft.Colors.BLUE_ACCENT_700 if is_user else ft.Colors.GREY_200,
        border_radius=ft.BorderRadius.all(16),
        alignment=ft.Alignment(1, 0) if is_user else ft.Alignment(-1, 0),
    )


def main(page: ft.Page):
    """Main application entry point."""
    page.title = WINDOW_TITLE
    page.window_width = WINDOW_WIDTH
    page.window_height = WINDOW_HEIGHT

    # ---------- SELECT BOT TONE / SYSTEM PROMPT ----------
    def pick_tone():
        """Randomly select one of three communication styles."""
        return random.choice(
            [
                ("Empathetic", EMPATHETIC_PROMPT),
                ("Neutral", NEUTRAL_PROMPT),
                ("Non-Empathetic", NON_EMPATHETIC_PROMPT),
            ]
        )

    tone_label, system_prompt = pick_tone()

    # ---------- CHAT STATE ----------
    chat_history = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Hello"},
    ]

    def trim_history():
        nonlocal chat_history
        if len(chat_history) > MAX_HISTORY + 1:
            chat_history = [chat_history[0]] + chat_history[-MAX_HISTORY:]

    # Thread-safe state management
    state_lock = threading.Lock()
    is_processing = False
    stop_requested = threading.Event()
    questionnaire_started = False
    questionnaire_scroll_key = ft.ScrollKey("questionnaire_start")
    thank_you_scroll_key = ft.ScrollKey("thank_you_message")

    # Session metadata
    session_id = str(uuid.uuid4())[:8]
    session_start_time = time.time()
    turn_count = 0

    # ---------- UI ----------
    chat_list = ft.ListView(expand=True, spacing=12, auto_scroll=True, padding=20)
    user_input = ft.TextField(
        hint_text="Type your message...",
        expand=True,
        border_radius=25,
        content_padding=15,
    )

    def run_async(coro_func, *args):
        """Schedule a coroutine on the main event loop."""
        page.run_task(coro_func, *args)

    # ---------- ASYNC UI UPDATE FUNCTIONS (run on main thread) ----------
    async def update_bot_text(ref: ft.Ref[ft.Text], value: str):
        if ref.current:
            ref.current.value = value
            ref.current.update()
            await chat_list.scroll_to(offset=-1, duration=300)

    async def enable_input():
        user_input.disabled = False
        user_input.update()
        await user_input.focus()

    async def show_questionnaire():
        nonlocal questionnaire_started
        if questionnaire_started:
            return
        questionnaire_started = True

        # Save chat transcript before questionnaire
        save_chat_transcript(session_id, tone_label, chat_history,
                             session_start_time, turn_count)

        thank_you_message = (
            "Thank you for participating in this experiment!\n"
            "We truly appreciate the time you spent using the application. "
            "Your interaction helps us better understand how people experience and use AI-powered assistants.\n"
            "You will now be redirected to a short questionnaire about your experience with the app. "
            "Your feedback is very valuable and will help improve future versions of the system.\n"
            "Thank you again for your contribution!"
        )
        chat_list.controls.append(
            ft.Container(
                key=thank_you_scroll_key,
                content=create_message_bubble(thank_you_message, False),
            )
        )
        chat_list.update()
        await chat_list.scroll_to(offset=-1, duration=300)
        await asyncio.sleep(3)
        chat_list.auto_scroll = False

        def likert_group() -> ft.RadioGroup:
            return ft.RadioGroup(
                content=ft.Row(
                    [
                        ft.Radio(value="1", label="1", label_style=ft.TextStyle(color=ft.Colors.BLACK)),
                        ft.Radio(value="2", label="2", label_style=ft.TextStyle(color=ft.Colors.BLACK)),
                        ft.Radio(value="3", label="3", label_style=ft.TextStyle(color=ft.Colors.BLACK)),
                        ft.Radio(value="4", label="4", label_style=ft.TextStyle(color=ft.Colors.BLACK)),
                        ft.Radio(value="5", label="5", label_style=ft.TextStyle(color=ft.Colors.BLACK)),
                    ],
                    wrap=True,
                )
            )

        q1 = likert_group()
        q2 = likert_group()
        q3 = likert_group()
        q4 = likert_group()
        q5 = likert_group()
        q6 = likert_group()

        comments = ft.TextField(
            multiline=True,
            min_lines=2,
            max_lines=4,
            hint_text="Share any thoughts about your experience...",
            color=ft.Colors.BLACK,
            expand=True,
        )

        submit_button = ft.Button("Submit responses")
        form_feedback = ft.Text("", color=ft.Colors.BLACK)
        submit_popup_text = ft.Text(
            "Thank you. Your anonymous responses were recorded.",
            size=18,
            color=ft.Colors.BLACK,
        )
        submit_popup = ft.Container(
            content=submit_popup_text,
            bgcolor=ft.Colors.AMBER_200,
            border=ft.Border.all(1, ft.Colors.AMBER_400),
            border_radius=10,
            padding=12,
            alignment=ft.Alignment(0, 0),
            top=10,
            left=10,
            right=10,
            visible=False,
        )
        start_new_button = ft.Button(
            "Start new conversation",
            visible=False,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
        )
        start_new_button_container = ft.Container(
            content=start_new_button,
            top=20,
            left=10,
            visible=False,
        )
        page.overlay.append(submit_popup)
        page.overlay.append(start_new_button_container)
        start_new_button.on_click = start_new_conversation

        async def hide_submit_popup():
            await asyncio.sleep(15)
            submit_popup.visible = False
            submit_popup.update()

        def submit_questionnaire(e: ft.ControlEvent):
            answers = [q1.value, q2.value, q3.value, q4.value, q5.value, q6.value]
            if any(not value for value in answers):
                form_feedback.value = "Please answer questions 1-6 before submitting."
                form_feedback.color = ft.Colors.BLACK
                form_feedback.update()
                return

            append_response(
                tone_label,
                q1.value,
                q2.value,
                q3.value,
                q4.value,
                q5.value,
                q6.value,
                comments.value,
                session_id,
            )

            submit_button.disabled = True
            q1.disabled = True
            q2.disabled = True
            q3.disabled = True
            q4.disabled = True
            q5.disabled = True
            q6.disabled = True
            comments.disabled = True
            form_feedback.value = ""
            submit_popup.visible = True
            start_new_button_container.visible = True
            start_new_button.visible = True
            page.update()
            submit_popup.update()
            start_new_button_container.update()
            start_new_button.update()
            run_async(hide_submit_popup)

        submit_button.on_click = submit_questionnaire

        questionnaire_card = ft.Container(
            key=questionnaire_scroll_key,
            content=ft.Column(
                [
                    ft.Text("Anonymous Questionnaire", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                    ft.Text(
                        "Please answer these questions about your experience. Responses are anonymous.",
                        size=13,
                        color=ft.Colors.BLACK,
                    ),
                    ft.Text("1. The chatbot understood my concerns effectively", weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                    q1,
                    ft.Text("2. I felt the chatbot cared about helping me", weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                    q2,
                    ft.Text("3. I would trust this chatbot with my personal information", weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                    q3,
                    ft.Text("4. The chatbot's responses felt personalised and human-like", weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                    q4,
                    ft.Text("5. I felt confident the chatbot would protect my privacy", weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                    q5,
                    ft.Text("6. Overall, I was satisfied with this interaction", weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                    q6,
                    ft.Text("7. Any additional comments? (Optional)", weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                    comments,
                    submit_button,
                    form_feedback,
                ],
                spacing=8,
            ),
            bgcolor=ft.Colors.AMBER_50,
            border=ft.Border.all(1, ft.Colors.AMBER_200),
            border_radius=12,
            padding=12,
            margin=ft.Margin(0, 6, 0, 6),
        )

        chat_list.controls.append(questionnaire_card)
        chat_list.update()
        await asyncio.sleep(0.05)
        await chat_list.scroll_to(scroll_key=thank_you_scroll_key, duration=300)

    # ---------- OLLAMA STREAM (runs in background thread) ----------
    def run_ollama_stream(bot_text_ref: ft.Ref[ft.Text]):
        """Stream LLM response tokens and update UI in real-time."""
        nonlocal is_processing, turn_count
        tokens: list[str] = []
        final_response = ""

        try:
            stream = ollama.chat(
                model=MODEL_NAME,
                messages=chat_history,
                stream=True,
                options={"temperature": TEMPERATURE, "max_tokens": MAX_TOKENS},
            )

            for chunk in stream:
                if stop_requested.is_set():
                    break
                content = chunk.get("message", {}).get("content", "")
                if not content:
                    continue

                tokens.append(content)
                final_response = "".join(tokens)
                run_async(update_bot_text, bot_text_ref, final_response)

            if final_response:
                with state_lock:
                    chat_history.append({"role": "assistant", "content": final_response})
                    turn_count += 1
                trim_history()

        except ConnectionError:
            run_async(update_bot_text, bot_text_ref,
                      "Could not connect to Ollama. Please make sure it is running (ollama serve).")
        except Exception as ex:
            run_async(update_bot_text, bot_text_ref,
                      "Something went wrong. Please try starting a new conversation.")
            print(f"[Ollama error] {ex}")

        if stop_requested.is_set():
            with state_lock:
                is_processing = True
            return

        if "Now a survey about your experience should start" in final_response:
            with state_lock:
                is_processing = True
            run_async(show_questionnaire)
        else:
            run_async(enable_input)
            with state_lock:
                is_processing = False

    # ---------- SEND MESSAGE ----------
    def send_click(e):
        nonlocal is_processing
        with state_lock:
            if is_processing:
                return
            is_processing = True

        text = user_input.value.strip()
        if not text:
            with state_lock:
                is_processing = False
            return

        # Show user bubble
        chat_list.controls.append(create_message_bubble(text, True))
        chat_history.append({"role": "user", "content": text})
        chat_list.update()

        user_input.value = ""
        user_input.disabled = True
        page.update()

        bot_text_ref = ft.Ref[ft.Text]()
        chat_list.controls.append(create_message_bubble("Thinking...", False, text_ref=bot_text_ref))
        chat_list.update()

        threading.Thread(target=run_ollama_stream, args=(bot_text_ref,), daemon=True).start()

    def finish_click(e):
        nonlocal is_processing
        stop_requested.set()
        with state_lock:
            is_processing = True
        user_input.disabled = True
        send_button.disabled = True
        finish_button.disabled = True
        page.update()
        run_async(show_questionnaire)

    user_input.on_submit = send_click
    send_button = ft.IconButton(icon=ft.Icons.SEND_ROUNDED, on_click=send_click)
    finish_button = ft.IconButton(
        icon=ft.Icons.STOP_CIRCLE_ROUNDED,
        tooltip="Finish and open questionnaire",
        on_click=finish_click,
    )

    def start_new_conversation(e):
        nonlocal is_processing, chat_history, questionnaire_started, tone_label, system_prompt
        nonlocal session_id, session_start_time, turn_count
        stop_requested.clear()
        questionnaire_started = False
        is_processing = False
        tone_label, system_prompt = pick_tone()
        chat_list.controls.clear()
        page.overlay.clear()
        chat_history = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Hello"},
        ]
        # Reset session metadata
        session_id = str(uuid.uuid4())[:8]
        session_start_time = time.time()
        turn_count = 0

        user_input.disabled = False
        user_input.value = ""
        send_button.disabled = False
        finish_button.disabled = False
        page.update()
        start_conversation()

    # ---------- START CONVERSATION ----------
    def start_conversation():
        nonlocal is_processing
        if is_processing:
            return
        is_processing = True

        bot_text_ref = ft.Ref[ft.Text]()
        chat_list.controls.append(create_message_bubble("Loading...", False, text_ref=bot_text_ref))
        user_input.disabled = True
        chat_list.update()
        page.update()

        threading.Thread(target=run_ollama_stream, args=(bot_text_ref,), daemon=True).start()

    # ---------- WELCOME SCREEN ----------
    consent_checkbox = ft.Checkbox(
        label=(
            "I confirm that I am 18 years or older and I consent to participate in this research study.\n"
            "I understand this is a chatbot simulation, I can exit at any time, and my anonymous responses\n "
            "will be used for academic research purposes only."
        ),
        value=False,
    )
    start_button = ft.Button("Start study", disabled=True)

    def on_consent_change(e: ft.ControlEvent):
        start_button.disabled = not consent_checkbox.value
        start_button.update()

    consent_checkbox.on_change = on_consent_change

    def on_start_click(e: ft.ControlEvent):
        if not consent_checkbox.value:
            return
        welcome_view.visible = False
        chat_view.visible = True
        page.update()
        start_conversation()

    start_button.on_click = on_start_click

    welcome_view = ft.Column(
        [
            ft.Container(
                alignment=ft.Alignment(0, 0),
                content=ft.Column(
                    [
                        ft.Text(
                            "✈️ Travel Planning Assistant",
                            size=26,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "Academic Research Study - BSc Computing Dissertation",
                            size=14,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "🎓 Developed by Rodica - BSc Computing Dissertation - 2026",
                            size=11,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                expand=True,
            ),
            ft.Divider(),
            ft.Text("Participant Information", size=18, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=ft.Text(
                    "Purpose: This study explores how different communication styles in travel planning chatbots "
                    "influence user perception, emotional trust, and data privacy concerns.",
                    size=14,
                    color=ft.Colors.BLACK,
                ),
                bgcolor=ft.Colors.GREY_100,
                padding=12,
                border_radius=8,
                margin=ft.Margin(0, 12, 0, 12),
            ),
            ft.Text(
                "What you'll do: Have a conversation (8–12 minutes) with a travel planning assistant about your "
                "holiday preferences. The chatbot will ask questions about destinations, activities, budget, and "
                "travel style.",
                size=14,
            ),
            ft.Text("Important information:", size=14, weight=ft.FontWeight.BOLD),
            ft.Column(
                [
                    ft.Text("• This is a simulation for academic research purposes", size=14),
                    ft.Text(
                        "• No personal data (name, email, payment info) is collected",
                        size=14,
                    ),
                    ft.Text(
                        '• You can exit the conversation at ANY time using the "Finish" button',
                        size=14,
                    ),
                    ft.Text("• Your responses are completely anonymous", size=14),
                ],
                spacing=4,
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.START,
            ),
            ft.Container(height=12),
            consent_checkbox,
            ft.Container(height=8),
            start_button,
        ],
        alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.START,
        expand=True,
    )

    # ---------- CHAT VIEW ----------
    chat_view = ft.Column(
        [
            ft.Container(
                content=ft.Row(
                    [finish_button],
                    alignment=ft.MainAxisAlignment.END,
                ),
                padding=ft.Padding(left=10, top=10, right=10, bottom=0),
            ),
            ft.Container(chat_list, expand=True),
            ft.Divider(),
            ft.Container(ft.Row([user_input, send_button]), padding=10),
        ],
        expand=True,
        visible=False,
    )

    # ---------- LAYOUT ----------
    page.add(welcome_view, chat_view)


if __name__ == "__main__":
    ft.run(main)
