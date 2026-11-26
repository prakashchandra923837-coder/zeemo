"""
main.py — Kivy Mobile UI for Zeemo Clone Android APK
"""

import os
import threading
from pathlib import Path

from kivy.app import App
from kivy.clock import mainthread
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from zeemo_core import (
    STYLE_PRESETS,
    add_auto_emojis,
    chunks_to_editor_text,
    group_words_into_chunks,
    transcribe_via_api,
    write_ass,
    write_srt,
)

Window.clearcolor = (0.07, 0.07, 0.10, 1)


class ZeemoMobileRoot(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=14, spacing=10, **kwargs)
        self.video_path = ""
        self.chunks = []

        self.add_widget(Label(
            text="[b]Zeemo Clone — AI Auto Captions[/b]",
            markup=True,
            size_hint_y=None,
            height=44,
            font_size="20sp",
            color=(1, 0.85, 0.2, 1),
        ))

        scroll = ScrollView()
        form = BoxLayout(orientation="vertical", spacing=10, size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))

        # Video Picker
        self.video_label = Label(
            text="No video selected",
            size_hint_y=None,
            height=34,
            color=(0.8, 0.8, 0.85, 1),
        )
        pick_btn = Button(
            text="1. Select Video / Audio File",
            size_hint_y=None,
            height=48,
            background_color=(0.35, 0.25, 0.85, 1),
        )
        pick_btn.bind(on_release=self.pick_file)
        form.add_widget(pick_btn)
        form.add_widget(self.video_label)

        # Provider + API Key
        row1 = BoxLayout(size_hint_y=None, height=44, spacing=8)
        self.provider_spin = Spinner(text="groq", values=("groq", "openai"), size_hint_x=0.35)
        self.api_input = TextInput(
            hint_text="Paste Groq or OpenAI API Key",
            password=True,
            multiline=False,
        )
        row1.add_widget(self.provider_spin)
        row1.add_widget(self.api_input)
        form.add_widget(row1)

        # Language + Style + Position
        row2 = BoxLayout(size_hint_y=None, height=44, spacing=8)
        self.lang_spin = Spinner(text="auto", values=("auto", "hi", "en", "es", "fr"))
        self.style_spin = Spinner(
            text="zeemo_pop",
            values=tuple(STYLE_PRESETS.keys()),
        )
        self.pos_spin = Spinner(text="Bottom", values=("Bottom", "Center", "Top"))
        row2.add_widget(self.lang_spin)
        row2.add_widget(self.style_spin)
        row2.add_widget(self.pos_spin)
        form.add_widget(row2)

        # Words per line + Auto Emoji
        row3 = BoxLayout(size_hint_y=None, height=40, spacing=8)
        self.words_spin = Spinner(text="3", values=("2", "3", "4", "5"))
        self.emoji_chk = CheckBox(active=True, size_hint_x=0.2)
        row3.add_widget(Label(text="Words/line:", size_hint_x=0.3))
        row3.add_widget(self.words_spin)
        row3.add_widget(Label(text="Auto Emoji:", size_hint_x=0.3))
        row3.add_widget(self.emoji_chk)
        form.add_widget(row3)

        # Generate Button
        self.gen_btn = Button(
            text="2. Generate Auto Captions",
            size_hint_y=None,
            height=50,
            background_color=(0.15, 0.70, 0.45, 1),
        )
        self.gen_btn.bind(on_release=self.start_transcription)
        form.add_widget(self.gen_btn)

        self.status_label = Label(
            text="Ready.",
            size_hint_y=None,
            height=34,
            color=(0.7, 0.9, 1, 1),
        )
        form.add_widget(self.status_label)

        # Batch Caption Editor
        self.editor = TextInput(
            hint_text="Generated captions will appear here...",
            size_hint_y=None,
            height=220,
        )
        form.add_widget(self.editor)

        # Export Button
        export_btn = Button(
            text="3. Save .SRT & .ASS Files to Downloads",
            size_hint_y=None,
            height=50,
            background_color=(0.85, 0.45, 0.15, 1),
        )
        export_btn.bind(on_release=self.export_subtitles)
        form.add_widget(export_btn)

        scroll.add_widget(form)
        self.add_widget(scroll)

    def pick_file(self, *_):
        try:
            from plyer import filechooser
            filechooser.open_file(on_selection=self._on_file_selected)
        except Exception as exc:
            self.status_label.text = f"File picker error: {exc}"

    @mainthread
    def _on_file_selected(self, selection):
        if selection:
            self.video_path = selection[0]
            self.video_label.text = f"Selected: {os.path.basename(self.video_path)}"

    def start_transcription(self, *_):
        if not self.video_path:
            self.status_label.text = "Please select a video/audio file first."
            return
        self.status_label.text = "Transcribing with Whisper AI..."
        self.gen_btn.disabled = True
        threading.Thread(target=self._run_transcribe, daemon=True).start()

    def _run_transcribe(self):
        try:
            words, lang = transcribe_via_api(
                self.video_path,
                api_key=self.api_input.text,
                provider=self.provider_spin.text,
                language=self.lang_spin.text,
            )
            chunks = group_words_into_chunks(words, max_words_per_line=int(self.words_spin.text))
            if self.emoji_chk.active:
                chunks = add_auto_emojis(chunks)
            self._on_transcribe_done(chunks, lang)
        except Exception as exc:
            self._on_transcribe_error(str(exc))

    @mainthread
    def _on_transcribe_done(self, chunks, lang):
        self.chunks = chunks
        self.editor.text = chunks_to_editor_text(chunks)
        self.status_label.text = f"Done! Language: {lang} | Captions: {len(chunks)}"
        self.gen_btn.disabled = False

    @mainthread
    def _on_transcribe_error(self, msg):
        self.status_label.text = f"Error: {msg[:80]}"
        self.gen_btn.disabled = False

    def export_subtitles(self, *_):
        if not self.chunks:
            self.status_label.text = "Generate captions first!"
            return
        out_dir = Path("/sdcard/Download/ZeemoClone") if os.path.exists("/sdcard/Download") else Path("./zeemo_mobile_out")
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(self.video_path).stem if self.video_path else "captions"
        style = STYLE_PRESETS.get(self.style_spin.text, STYLE_PRESETS["zeemo_pop"])

        srt_p = str(out_dir / f"{stem}.srt")
        ass_p = str(out_dir / f"{stem}.ass")
        write_srt(self.chunks, srt_p, uppercase=style.uppercase)
        write_ass(self.chunks, ass_p, style=style, position=self.pos_spin.text)
        self.status_label.text = f"Saved to {out_dir}"


class ZeemoCloneApp(App):
    def build(self):
        return ZeemoMobileRoot()


if __name__ == "__main__":
    ZeemoCloneApp().run()
