import argparse
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.agent import answer_question
from app.context_collector import collect_context


class LocalPilotPopup:
    def __init__(self, selected_path: str):
        self.selected_path = selected_path
        self.messages: queue.Queue[tuple[str, str]] = queue.Queue()
        self.context_summary = "Loading selected item..."

        self.root = tk.Tk()
        self.root.title("Local Pilot")
        self.root.geometry("860x660")
        self.root.minsize(680, 500)
        self.root.configure(bg="#f5f7fb")

        self.colors = {
            "bg": "#f5f7fb",
            "panel": "#ffffff",
            "border": "#d9e0ea",
            "text": "#172033",
            "muted": "#64748b",
            "brand": "#2563eb",
            "brand_dark": "#1d4ed8",
            "assistant": "#ffffff",
            "user": "#e8f0ff",
            "input": "#ffffff",
        }

        self._configure_style()
        self._build_ui()
        self._load_context_preview()
        self.root.after(100, self._drain_messages)

    def run(self) -> None:
        self.root.mainloop()

    def _configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Accent.TButton",
            background=self.colors["brand"],
            foreground="#ffffff",
            borderwidth=0,
            focusthickness=0,
            font=("Segoe UI", 10, "bold"),
            padding=(18, 12),
        )
        style.map(
            "Accent.TButton",
            background=[("active", self.colors["brand_dark"]), ("disabled", "#94a3b8")],
            foreground=[("disabled", "#eef2ff")],
        )

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        shell = tk.Frame(self.root, bg=self.colors["bg"], padx=22, pady=20)
        shell.grid(row=0, column=0, rowspan=4, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)

        header = tk.Frame(shell, bg=self.colors["bg"])
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.columnconfigure(1, weight=1)

        mark = tk.Canvas(header, width=42, height=42, bg=self.colors["bg"], highlightthickness=0)
        mark.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 12))
        mark.create_oval(3, 3, 39, 39, fill=self.colors["brand"], outline="")
        mark.create_text(21, 21, text="LP", fill="#ffffff", font=("Segoe UI", 10, "bold"))

        tk.Label(
            header,
            text="Local Pilot",
            font=("Segoe UI", 20, "bold"),
            fg=self.colors["text"],
            bg=self.colors["bg"],
            anchor="w",
        ).grid(row=0, column=1, sticky="ew")

        tk.Label(
            header,
            text="Ask questions about the file or folder you selected.",
            font=("Segoe UI", 10),
            fg=self.colors["muted"],
            bg=self.colors["bg"],
            anchor="w",
        ).grid(row=1, column=1, sticky="ew", pady=(2, 0))

        context_card = tk.Frame(
            shell,
            bg=self.colors["panel"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            padx=14,
            pady=10,
        )
        context_card.grid(row=1, column=0, sticky="new", pady=(0, 12))
        context_card.columnconfigure(0, weight=1)

        self.context_title = tk.Label(
            context_card,
            text="Selected item",
            font=("Segoe UI", 9, "bold"),
            fg=self.colors["brand"],
            bg=self.colors["panel"],
            anchor="w",
        )
        self.context_title.grid(row=0, column=0, sticky="ew")

        self.path_label = tk.Label(
            context_card,
            text=self.selected_path,
            font=("Segoe UI", 9),
            fg=self.colors["text"],
            bg=self.colors["panel"],
            anchor="w",
            wraplength=760,
            justify="left",
        )
        self.path_label.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        self.summary_label = tk.Label(
            context_card,
            text=self.context_summary,
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["panel"],
            anchor="w",
            wraplength=760,
            justify="left",
        )
        self.summary_label.grid(row=2, column=0, sticky="ew", pady=(4, 0))

        actions = tk.Frame(shell, bg=self.colors["bg"])
        actions.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        actions.columnconfigure(4, weight=1)

        quick_actions = [
            ("Summary", "Summarize this document in 5 concise bullets."),
            ("Skills", "List the skills mentioned in this document."),
            ("Projects", "List all projects mentioned in this document with one-line descriptions."),
            ("Experience", "Summarize the experience mentioned in this document."),
        ]
        for index, (label, prompt) in enumerate(quick_actions):
            tk.Button(
                actions,
                text=label,
                font=("Segoe UI", 9, "bold"),
                fg=self.colors["brand"],
                bg="#eef4ff",
                activebackground="#dbeafe",
                activeforeground=self.colors["brand_dark"],
                relief=tk.FLAT,
                padx=12,
                pady=7,
                command=lambda value=prompt: self._ask_prompt(value),
            ).grid(row=0, column=index, sticky="w", padx=(0, 8))

        chat_panel = tk.Frame(
            shell,
            bg=self.colors["panel"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        chat_panel.grid(row=3, column=0, sticky="nsew", pady=(0, 12))
        chat_panel.columnconfigure(0, weight=1)
        chat_panel.rowconfigure(0, weight=1)

        self.chat_canvas = tk.Canvas(chat_panel, bg=self.colors["panel"], highlightthickness=0)
        self.chat_canvas.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(chat_panel, orient="vertical", command=self.chat_canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.chat_canvas.configure(yscrollcommand=scrollbar.set)

        self.messages_frame = tk.Frame(self.chat_canvas, bg=self.colors["panel"], padx=14, pady=14)
        self.messages_window = self.chat_canvas.create_window(
            (0, 0), window=self.messages_frame, anchor="nw"
        )
        self.messages_frame.bind("<Configure>", self._sync_scroll_region)
        self.chat_canvas.bind("<Configure>", self._sync_message_width)
        self.chat_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        input_card = tk.Frame(
            shell,
            bg=self.colors["input"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        input_card.grid(row=4, column=0, sticky="ew")
        input_card.columnconfigure(0, weight=1)

        self.question = tk.Text(
            input_card,
            height=3,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            fg=self.colors["text"],
            bg=self.colors["input"],
            bd=0,
            padx=4,
            pady=4,
            insertbackground=self.colors["brand"],
        )
        self.question.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self.question.bind("<Control-Return>", self._ask)

        self.ask_button = ttk.Button(
            input_card,
            text="Ask",
            style="Accent.TButton",
            command=self._ask,
        )
        self.ask_button.grid(row=0, column=1, sticky="ns")

        footer = tk.Frame(shell, bg=self.colors["bg"])
        footer.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        footer.columnconfigure(0, weight=1)

        self.status = tk.Label(
            footer,
            text="Ctrl+Enter to ask",
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["bg"],
            anchor="w",
        )
        self.status.grid(row=0, column=0, sticky="ew")

        tk.Label(
            footer,
            text="Powered by local Ollama",
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["bg"],
            anchor="e",
        ).grid(row=0, column=1, sticky="e")

    def _load_context_preview(self) -> None:
        try:
            context = collect_context(self.selected_path)
            self.summary_label.configure(text=context["summary"])
            self._append(
                "Local Pilot",
                f"Loaded {context['kind']}: {context['name']}\n\n"
                "Ask me anything about it.",
            )
        except Exception as exc:
            self.summary_label.configure(text="Could not load selected item.")
            self._append("Local Pilot", f"Could not load selected item:\n{exc}")

    def _ask(self, event: object | None = None) -> str:
        question = self.question.get("1.0", tk.END).strip()
        if not question:
            return "break"

        self._submit_question(question)
        return "break"

    def _ask_prompt(self, prompt: str) -> None:
        self._submit_question(prompt)

    def _submit_question(self, question: str) -> None:
        self.question.delete("1.0", tk.END)
        self._append("You", question)
        self._set_busy(True)

        thread = threading.Thread(target=self._answer_in_background, args=(question,), daemon=True)
        thread.start()

    def _answer_in_background(self, question: str) -> None:
        try:
            result = answer_question(self.selected_path, question)
            self.messages.put(("Local Pilot", result["answer"]))
        except Exception as exc:
            self.messages.put(("Local Pilot", f"Something went wrong:\n{exc}"))
        finally:
            self.messages.put(("status", "ready"))

    def _drain_messages(self) -> None:
        while True:
            try:
                sender, text = self.messages.get_nowait()
            except queue.Empty:
                break

            if sender == "status":
                self._set_busy(False)
            else:
                self._append(sender, text)

        self.root.after(100, self._drain_messages)

    def _append(self, sender: str, text: str) -> None:
        is_user = sender == "You"
        row = tk.Frame(self.messages_frame, bg=self.colors["panel"])
        row.pack(fill="x", pady=(0, 12))
        row.columnconfigure(0, weight=1)

        bubble = tk.Frame(
            row,
            bg=self.colors["user"] if is_user else self.colors["assistant"],
            highlightbackground="#c7d2fe" if is_user else self.colors["border"],
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        bubble.grid(row=0, column=0, sticky="e" if is_user else "w")

        tk.Label(
            bubble,
            text=sender,
            font=("Segoe UI", 9, "bold"),
            fg=self.colors["brand"] if not is_user else self.colors["brand_dark"],
            bg=bubble["bg"],
            anchor="w",
        ).pack(fill="x", anchor="w")

        tk.Label(
            bubble,
            text=text,
            font=("Segoe UI", 10),
            fg=self.colors["text"],
            bg=bubble["bg"],
            justify="left",
            anchor="w",
            wraplength=620,
        ).pack(fill="x", anchor="w", pady=(4, 0))

        self.root.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    def _set_busy(self, busy: bool) -> None:
        if busy:
            self.ask_button.configure(state=tk.DISABLED)
            self.status.configure(text="Thinking with Ollama...")
        else:
            self.ask_button.configure(state=tk.NORMAL)
            self.status.configure(text="Ctrl+Enter to ask")

    def _sync_scroll_region(self, event: object | None = None) -> None:
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))

    def _sync_message_width(self, event: tk.Event) -> None:
        self.chat_canvas.itemconfigure(self.messages_window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        self.chat_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


def main() -> None:
    parser = argparse.ArgumentParser(description="Open Local Pilot chat for a selected path.")
    parser.add_argument("path", help="Selected file or folder path")
    args = parser.parse_args()

    LocalPilotPopup(args.path).run()


if __name__ == "__main__":
    main()
