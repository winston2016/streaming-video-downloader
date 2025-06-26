# -*- coding: utf-8 -*-
"""Kivy application providing a simple menu for downloading
videos from multiple platforms and cutting videos. Downloads are
organized in ``videos/<data>/<plataforma>``.

The cut screen allows selecting a local file and saving the same
cut in each platform directory. This is a basic example that can
be extended with ChatGPT integration for automatic clipping.
"""
from datetime import datetime
import os
import threading

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.uix.modalview import ModalView
from kivy.clock import Clock, mainthread
import openai
from dotenv import load_dotenv

load_dotenv()

import yt_dlp
import instaloader
from moviepy.editor import VideoFileClip

try:
    from tkinter import filedialog, Tk
except Exception:
    filedialog = None
    Tk = None


# Helper functions ---------------------------------------------------------

def _get_platform_dir(platform: str) -> str:
    """Return directory for the current date and platform."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join("videos", date_str, platform)
    os.makedirs(path, exist_ok=True)
    return path


def hms_to_seconds(value: str) -> float:
    """Convert HH:MM:SS string to seconds."""
    parts = value.strip().split(":")
    try:
        parts = [float(p) for p in parts]
    except ValueError:
        raise ValueError("Tempo inválido")
    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h = 0
        m, s = parts
    elif len(parts) == 1:
        h = 0
        m = 0
        s = parts[0]
    else:
        raise ValueError("Tempo inválido")
    return h * 3600 + m * 60 + s


class MyLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)


# Screens -----------------------------------------------------------------

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        layout.add_widget(Label(text="Menu", font_size="20sp"))
        btn_download = Button(text="Baixar Vídeo")
        btn_download.bind(on_press=lambda *_: setattr(self.manager, "current", "download"))
        layout.add_widget(btn_download)
        btn_cut = Button(text="Cortar Vídeo")
        btn_cut.bind(on_press=lambda *_: setattr(self.manager, "current", "cut"))
        layout.add_widget(btn_cut)
        btn_auto = Button(text="Corte Automático")
        btn_auto.bind(on_press=lambda *_: setattr(self.manager, "current", "auto"))
        layout.add_widget(btn_auto)
        btn_conf = Button(text="Configurar API")
        btn_conf.bind(on_press=lambda *_: setattr(self.manager, "current", "config"))
        layout.add_widget(btn_conf)
        self.add_widget(layout)


class DownloadScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.url_input = TextInput(hint_text="URL", size_hint_y=None, height=40)
        self.progress = ProgressBar(max=100, size_hint_y=None, height=30)
        self._loading = None

        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        layout.add_widget(Label(text="URL do vídeo:"))
        layout.add_widget(self.url_input)
        btn = Button(text="Baixar", size_hint_y=None, height=40)
        btn.bind(on_press=self.start_download)
        layout.add_widget(btn)
        layout.add_widget(self.progress)
        back = Button(text="Voltar", size_hint_y=None, height=40)
        back.bind(on_press=lambda *_: setattr(self.manager, "current", "menu"))
        layout.add_widget(back)
        self.add_widget(layout)

    @mainthread
    def update_progress(self, value):
        self.progress.value = value

    # Loading helpers -----------------------------------------------------
    def show_loading(self):
        if self._loading is None:
            layout = BoxLayout(orientation="vertical", padding=10)
            layout.add_widget(Label(text="Carregando..."))
            self._loading = ModalView(size_hint=(0.5, 0.3), auto_dismiss=False)
            self._loading.add_widget(layout)
        self._loading.open()

    def hide_loading(self, *_):
        if self._loading is not None:
            self._loading.dismiss()
            self._loading = None

    def show_popup(self, title, message):
        popup_layout = BoxLayout(orientation="vertical", padding=10)
        popup_layout.add_widget(Label(text=message))
        btn = Button(text="Fechar", size_hint_y=None, height=40)
        popup_layout.add_widget(btn)
        popup = Popup(title=title, content=popup_layout, size_hint=(0.75, 0.5))
        btn.bind(on_press=popup.dismiss)
        popup.open()

    # Download helpers -----------------------------------------------------
    def _hook(self, d):
        if d.get("status") == "downloading":
            percent_str = d.get("_percent_str", "0").replace("%", "").strip()
            try:
                self.update_progress(float(percent_str))
            except ValueError:
                pass
        elif d.get("status") == "finished":
            self.update_progress(100)
            Clock.schedule_once(self.hide_loading)

    def _download_youtube(self, url):
        path = _get_platform_dir("youtube")
        opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": os.path.join(path, "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "logger": MyLogger(),
            "progress_hooks": [self._hook],
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        Clock.schedule_once(lambda *_: self.show_popup("Sucesso", "Download concluído"))

    def _download_tiktok(self, url):
        path = _get_platform_dir("tiktok")
        opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": os.path.join(path, "%(title)s.%(ext)s"),
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "logger": MyLogger(),
            "progress_hooks": [self._hook],
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        Clock.schedule_once(lambda *_: self.show_popup("Sucesso", "Download concluído"))

    def _download_instagram(self, url):
        path = _get_platform_dir("instagram")
        loader = instaloader.Instaloader(dirname_pattern=path, filename_pattern="{shortcode}")
        media_id = url.rstrip("/").split("/")[-1]
        post = instaloader.Post.from_shortcode(loader.context, media_id)
        loader.download_post(post, target="post")
        Clock.schedule_once(lambda *_: self.show_popup("Sucesso", "Download concluído"))

    def start_download(self, *_):
        self.progress.value = 0
        self.show_loading()
        url = self.url_input.text
        if "youtube" in url:
            threading.Thread(target=self._download_youtube, args=(url,), daemon=True).start()
        elif "tiktok" in url:
            threading.Thread(target=self._download_tiktok, args=(url,), daemon=True).start()
        elif "instagram" in url:
            threading.Thread(target=self._download_instagram, args=(url,), daemon=True).start()
        else:
            self.hide_loading()
            self.show_popup("Erro", "Plataforma não reconhecida")


class CutScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.file_path = TextInput(hint_text="Caminho do vídeo", readonly=True, size_hint_y=None, height=40)
        self.start_input = TextInput(hint_text="Início (HH:MM:SS)", size_hint_y=None, height=40)
        self.end_input = TextInput(hint_text="Fim (HH:MM:SS)", size_hint_y=None, height=40)
        self.progress = ProgressBar(max=100, size_hint_y=None, height=30)
        self._loading = None

        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        btn_choose = Button(text="Selecionar Vídeo")
        btn_choose.bind(on_press=self.choose_file)
        layout.add_widget(btn_choose)
        layout.add_widget(self.file_path)
        layout.add_widget(self.start_input)
        layout.add_widget(self.end_input)
        btn_cut = Button(text="Cortar", size_hint_y=None, height=40)
        btn_cut.bind(on_press=self.start_cut)
        layout.add_widget(btn_cut)
        layout.add_widget(self.progress)
        back = Button(text="Voltar", size_hint_y=None, height=40)
        back.bind(on_press=lambda *_: setattr(self.manager, "current", "menu"))
        layout.add_widget(back)
        self.add_widget(layout)

    def choose_file(self, *_):
        if filedialog is None:
            return
        root = Tk()
        root.withdraw()
        path = filedialog.askopenfilename(title="Selecione o vídeo")
        root.destroy()
        if path:
            self.file_path.text = path

    @mainthread
    def update_progress(self, value):
        self.progress.value = value

    # Loading helpers -----------------------------------------------------
    def show_loading(self):
        if self._loading is None:
            layout = BoxLayout(orientation="vertical", padding=10)
            layout.add_widget(Label(text="Carregando..."))
            self._loading = ModalView(size_hint=(0.5, 0.3), auto_dismiss=False)
            self._loading.add_widget(layout)
        self._loading.open()

    def hide_loading(self, *_):
        if self._loading is not None:
            self._loading.dismiss()
            self._loading = None

    def _cut_video(self, path, start, end):
        clip = VideoFileClip(path).subclip(start, end)
        for platform in ["youtube", "tiktok", "instagram"]:
            out_dir = _get_platform_dir(platform)
            out_file = os.path.join(out_dir, f"corte_{platform}.mp4")
            clip.write_videofile(out_file, codec="libx264", audio_codec="aac")
        Clock.schedule_once(lambda *_: self.update_progress(100))
        Clock.schedule_once(lambda *_: self.show_popup("Sucesso", "Cortes gerados"))
        Clock.schedule_once(self.hide_loading)

    def start_cut(self, *_):
        path = self.file_path.text
        try:
            start = hms_to_seconds(self.start_input.text)
            end = hms_to_seconds(self.end_input.text)
        except ValueError:
            self.show_popup("Erro", "Tempos inválidos")
            return
        self.progress.value = 0
        self.show_loading()
        threading.Thread(target=self._cut_video, args=(path, start, end), daemon=True).start()

    def show_popup(self, title, message):
        popup_layout = BoxLayout(orientation="vertical", padding=10)
        popup_layout.add_widget(Label(text=message))
        btn = Button(text="Fechar", size_hint_y=None, height=40)
        popup_layout.add_widget(btn)
        popup = Popup(title=title, content=popup_layout, size_hint=(0.75, 0.5))
        btn.bind(on_press=popup.dismiss)
        popup.open()


class ConfigScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_input = TextInput(text=os.getenv("OPENAI_API_KEY", ""), size_hint_y=None, height=40)
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        layout.add_widget(Label(text="Chave da API ChatGPT", font_size="20sp"))
        layout.add_widget(self.api_input)
        btn_save = Button(text="Salvar", size_hint_y=None, height=40)
        btn_save.bind(on_press=self.save_key)
        layout.add_widget(btn_save)
        back = Button(text="Voltar", size_hint_y=None, height=40)
        back.bind(on_press=lambda *_: setattr(self.manager, "current", "menu"))
        layout.add_widget(back)
        self.add_widget(layout)

    def save_key(self, *_):
        key = self.api_input.text.strip()
        os.environ["OPENAI_API_KEY"] = key
        with open(".env", "w") as f:
            f.write(f"OPENAI_API_KEY={key}\n")
        self.show_popup("Sucesso", "Chave salva")

    def show_popup(self, title, message):
        popup_layout = BoxLayout(orientation="vertical", padding=10)
        popup_layout.add_widget(Label(text=message))
        btn = Button(text="Fechar", size_hint_y=None, height=40)
        popup_layout.add_widget(btn)
        popup = Popup(title=title, content=popup_layout, size_hint=(0.75, 0.5))
        btn.bind(on_press=popup.dismiss)
        popup.open()


class AutoCutScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.file_path = TextInput(hint_text="Caminho do vídeo", readonly=True, size_hint_y=None, height=40)
        self.transcript_input = TextInput(hint_text="Transcrição do vídeo", size_hint=(1, 0.4))
        self.niche_input = TextInput(hint_text="Nicho/tema", size_hint_y=None, height=40)
        self.suggestions_box = BoxLayout(orientation="vertical", size_hint_y=None)
        self._loading = None

        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        btn_video = Button(text="Selecionar Vídeo")
        btn_video.bind(on_press=self.choose_file)
        layout.add_widget(btn_video)
        layout.add_widget(self.file_path)
        layout.add_widget(self.transcript_input)
        layout.add_widget(self.niche_input)
        btn_analyze = Button(text="Gerar Sugestões", size_hint_y=None, height=40)
        btn_analyze.bind(on_press=self.generate)
        layout.add_widget(btn_analyze)
        layout.add_widget(Label(text="Sugestões:"))
        layout.add_widget(self.suggestions_box)
        back = Button(text="Voltar", size_hint_y=None, height=40)
        back.bind(on_press=lambda *_: setattr(self.manager, "current", "menu"))
        layout.add_widget(back)
        self.add_widget(layout)

    def choose_file(self, *_):
        if filedialog is None:
            return
        root = Tk(); root.withdraw()
        path = filedialog.askopenfilename(title="Selecione o vídeo")
        root.destroy()
        if path:
            self.file_path.text = path

    # Loading helpers -----------------------------------------------------
    def show_loading(self):
        if self._loading is None:
            layout = BoxLayout(orientation="vertical", padding=10)
            layout.add_widget(Label(text="Carregando..."))
            self._loading = ModalView(size_hint=(0.5, 0.3), auto_dismiss=False)
            self._loading.add_widget(layout)
        self._loading.open()

    def hide_loading(self, *_):
        if self._loading is not None:
            self._loading.dismiss()
            self._loading = None

    def generate(self, *_):
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            self.show_popup("Erro", "Configure a chave da API")
            return
        self.show_loading()
        openai.api_key = key
        prompt = (
            "Sugira até 3 cortes interessantes no formato HH:MM:SS-HH:MM:SS "
            "baseado no nicho '" + self.niche_input.text + "'.\n" + self.transcript_input.text
        )
        try:
            completion = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
            )
            text = completion.choices[0].message.content
        except Exception as exc:
            self.hide_loading()
            self.show_popup("Erro", str(exc))
            return
        self.hide_loading()
        self.show_suggestions(text)

    def show_suggestions(self, text):
        import re
        self.suggestions_box.clear_widgets()
        lines = re.findall(r"(\d{2}:\d{2}:\d{2}).*(\d{2}:\d{2}:\d{2})", text)
        for start, end in lines:
            btn = Button(text=f"{start} - {end}", size_hint_y=None, height=40)
            btn.bind(on_press=lambda _btn, s=start, e=end: self.cut_segment(s, e))
            self.suggestions_box.add_widget(btn)

    def cut_segment(self, start_str, end_str):
        path = self.file_path.text
        if not path:
            self.show_popup("Erro", "Selecione o vídeo")
            return
        try:
            start = hms_to_seconds(start_str)
            end = hms_to_seconds(end_str)
        except ValueError:
            self.show_popup("Erro", "Tempos inválidos")
            return
        threading.Thread(target=self._cut_video, args=(path, start, end), daemon=True).start()

    def _cut_video(self, path, start, end):
        clip = VideoFileClip(path).subclip(start, end)
        out_dir = _get_platform_dir("gpt")
        out_file = os.path.join(out_dir, f"corte_{int(start)}_{int(end)}.mp4")
        clip.write_videofile(out_file, codec="libx264", audio_codec="aac")
        Clock.schedule_once(lambda *_: self.show_popup("Sucesso", "Corte gerado"))
        Clock.schedule_once(self.hide_loading)

    def show_popup(self, title, message):
        popup_layout = BoxLayout(orientation="vertical", padding=10)
        popup_layout.add_widget(Label(text=message))
        btn = Button(text="Fechar", size_hint_y=None, height=40)
        popup_layout.add_widget(btn)
        popup = Popup(title=title, content=popup_layout, size_hint=(0.75, 0.5))
        btn.bind(on_press=popup.dismiss)
        popup.open()


# App ---------------------------------------------------------------------

class VideoApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(DownloadScreen(name="download"))
        sm.add_widget(CutScreen(name="cut"))
        sm.add_widget(AutoCutScreen(name="auto"))
        sm.add_widget(ConfigScreen(name="config"))
        return sm


if __name__ == "__main__":
    VideoApp().run()
