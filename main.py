from kivy.app import App
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox
from kivy.clock import Clock
from kivy.core.window import Window

import os
import threading
import subprocess
import shutil

# =========================
# WINDOW
# =========================
Window.size = (520, 1200)

# =========================
# GLOBALS
# =========================
overlay_items = []

# =========================
# HELPERS
# =========================
def format_time_srt(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)

    return f"{hrs:02}:{mins:02}:{secs:02},{millis:03}"


def build_atempo_filter(speed):
    filters = []
    while speed > 2.0:
        filters.append("atempo=2.0")
        speed /= 2.0
    filters.append(f"atempo={speed}")
    return ",".join(filters)


def create_subtitles(segments):
    srt_file = os.path.abspath("subtitles.srt")
    with open(srt_file, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments):
            f.write(f"{i+1}\n")
            f.write(f"{format_time_srt(seg.start)} --> {format_time_srt(seg.end)}\n")
            f.write(f"{seg.text}\n\n")
    return srt_file


# =========================
# MAIN APP
# =========================
class AndroidEditor(App):

    def build(self):
        self.selected_video = "/storage/emulated/0/input.mp4"
        self.bulk_folder = "/storage/emulated/0/videos"

        self.ffmpeg_path = None

        root = ScrollView()
        self.layout = BoxLayout(
            orientation="vertical",
            spacing=10,
            padding=15,
            size_hint_y=None
        )
        self.layout.bind(minimum_height=self.layout.setter("height"))

        self.layout.add_widget(Label(text="AI Shorts Generator ⚡", size_hint_y=None, height=60, font_size=24))

        self.layout.add_widget(Label(text="Clip Duration", size_hint_y=None, height=40))
        self.duration_entry = TextInput(text="30", multiline=False, size_hint_y=None, height=50)
        self.layout.add_widget(self.duration_entry)

        # splitter
        splitter = BoxLayout(size_hint_y=None, height=50)
        self.splitter_check = CheckBox()
        splitter.add_widget(self.splitter_check)
        splitter.add_widget(Label(text="✂️ Enable Splitting"))
        self.layout.add_widget(splitter)

        # viral
        viral = BoxLayout(size_hint_y=None, height=50)
        self.viral_check = CheckBox()
        viral.add_widget(self.viral_check)
        viral.add_widget(Label(text="🔥 Viral Mode"))
        self.layout.add_widget(viral)

        # aspect
        self.layout.add_widget(Label(text="Aspect Ratio", size_hint_y=None, height=40))
        self.aspect_spinner = Spinner(text="9:16", values=["9:16", "1:1", "16:9"], size_hint_y=None, height=50)
        self.layout.add_widget(self.aspect_spinner)

        # subtitles
        subs = BoxLayout(size_hint_y=None, height=50)
        self.subtitle_check = CheckBox()
        subs.add_widget(self.subtitle_check)
        subs.add_widget(Label(text="🎤 Add Subtitles"))
        self.layout.add_widget(subs)

        # speed
        speed = BoxLayout(size_hint_y=None, height=50)
        self.speed_check = CheckBox()
        speed.add_widget(self.speed_check)
        speed.add_widget(Label(text="⚡ Speed"))
        self.layout.add_widget(speed)

        self.speed_entry = TextInput(text="1", multiline=False, size_hint_y=None, height=50)
        self.layout.add_widget(self.speed_entry)

        # buttons
        Button(text="🔥 Generate Shorts", size_hint_y=None, height=70,
               on_press=self.start_processing)

        gen_btn = Button(text="🔥 Generate Shorts", size_hint_y=None, height=70)
        gen_btn.bind(on_press=self.start_processing)
        self.layout.add_widget(gen_btn)

        bulk_btn = Button(text="📂 Bulk Edit", size_hint_y=None, height=70)
        bulk_btn.bind(on_press=self.start_bulk)
        self.layout.add_widget(bulk_btn)

        self.result_label = Label(text="", size_hint_y=None, height=80)
        self.layout.add_widget(self.result_label)

        root.add_widget(self.layout)
        return root

    # =========================
    # FFmpeg setup (CRITICAL FIX)
    # =========================
    def on_start(self):
        src = os.path.join("assets", "ffmpeg")
        dst = os.path.join(self.user_data_dir, "ffmpeg")

        try:
            if not os.path.exists(dst):
                shutil.copy(src, dst)
                os.chmod(dst, 0o755)

            self.ffmpeg_path = dst
        except Exception as e:
            self.set_result(f"FFmpeg error: {e}")

    # =========================
    # OVERLAY
    # =========================
    def add_overlay(self, instance):
        overlay_items.append({
            "path": "/storage/emulated/0/overlay.png",
            "size": "150",
            "opacity": "0.7",
            "overlay_speed": "1",
            "x": "20",
            "y": "20",
            "start": "0",
            "green": False,
            "chroma": "green",
            "freeze": False
        })

        self.set_result(f"Overlay Added: {len(overlay_items)}")

    # =========================
    # START
    # =========================
    def start_processing(self, instance):
        threading.Thread(target=self.process_video).start()

    def start_bulk(self, instance):
        threading.Thread(target=self.bulk_video_edit).start()

    # =========================
    # PROCESS VIDEO
    # =========================
    def process_video(self):
        if not self.ffmpeg_path:
            self.set_result("FFmpeg not ready")
            return

        filepath = self.selected_video
        duration = self.duration_entry.text
        aspect = self.aspect_spinner.text

        speed_on = self.speed_check.active
        speed = float(self.speed_entry.text)

        add_subs = self.subtitle_check.active

        # scale
        if aspect == "9:16":
            vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        elif aspect == "1:1":
            vf = "scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080"
        else:
            vf = "scale=1280:720"

        if speed_on:
            vf += f",setpts={1/speed}*PTS"

        af = build_atempo_filter(speed) if speed_on else "anull"

        # subtitles (FIXED)
        if add_subs:
            srt = create_subtitles([])  # no whisper in APK
            vf += f",subtitles=filename='{srt}'"

        output = f"/storage/emulated/0/output_{os.path.basename(filepath)}"

        command = [
            self.ffmpeg_path,
            "-y",
            "-i", filepath,
            "-vf", vf,
            "-af", af,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            output
        ]

        try:
            subprocess.run(command, check=True)
            Clock.schedule_once(lambda dt: self.set_result("✅ Video Done"))
        except Exception as e:
            Clock.schedule_once(lambda dt: self.set_result(f"❌ Error: {e}"))

    # =========================
    # BULK
    # =========================
    def bulk_video_edit(self):
        files = os.listdir(self.bulk_folder)

        videos = [
            os.path.join(self.bulk_folder, f)
            for f in files
            if f.endswith((".mp4", ".mkv", ".mov", ".avi"))
        ]

        for v in videos:
            self.selected_video = v
            self.process_video()

        Clock.schedule_once(lambda dt: self.set_result("✅ Bulk Done"))

    # =========================
    # RESULT
    # =========================
    def set_result(self, text):
        self.result_label.text = text


# =========================
# RUN
# =========================
if __name__ == "__main__":
    AndroidEditor().run()