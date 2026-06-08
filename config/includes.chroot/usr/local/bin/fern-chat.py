#!/usr/bin/env python3
"""
fern-chat.py — FernOS AI Chat
A fully agentic local AI assistant with system-level access.
Talks to Ollama via REST API. Built with GTK4.
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gdk, Pango

import os
import sys
import json
import time
import shlex
import threading
import subprocess
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# ─── Config ───────────────────────────────────────────────
OLLAMA_URL      = "http://localhost:11434"
HISTORY_FILE    = Path.home() / ".local" / "share" / "fernos" / "chat_history.json"
PREFS_FILE      = Path.home() / ".local" / "share" / "fernos" / "chat_prefs.json"
SETUP_SCRIPT    = "/usr/local/bin/fern-model-setup.sh"
APP_NAME        = "Fern AI Chat"
APP_VERSION     = "0.1.0"

# Destructive command patterns that trigger the confirm dialog
DESTRUCTIVE_PATTERNS = [
    "rm ", "rmdir", "shred", "dd ", "mkfs",
    "apt remove", "apt purge", "apt autoremove",
    "> /",   # overwrite via redirect
    "chmod 000", "chown root",
    "mv /home", "mv /etc", "mv /usr",
    "systemctl stop", "systemctl disable", "kill ", "killall",
    "sudo rm", "sudo dd", ":(){:|:&};:",  # fork bomb
]

# System prompt given to the model
SYSTEM_PROMPT = """You are Fern, the built-in AI assistant for FernOS — a Debian-based Linux distribution.
You have full access to the user's system and can run any shell command to help them.

When you need to run a command, output it in this exact format on its own line:
  <RUN>command here</RUN>

Rules:
- You may chain multiple <RUN> blocks in one response to complete multi-step tasks.
- After each <RUN> block is executed, you will receive the output as a new message starting with [RESULT].
- If a task requires many steps (sorting files, installing software, reorganising directories), continue issuing <RUN> blocks until the task is fully complete.
- You have sudo access. Use it when necessary.
- You have internet access. Use curl or wget to fetch information when needed.
- Be direct and practical. Explain what you're doing in plain language, not corporate speak.
- When something fails, read the error output and try again with a corrected command.
- Never refuse a system task — the user owns this machine.
- After completing a task, give a short summary of what was done.
"""


# ─── GTK4 CSS ─────────────────────────────────────────────
CSS = b"""
window, .background {
    background-color: #0d1a0e;
}

.fern-sidebar {
    background: rgba(20, 38, 20, 0.95);
    border-right: 1px solid rgba(255,255,255,0.08);
}

.fern-header {
    background: rgba(15, 28, 15, 0.98);
    border-bottom: 1px solid rgba(255,255,255,0.08);
    padding: 10px 16px;
    min-height: 52px;
}

.fern-logo {
    font-family: "DM Sans", "Cantarell", sans-serif;
    font-size: 1.1em;
    font-weight: 600;
    color: #ffffff;
}

.fern-logo-accent {
    color: #b8f0a0;
}

.fern-model-badge {
    font-family: "DM Mono", "Monospace", monospace;
    font-size: 0.7em;
    color: rgba(184,240,160,0.7);
    background: rgba(184,240,160,0.08);
    border: 1px solid rgba(184,240,160,0.2);
    border-radius: 99px;
    padding: 2px 10px;
}

.fern-chat-scroll {
    background: transparent;
}

.fern-chat-area {
    background: transparent;
    padding: 16px;
}

.fern-bubble-user {
    background: rgba(184, 240, 160, 0.12);
    border: 1px solid rgba(184,240,160,0.25);
    border-radius: 14px 14px 4px 14px;
    padding: 10px 14px;
    color: #ffffff;
    font-family: "DM Sans", "Cantarell", sans-serif;
    font-size: 0.95em;
}

.fern-bubble-ai {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 14px 14px 14px 4px;
    padding: 10px 14px;
    color: #e8f5e0;
    font-family: "DM Sans", "Cantarell", sans-serif;
    font-size: 0.95em;
}

.fern-bubble-tool {
    background: rgba(10, 20, 10, 0.7);
    border: 1px solid rgba(184,240,160,0.15);
    border-radius: 8px;
    padding: 8px 12px;
    font-family: "DM Mono", "Monospace", monospace;
    font-size: 0.78em;
    color: #a0c890;
}

.fern-bubble-result {
    background: rgba(10, 20, 10, 0.5);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 8px;
    padding: 8px 12px;
    font-family: "DM Mono", "Monospace", monospace;
    font-size: 0.75em;
    color: rgba(200,230,190,0.8);
}

.fern-sender-label {
    font-family: "DM Mono", "Monospace", monospace;
    font-size: 0.65em;
    color: rgba(255,255,255,0.35);
    margin-bottom: 4px;
}

.fern-input-bar {
    background: rgba(20, 38, 20, 0.98);
    border-top: 1px solid rgba(255,255,255,0.08);
    padding: 12px 16px;
}

.fern-input {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 12px;
    color: #ffffff;
    font-family: "DM Sans", "Cantarell", sans-serif;
    font-size: 0.95em;
    padding: 10px 14px;
}

.fern-input:focus {
    border-color: rgba(184,240,160,0.5);
    box-shadow: 0 0 0 2px rgba(125,234,106,0.1);
}

.fern-send-btn {
    background: rgba(184,240,160,0.14);
    border: 1px solid rgba(184,240,160,0.4);
    border-radius: 10px;
    color: #b8f0a0;
    font-family: "DM Mono", "Monospace", monospace;
    font-size: 0.8em;
    padding: 8px 16px;
    min-width: 64px;
}

.fern-send-btn:hover {
    background: rgba(125,234,106,0.22);
    color: #ffffff;
}

.fern-send-btn:disabled {
    opacity: 0.35;
}

.fern-history-btn {
    background: transparent;
    border: none;
    border-radius: 8px;
    color: rgba(255,255,255,0.5);
    font-family: "DM Sans", "Cantarell", sans-serif;
    font-size: 0.82em;
    padding: 6px 10px;
    text-align: left;
}

.fern-history-btn:hover {
    background: rgba(184,240,160,0.08);
    color: #ffffff;
}

.fern-history-active {
    background: rgba(184,240,160,0.12);
    color: #b8f0a0;
}

.fern-new-btn {
    background: rgba(184,240,160,0.1);
    border: 1px solid rgba(184,240,160,0.25);
    border-radius: 8px;
    color: #b8f0a0;
    font-family: "DM Mono", "Monospace", monospace;
    font-size: 0.75em;
    padding: 6px 12px;
    margin: 8px;
}

.fern-new-btn:hover {
    background: rgba(184,240,160,0.18);
}

.fern-confirm-bar {
    background: rgba(30, 20, 0, 0.95);
    border: 1px solid rgba(255,200,80,0.3);
    border-radius: 10px;
    padding: 10px 14px;
    margin: 4px 16px;
}

.fern-confirm-label {
    font-family: "DM Mono", "Monospace", monospace;
    font-size: 0.78em;
    color: rgba(255,220,120,0.9);
}

.fern-confirm-run-btn {
    background: rgba(255,200,80,0.12);
    border: 1px solid rgba(255,200,80,0.35);
    border-radius: 7px;
    color: #ffd878;
    font-family: "DM Mono", "Monospace", monospace;
    font-size: 0.72em;
    padding: 5px 12px;
}

.fern-confirm-run-btn:hover {
    background: rgba(255,200,80,0.22);
}

.fern-confirm-ignore-btn {
    background: transparent;
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 7px;
    color: rgba(255,255,255,0.5);
    font-family: "DM Mono", "Monospace", monospace;
    font-size: 0.72em;
    padding: 5px 12px;
}

.fern-confirm-ignore-btn:hover {
    background: rgba(255,255,255,0.06);
    color: #ffffff;
}

.fern-typing {
    font-family: "DM Mono", "Monospace", monospace;
    font-size: 0.78em;
    color: rgba(184,240,160,0.5);
    padding: 4px 16px;
}

.fern-sidebar-label {
    font-family: "DM Mono", "Monospace", monospace;
    font-size: 0.62em;
    color: rgba(255,255,255,0.25);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    padding: 12px 12px 4px 12px;
}
"""


# ─── Ollama API ───────────────────────────────────────────
class OllamaClient:
    def __init__(self, base_url=OLLAMA_URL):
        self.base_url = base_url

    def is_running(self):
        try:
            urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=2)
            return True
        except:
            return False

    def list_models(self):
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=5) as r:
                data = json.loads(r.read())
                return [m["name"] for m in data.get("models", [])]
        except:
            return []

    def chat_stream(self, model, messages, on_chunk, on_done):
        """Stream a chat response. Calls on_chunk(text) for each token, on_done() when finished."""
        payload = json.dumps({
            "model": model,
            "messages": messages,
            "stream": True,
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req) as resp:
                for raw_line in resp:
                    line = raw_line.decode().strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            on_chunk(content)
                        if chunk.get("done"):
                            on_done()
                            return
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            on_chunk(f"\n[Error communicating with Ollama: {e}]")
            on_done()


# ─── Tool executor ────────────────────────────────────────
class ToolExecutor:
    def __init__(self):
        self.ignore_all_destructive = False

    def is_destructive(self, cmd):
        if self.ignore_all_destructive:
            return False
        cmd_lower = cmd.lower()
        return any(p in cmd_lower for p in DESTRUCTIVE_PATTERNS)

    def run(self, cmd, timeout=60):
        """Run a shell command and return (stdout, stderr, returncode)."""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"},
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", f"Command timed out after {timeout}s", 1
        except Exception as e:
            return "", str(e), 1


# ─── History ──────────────────────────────────────────────
class ChatHistory:
    def __init__(self):
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.sessions = self._load()

    def _load(self):
        if HISTORY_FILE.exists():
            try:
                return json.loads(HISTORY_FILE.read_text())
            except:
                pass
        return []

    def save(self):
        HISTORY_FILE.write_text(json.dumps(self.sessions, indent=2))

    def new_session(self):
        session = {
            "id": str(time.time()),
            "title": "New chat",
            "created": datetime.now().isoformat(),
            "messages": [],
        }
        self.sessions.insert(0, session)
        self.save()
        return session

    def update_session(self, session):
        for i, s in enumerate(self.sessions):
            if s["id"] == session["id"]:
                self.sessions[i] = session
                break
        self.save()

    def delete_session(self, session_id):
        self.sessions = [s for s in self.sessions if s["id"] != session_id]
        self.save()


# ─── Prefs ────────────────────────────────────────────────
class Prefs:
    def __init__(self):
        PREFS_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self):
        if PREFS_FILE.exists():
            try:
                return json.loads(PREFS_FILE.read_text())
            except:
                pass
        return {"model": None}

    def save(self):
        PREFS_FILE.write_text(json.dumps(self.data, indent=2))

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()


# ─── Main Window ──────────────────────────────────────────
class FernChatWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title(APP_NAME)
        self.set_default_size(1000, 680)

        self.ollama = OllamaClient()
        self.executor = ToolExecutor()
        self.history = ChatHistory()
        self.prefs = Prefs()

        self.current_session = None
        self.ollama_messages = []   # messages sent to ollama (with system prompt)
        self.is_thinking = False
        self.current_ai_label = None
        self.current_ai_text = ""
        self.pending_command = None  # waiting for user confirm

        self._build_ui()
        self._apply_css()
        self._check_ollama()

    # ── UI construction ───────────────────────────────────
    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_content(root)

        # Sidebar
        sidebar = self._build_sidebar()
        root.append(sidebar)

        # Main area
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main.set_hexpand(True)
        root.append(main)

        # Header
        header = self._build_header()
        main.append(header)

        # Chat scroll area
        self.chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.chat_box.add_css_class("fern-chat-area")

        scroll = Gtk.ScrolledWindow()
        scroll.add_css_class("fern-chat-scroll")
        scroll.set_vexpand(True)
        scroll.set_child(self.chat_box)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll = scroll
        main.append(scroll)

        # Typing indicator
        self.typing_label = Gtk.Label(label="Fern is thinking...")
        self.typing_label.add_css_class("fern-typing")
        self.typing_label.set_halign(Gtk.Align.START)
        self.typing_label.set_visible(False)
        main.append(self.typing_label)

        # Confirm bar (hidden until needed)
        self.confirm_bar = self._build_confirm_bar()
        self.confirm_bar.set_visible(False)
        main.append(self.confirm_bar)

        # Input bar
        input_bar = self._build_input_bar()
        main.append(input_bar)

    def _build_sidebar(self):
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar.add_css_class("fern-sidebar")
        sidebar.set_size_request(220, -1)

        # Logo
        logo_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        logo_box.set_margin_top(16)
        logo_box.set_margin_bottom(8)
        logo_box.set_margin_start(14)
        logo_l = Gtk.Label(label="Fern")
        logo_l.add_css_class("fern-logo")
        logo_r = Gtk.Label(label="OS")
        logo_r.add_css_class("fern-logo")
        logo_r.add_css_class("fern-logo-accent")
        logo_box.append(logo_l)
        logo_box.append(logo_r)
        sidebar.append(logo_box)

        # New chat button
        new_btn = Gtk.Button(label="+ New chat")
        new_btn.add_css_class("fern-new-btn")
        new_btn.connect("clicked", self._on_new_chat)
        sidebar.append(new_btn)

        # History label
        hist_label = Gtk.Label(label="Recent")
        hist_label.add_css_class("fern-sidebar-label")
        hist_label.set_halign(Gtk.Align.START)
        sidebar.append(hist_label)

        # History list
        self.history_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.history_box.set_margin_start(6)
        self.history_box.set_margin_end(6)

        hist_scroll = Gtk.ScrolledWindow()
        hist_scroll.set_vexpand(True)
        hist_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        hist_scroll.set_child(self.history_box)
        sidebar.append(hist_scroll)

        self._refresh_history_list()
        return sidebar

    def _build_header(self):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header.add_css_class("fern-header")

        title = Gtk.Label(label="AI Chat")
        title.add_css_class("fern-logo")
        title.set_hexpand(True)
        title.set_halign(Gtk.Align.START)
        header.append(title)

        self.model_badge = Gtk.Label(label="no model")
        self.model_badge.add_css_class("fern-model-badge")
        header.append(self.model_badge)

        # Model switcher button
        switch_btn = Gtk.Button(label="⌄")
        switch_btn.add_css_class("fern-confirm-ignore-btn")
        switch_btn.set_tooltip_text("Switch model")
        switch_btn.connect("clicked", self._on_switch_model)
        header.append(switch_btn)

        return header

    def _build_input_bar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bar.add_css_class("fern-input-bar")

        self.input_entry = Gtk.Entry()
        self.input_entry.add_css_class("fern-input")
        self.input_entry.set_hexpand(True)
        self.input_entry.set_placeholder_text("Ask Fern anything, or give it a task...")
        self.input_entry.connect("activate", self._on_send)
        bar.append(self.input_entry)

        self.send_btn = Gtk.Button(label="Send")
        self.send_btn.add_css_class("fern-send-btn")
        self.send_btn.connect("clicked", self._on_send)
        bar.append(self.send_btn)

        return bar

    def _build_confirm_bar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        bar.add_css_class("fern-confirm-bar")
        bar.set_margin_start(16)
        bar.set_margin_end(16)
        bar.set_margin_bottom(4)

        self.confirm_label = Gtk.Label()
        self.confirm_label.add_css_class("fern-confirm-label")
        self.confirm_label.set_halign(Gtk.Align.START)
        self.confirm_label.set_wrap(True)
        self.confirm_label.set_selectable(True)
        bar.append(self.confirm_label)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        run_btn = Gtk.Button(label="Run this once")
        run_btn.add_css_class("fern-confirm-run-btn")
        run_btn.connect("clicked", self._on_confirm_run_once)

        ignore_btn = Gtk.Button(label="Ignore for this session")
        ignore_btn.add_css_class("fern-confirm-ignore-btn")
        ignore_btn.connect("clicked", self._on_confirm_ignore_session)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.add_css_class("fern-confirm-ignore-btn")
        cancel_btn.connect("clicked", self._on_confirm_cancel)

        btn_row.append(run_btn)
        btn_row.append(ignore_btn)
        btn_row.append(cancel_btn)
        bar.append(btn_row)

        return bar

    def _apply_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    # ── History sidebar ───────────────────────────────────
    def _refresh_history_list(self):
        while child := self.history_box.get_first_child():
            self.history_box.remove(child)

        for session in self.history.sessions:
            btn = Gtk.Button(label=session["title"][:32])
            btn.add_css_class("fern-history-btn")
            if self.current_session and session["id"] == self.current_session["id"]:
                btn.add_css_class("fern-history-active")
            btn.connect("clicked", self._on_load_session, session["id"])
            self.history_box.append(btn)

    def _on_new_chat(self, *_):
        self.current_session = self.history.new_session()
        self.ollama_messages = []
        self._clear_chat()
        self._refresh_history_list()
        self._add_system_message("New conversation started.")

    def _on_load_session(self, btn, session_id):
        for s in self.history.sessions:
            if s["id"] == session_id:
                self.current_session = s
                break
        self._clear_chat()
        self._refresh_history_list()

        # Replay messages visually
        self.ollama_messages = []
        for msg in self.current_session["messages"]:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                self._add_bubble_user(content)
                self.ollama_messages.append({"role": "user", "content": content})
            elif role == "assistant":
                self._add_bubble_ai(content)
                self.ollama_messages.append({"role": "assistant", "content": content})
            elif role == "tool":
                self._add_bubble_tool(content)
            elif role == "result":
                self._add_bubble_result(content)

    # ── Ollama check + model setup ────────────────────────
    def _check_ollama(self):
        def check():
            if not self.ollama.is_running():
                GLib.idle_add(self._show_ollama_error)
                return
            models = self.ollama.list_models()
            if not models:
                GLib.idle_add(self._show_no_model_dialog)
                return
            saved = self.prefs.get("model")
            model = saved if saved in models else models[0]
            self.prefs.set("model", model)
            GLib.idle_add(self._on_model_ready, model)

        threading.Thread(target=check, daemon=True).start()

    def _show_ollama_error(self):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Ollama isn't running",
            body="FernOS needs Ollama to be running to use the AI assistant.\n\nStart it with:  ollama serve",
        )
        dialog.add_response("close", "Close")
        dialog.present()

    def _show_no_model_dialog(self):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="No models installed",
            body="You don't have any Ollama models installed yet.\n\nWould you like to run the FernOS model setup to download one?",
        )
        dialog.add_response("cancel", "Not now")
        dialog.add_response("setup", "Run setup")
        dialog.set_response_appearance("setup", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_no_model_response)
        dialog.present()

    def _on_no_model_response(self, dialog, response):
        if response == "setup":
            subprocess.Popen(["bash", SETUP_SCRIPT])
            # Poll until a model appears
            GLib.timeout_add(3000, self._poll_for_model)

    def _poll_for_model(self):
        models = self.ollama.list_models()
        if models:
            self.prefs.set("model", models[0])
            self._on_model_ready(models[0])
            return False  # stop polling
        return True  # keep polling

    def _on_model_ready(self, model):
        self.model_badge.set_label(model)
        # Start a fresh session if none active
        if not self.current_session:
            if self.history.sessions:
                self.current_session = self.history.sessions[0]
                self._on_load_session(None, self.current_session["id"])
            else:
                self._on_new_chat()

    def _on_switch_model(self, *_):
        models = self.ollama.list_models()
        if not models:
            return

        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Switch model",
            body="Choose a model to use for this conversation:",
        )
        # Build a simple combo-style list via body label — GTK4 Adw doesn't have a built-in combo dialog
        # so we use a window with a ListBox instead
        dialog.add_response("cancel", "Cancel")
        dialog.present()
        dialog.close()

        win = Gtk.Window(transient_for=self, modal=True, title="Switch model")
        win.set_default_size(360, 300)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        win.set_child(box)

        label = Gtk.Label(label="Available models")
        label.add_css_class("fern-sidebar-label")
        label.set_halign(Gtk.Align.START)
        label.set_margin_top(12)
        label.set_margin_start(14)
        box.append(label)

        lb = Gtk.ListBox()
        lb.set_selection_mode(Gtk.SelectionMode.SINGLE)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_child(lb)
        box.append(scroll)

        for m in models:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=m)
            lbl.set_halign(Gtk.Align.START)
            lbl.set_margin_start(14)
            lbl.set_margin_top(8)
            lbl.set_margin_bottom(8)
            row.set_child(lbl)
            lb.append(row)

        def on_row_activated(lb, row):
            idx = row.get_index()
            chosen = models[idx]
            self.prefs.set("model", chosen)
            self.model_badge.set_label(chosen)
            win.close()

        lb.connect("row-activated", on_row_activated)

        btn = Gtk.Button(label="Cancel")
        btn.add_css_class("fern-confirm-ignore-btn")
        btn.set_margin_start(14)
        btn.set_margin_end(14)
        btn.set_margin_top(8)
        btn.set_margin_bottom(12)
        btn.connect("clicked", lambda *_: win.close())
        box.append(btn)
        win.present()

    # ── Chat bubbles ──────────────────────────────────────
    def _clear_chat(self):
        while child := self.chat_box.get_first_child():
            self.chat_box.remove(child)

    def _add_system_message(self, text):
        label = Gtk.Label(label=text)
        label.add_css_class("fern-typing")
        label.set_halign(Gtk.Align.CENTER)
        self.chat_box.append(label)
        self._scroll_bottom()

    def _make_bubble_row(self, align):
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        row.set_halign(align)
        row.set_hexpand(False)
        if align == Gtk.Align.END:
            row.set_margin_start(80)
        else:
            row.set_margin_end(80)
        return row

    def _add_bubble_user(self, text):
        row = self._make_bubble_row(Gtk.Align.END)
        sender = Gtk.Label(label="you")
        sender.add_css_class("fern-sender-label")
        sender.set_halign(Gtk.Align.END)
        row.append(sender)

        bubble = Gtk.Label(label=text)
        bubble.add_css_class("fern-bubble-user")
        bubble.set_wrap(True)
        bubble.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        bubble.set_selectable(True)
        bubble.set_halign(Gtk.Align.END)
        row.append(bubble)

        self.chat_box.append(row)
        self._scroll_bottom()

    def _add_bubble_ai(self, text):
        row = self._make_bubble_row(Gtk.Align.START)
        sender = Gtk.Label(label="fern")
        sender.add_css_class("fern-sender-label")
        sender.set_halign(Gtk.Align.START)
        row.append(sender)

        bubble = Gtk.Label(label=text)
        bubble.add_css_class("fern-bubble-ai")
        bubble.set_wrap(True)
        bubble.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        bubble.set_selectable(True)
        bubble.set_halign(Gtk.Align.START)
        bubble.set_xalign(0)
        row.append(bubble)

        self.chat_box.append(row)
        self._scroll_bottom()
        return bubble  # return so we can update it while streaming

    def _add_bubble_ai_streaming(self):
        """Add an empty AI bubble and return a reference to update it."""
        row = self._make_bubble_row(Gtk.Align.START)
        sender = Gtk.Label(label="fern")
        sender.add_css_class("fern-sender-label")
        sender.set_halign(Gtk.Align.START)
        row.append(sender)

        bubble = Gtk.Label(label="")
        bubble.add_css_class("fern-bubble-ai")
        bubble.set_wrap(True)
        bubble.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        bubble.set_selectable(True)
        bubble.set_halign(Gtk.Align.START)
        bubble.set_xalign(0)
        row.append(bubble)

        self.chat_box.append(row)
        self.current_ai_label = bubble
        self.current_ai_text = ""
        return bubble

    def _add_bubble_tool(self, cmd):
        row = self._make_bubble_row(Gtk.Align.START)
        row.set_margin_start(10)

        label = Gtk.Label(label=f"$ {cmd}")
        label.add_css_class("fern-bubble-tool")
        label.set_wrap(True)
        label.set_wrap_mode(Pango.WrapMode.CHAR)
        label.set_selectable(True)
        label.set_halign(Gtk.Align.START)
        label.set_xalign(0)
        row.append(label)

        self.chat_box.append(row)
        self._scroll_bottom()

    def _add_bubble_result(self, text):
        row = self._make_bubble_row(Gtk.Align.START)
        row.set_margin_start(10)

        # Truncate very long output for display
        display = text if len(text) < 2000 else text[:2000] + "\n… (truncated)"

        label = Gtk.Label(label=display)
        label.add_css_class("fern-bubble-result")
        label.set_wrap(True)
        label.set_wrap_mode(Pango.WrapMode.CHAR)
        label.set_selectable(True)
        label.set_halign(Gtk.Align.START)
        label.set_xalign(0)
        row.append(label)

        self.chat_box.append(row)
        self._scroll_bottom()

    def _scroll_bottom(self):
        def do_scroll():
            adj = self.scroll.get_vadjustment()
            adj.set_value(adj.get_upper())
        GLib.idle_add(do_scroll)

    # ── Send + agentic loop ───────────────────────────────
    def _on_send(self, *_):
        if self.is_thinking:
            return
        text = self.input_entry.get_text().strip()
        if not text:
            return
        model = self.prefs.get("model")
        if not model:
            return

        self.input_entry.set_text("")
        self._add_bubble_user(text)

        # Save to session
        if self.current_session is None:
            self.current_session = self.history.new_session()

        self.current_session["messages"].append({"role": "user", "content": text})
        if len(self.current_session["messages"]) == 1:
            # Use first message as session title
            self.current_session["title"] = text[:40]
        self.history.update_session(self.current_session)
        self._refresh_history_list()

        # Prepare ollama messages (inject system prompt on first turn)
        if not self.ollama_messages:
            self.ollama_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.ollama_messages.append({"role": "user", "content": text})

        self._set_thinking(True)
        threading.Thread(
            target=self._agent_turn,
            args=(model,),
            daemon=True,
        ).start()

    def _set_thinking(self, val):
        self.is_thinking = val
        self.send_btn.set_sensitive(not val)
        self.typing_label.set_visible(val)

    def _agent_turn(self, model):
        """One round of the agentic loop: stream a response, extract <RUN> blocks, execute them."""
        response_text = []

        def on_chunk(chunk):
            response_text.append(chunk)
            GLib.idle_add(self._stream_chunk, chunk)

        def on_done():
            GLib.idle_add(self._on_stream_done, "".join(response_text), model)

        self.ollama.chat_stream(model, self.ollama_messages, on_chunk, on_done)

    def _stream_chunk(self, chunk):
        if self.current_ai_label is None:
            self._add_bubble_ai_streaming()
        self.current_ai_text += chunk
        # Don't render <RUN>...</RUN> blocks in the bubble — show clean text
        display = self._strip_run_tags(self.current_ai_text)
        self.current_ai_label.set_label(display)
        self._scroll_bottom()

    def _strip_run_tags(self, text):
        import re
        return re.sub(r"<RUN>.*?</RUN>", "", text, flags=re.DOTALL).strip()

    def _on_stream_done(self, full_text, model):
        import re

        # Finalise the AI bubble with clean text
        display = self._strip_run_tags(full_text)
        if self.current_ai_label:
            self.current_ai_label.set_label(display if display else "(running commands...)")
        self.current_ai_label = None

        # Save assistant message
        self.ollama_messages.append({"role": "assistant", "content": full_text})
        self.current_session["messages"].append({"role": "assistant", "content": full_text})
        self.history.update_session(self.current_session)

        # Extract all <RUN> commands
        commands = re.findall(r"<RUN>(.*?)</RUN>", full_text, re.DOTALL)
        commands = [c.strip() for c in commands if c.strip()]

        if commands:
            # Execute them sequentially; if any is destructive, pause for confirm
            self._execute_commands(commands, model, index=0)
        else:
            self._set_thinking(False)

    def _execute_commands(self, commands, model, index):
        if index >= len(commands):
            # All done — do another agent turn to let it continue if needed
            self._set_thinking(False)
            return

        cmd = commands[index]

        if self.executor.is_destructive(cmd):
            # Show confirm bar and pause
            self.pending_command = (commands, model, index)
            self.confirm_label.set_label(f"⚠  Destructive command:\n$ {cmd}")
            self.confirm_bar.set_visible(True)
        else:
            self._run_command(cmd, commands, model, index)

    def _run_command(self, cmd, commands, model, index):
        self._add_bubble_tool(cmd)
        self.current_session["messages"].append({"role": "tool", "content": cmd})

        def do_run():
            stdout, stderr, code = self.executor.run(cmd)
            result = stdout
            if stderr:
                result += f"\n[stderr]\n{stderr}" if result else stderr
            if not result:
                result = f"(exit code {code})"
            GLib.idle_add(self._on_command_result, result, cmd, commands, model, index)

        threading.Thread(target=do_run, daemon=True).start()

    def _on_command_result(self, result, cmd, commands, model, index):
        self._add_bubble_result(result)
        self.current_session["messages"].append({"role": "result", "content": result})
        self.history.update_session(self.current_session)

        # Feed result back to the model
        result_msg = f"[RESULT of: {cmd}]\n{result}"
        self.ollama_messages.append({"role": "user", "content": result_msg})

        # Continue with next command in the list
        next_index = index + 1
        if next_index < len(commands):
            self._execute_commands(commands, model, next_index)
        else:
            # All commands in this response done — do another model turn
            # so it can decide whether to continue or summarise
            threading.Thread(
                target=self._agent_turn,
                args=(model,),
                daemon=True,
            ).start()

    # ── Confirm bar handlers ──────────────────────────────
    def _on_confirm_run_once(self, *_):
        self.confirm_bar.set_visible(False)
        if self.pending_command:
            commands, model, index = self.pending_command
            self.pending_command = None
            self._run_command(commands[index], commands, model, index)

    def _on_confirm_ignore_session(self, *_):
        self.executor.ignore_all_destructive = True
        self.confirm_bar.set_visible(False)
        if self.pending_command:
            commands, model, index = self.pending_command
            self.pending_command = None
            self._run_command(commands[index], commands, model, index)

    def _on_confirm_cancel(self, *_):
        self.confirm_bar.set_visible(False)
        self.pending_command = None
        # Tell the model it was cancelled
        cancel_msg = "[RESULT: Command was cancelled by user.]"
        self.ollama_messages.append({"role": "user", "content": cancel_msg})
        self._set_thinking(False)
        self._add_system_message("Command cancelled.")


# ─── App ──────────────────────────────────────────────────
class FernChatApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="dev.fernos.chat")

    def do_activate(self):
        win = FernChatWindow(self)
        win.present()


def main():
    # Suppress accessibility bus noise
    os.environ.setdefault("NO_AT_BRIDGE", "1")
    app = FernChatApp()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
