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
import logging
from pathlib import Path

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.uix.slider import Slider
from kivy.uix.modalview import ModalView
from kivy.clock import Clock, mainthread
from kivy.utils import platform
import webbrowser
from kivy.uix.videoplayer import VideoPlayer
from kivy.uix.slider import Slider
import openai
from dotenv import load_dotenv

load_dotenv()

logs_path = Path("logs")
logs_path.mkdir(exist_ok=True)
logging.basicConfig(
    filename=logs_path / "auto_cut.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

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


def seconds_to_hms(value: float) -> str:
    """Format seconds into a ``HH:MM:SS`` string."""
    total = int(round(value))
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


class MyLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)


def ask_upload(paths):
    layout = BoxLayout(orientation="vertical", padding=10)
    layout.add_widget(Label(text="Cortes gerados. Postar automaticamente?"))
    btn_yes = Button(text="Sim", size_hint_y=None, height=40)
    btn_no = Button(text="Não", size_hint_y=None, height=40)
    layout.add_widget(btn_yes)
    layout.add_widget(btn_no)
    popup = Popup(title="Postar", content=layout, size_hint=(0.75, 0.5))

    def do_upload(_):
        popup.dismiss()
        threading.Thread(target=upload_videos, args=(paths,), daemon=True).start()

    btn_yes.bind(on_press=do_upload)
    btn_no.bind(on_press=popup.dismiss)
    popup.open()


def upload_videos(paths):
    from uploader import youtube, instagram, tiktok
    if "youtube" in paths:
        try:
            youtube.upload_video(paths["youtube"], title="Corte")
        except Exception as exc:
            print("YouTube upload failed:", exc)
    if "instagram" in paths:
        try:
            instagram.upload_video(paths["instagram"], caption="Corte")
        except Exception as exc:
            print("Instagram upload failed:", exc)
    if "tiktok" in paths:
        try:
            tiktok.upload_video(paths["tiktok"])
        except Exception as exc:
            print("TikTok upload failed:", exc)


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
        layout.add_widget(Label(text="Sites suportados:"))
        icons = BoxLayout(size_hint_y=None, height=40, spacing=10)

        Clock.schedule_once(self.hide_loading)
        def add_icon(name, url):
            img = os.path.join("assets", f"{name}.ppm")
            btn = Button(size_hint=(None, None), size=(40, 40),
                         background_normal=img, background_down=img)
            btn.bind(on_press=lambda *_: self.open_site(url))
            icons.add_widget(btn)

        add_icon("youtube", "https://www.youtube.com")
        add_icon("tiktok", "https://www.tiktok.com")
        add_icon("instagram", "https://www.instagram.com")

        layout.add_widget(icons)
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

    def open_site(self, url):
        # Use different behavior depending on the current platform
        if platform in ("android", "ios"):
            webbrowser.open(url)
        else:
            webbrowser.open(url, new=1)

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
        self.start_slider = None
        self.end_slider = None
        self._loading = None

        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        btn_choose = Button(text="Selecionar Vídeo")
        btn_choose.bind(on_press=self.choose_file)
        layout.add_widget(btn_choose)
        layout.add_widget(self.file_path)
        layout.add_widget(self.start_input)
        layout.add_widget(self.end_input)
        self.slider_box = BoxLayout(orientation="vertical")
        layout.add_widget(self.slider_box)
        btn_cut = Button(text="Cortar", size_hint_y=None, height=40)
        btn_cut.bind(on_press=self.start_cut)
        layout.add_widget(btn_cut)
        layout.add_widget(self.progress)
        back = Button(text="Voltar", size_hint_y=None, height=40)
        back.bind(on_press=lambda *_: setattr(self.manager, "current", "menu"))
        layout.add_widget(back)
        self.layout = layout
        self.add_widget(layout)
        self.start_input.bind(text=self._on_start_text)
        self.end_input.bind(text=self._on_end_text)

    def choose_file(self, *_):
        if filedialog is None:
            return
        root = Tk()
        root.withdraw()
        path = filedialog.askopenfilename(title="Selecione o vídeo")
        root.destroy()
        if path:
            self.file_path.text = path
            try:
                duration = VideoFileClip(path).duration
            except Exception as exc:
                self.show_popup("Erro", str(exc))
                return
            self.slider_box.clear_widgets()
            self.start_slider = Slider(min=0, max=duration, value=0)
            self.end_slider = Slider(min=0, max=duration, value=duration)
            self.start_slider.bind(value=self._on_start_slider)
            self.end_slider.bind(value=self._on_end_slider)
            self.slider_box.add_widget(self.start_slider)
            self.slider_box.add_widget(self.end_slider)
            self.start_input.text = "00:00:00"
            self.end_input.text = seconds_to_hms(duration)

    @mainthread
    def update_progress(self, value):
        self.progress.value = value

    def _on_start_slider(self, instance, value):
        if getattr(self, "_sync", False):
            return
        self._sync = True
        self.start_input.text = seconds_to_hms(value)
        self._sync = False

    def _on_end_slider(self, instance, value):
        if getattr(self, "_sync", False):
            return
        self._sync = True
        self.end_input.text = seconds_to_hms(value)
        self._sync = False

    def _on_start_text(self, instance, value):
        if getattr(self, "_sync", False):
            return
        try:
            sec = hms_to_seconds(value)
        except ValueError:
            return
        if self.start_slider:
            self._sync = True
            self.start_slider.value = sec
            self._sync = False

    def _on_end_text(self, instance, value):
        if getattr(self, "_sync", False):
            return
        try:
            sec = hms_to_seconds(value)
        except ValueError:
            return
        if self.end_slider:
            self._sync = True
            self.end_slider.value = sec
            self._sync = False
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
        sizes = {
            "youtube": (1280, 720),
            "tiktok": (720, 1280),
            "instagram": (1080, 1920),
        }
        for platform, new_size in sizes.items():
            out_dir = _get_platform_dir(platform)
            out_file = os.path.join(out_dir, f"corte_{platform}.mp4")
            resized = clip.resize(newsize=new_size)
            resized.write_videofile(out_file, codec="libx264", audio_codec="aac")
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
        self.yt_client_input = TextInput(text=os.getenv("YOUTUBE_CLIENT_SECRETS", ""), size_hint_y=None, height=40)
        self.insta_user_input = TextInput(text=os.getenv("INSTAGRAM_USER", ""), size_hint_y=None, height=40)
        self.insta_pass_input = TextInput(text=os.getenv("INSTAGRAM_PASSWORD", ""), size_hint_y=None, height=40, password=True)
        self.tiktok_user_input = TextInput(text=os.getenv("TIKTOK_USER", ""), size_hint_y=None, height=40)
        self.tiktok_pass_input = TextInput(text=os.getenv("TIKTOK_PASSWORD", ""), size_hint_y=None, height=40, password=True)

        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        layout.add_widget(Label(text="Chave da API ChatGPT", font_size="20sp"))
        layout.add_widget(self.api_input)
        layout.add_widget(Label(text="Arquivo client_secrets do YouTube"))
        layout.add_widget(self.yt_client_input)
        layout.add_widget(Label(text="Usuário do Instagram"))
        layout.add_widget(self.insta_user_input)
        layout.add_widget(Label(text="Senha do Instagram"))
        layout.add_widget(self.insta_pass_input)
        layout.add_widget(Label(text="Usuário do TikTok"))
        layout.add_widget(self.tiktok_user_input)
        layout.add_widget(Label(text="Senha do TikTok"))
        layout.add_widget(self.tiktok_pass_input)
        btn_save = Button(text="Salvar", size_hint_y=None, height=40)
        btn_save.bind(on_press=self.save_key)
        layout.add_widget(btn_save)
        back = Button(text="Voltar", size_hint_y=None, height=40)
        back.bind(on_press=lambda *_: setattr(self.manager, "current", "menu"))
        layout.add_widget(back)
        self.add_widget(layout)

    def save_key(self, *_):
        data = {
            "OPENAI_API_KEY": self.api_input.text.strip(),
            "YOUTUBE_CLIENT_SECRETS": self.yt_client_input.text.strip(),
            "INSTAGRAM_USER": self.insta_user_input.text.strip(),
            "INSTAGRAM_PASSWORD": self.insta_pass_input.text.strip(),
            "TIKTOK_USER": self.tiktok_user_input.text.strip(),
            "TIKTOK_PASSWORD": self.tiktok_pass_input.text.strip(),
        }
        os.environ.update(data)
        with open(".env", "w") as f:
            for k, v in data.items():
                f.write(f"{k}={v}\n")
        self.show_popup("Sucesso", "Configurações salvas")

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
        self.progress = ProgressBar(max=100, size_hint_y=None, height=30)
        self._loading = None

        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        btn_video = Button(text="Selecionar Vídeo")
        btn_video.bind(on_press=self.choose_file)
        layout.add_widget(btn_video)
        layout.add_widget(self.file_path)
        btn_transcribe = Button(text="Transcrever", size_hint_y=None, height=40)
        btn_transcribe.bind(on_press=self.transcribe)
        layout.add_widget(btn_transcribe)
        layout.add_widget(self.progress)
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

    def transcribe(self, *_):
        path = self.file_path.text
        if not path:
            self.show_popup("Erro", "Selecione o vídeo")
            return
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            self.show_popup("Erro", "Configure a chave da API")
            return
        openai.api_key = key
        self.update_progress(10)
        threading.Thread(target=self._transcribe, args=(path,), daemon=True).start()

    @mainthread
    def update_progress(self, value):
        self.progress.value = value

    def _transcribe(self, path: str):
        try:
            with open(path, "rb") as f:
                resp = openai.audio.transcriptions.create(file=f, model="whisper-1")
            text = resp.text if hasattr(resp, "text") else resp["text"]
            Clock.schedule_once(lambda *_: self.update_progress(50))
        except Exception as exc:
            Clock.schedule_once(lambda *_: self.show_popup("Erro", str(exc)))
            return
        Clock.schedule_once(lambda *_: setattr(self.transcript_input, "text", text))
        Clock.schedule_once(lambda *_: self.update_progress(100))

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
            logging.info("Prompt:\n%s\nResponse preview:\n%s", prompt, text[:200])
        except Exception as exc:
            self.hide_loading()
            self.show_popup("Erro", str(exc))
            logging.exception("OpenAI request failed for prompt:\n%s", prompt)
            self.show_popup("Erro", f"{exc.__class__.__name__}: {exc}")
            return
        self.hide_loading()
        self.show_suggestions(text)

    def show_suggestions(self, text):
        import re
        self.suggestions_box.clear_widgets()
        lines = re.findall(r"(\d{2}:\d{2}:\d{2}).*(\d{2}:\d{2}:\d{2})", text)
        for start, end in lines:
            btn = Button(text=f"{start} - {end}", size_hint_y=None, height=40)
            btn.bind(on_press=lambda _btn, s=start, e=end: self.preview_segment(s, e))
            self.suggestions_box.add_widget(btn)

    def preview_segment(self, start_str, end_str):
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
        self.show_preview(path, start, end)

    def show_preview(self, path, start, end):
        clip = VideoFileClip(path)
        duration = clip.duration
        clip.close()
        self.preview_start = TextInput(text=seconds_to_hms(start), size_hint_y=None, height=40)
        self.preview_end = TextInput(text=seconds_to_hms(end), size_hint_y=None, height=40)
        self.slider_start = Slider(min=0, max=duration, value=start)
        self.slider_end = Slider(min=0, max=duration, value=end)
        self.slider_start.bind(value=lambda _, v: setattr(self.preview_start, 'text', seconds_to_hms(v)))
        self.slider_end.bind(value=lambda _, v: setattr(self.preview_end, 'text', seconds_to_hms(v)))
        video = VideoPlayer(source=path, state='play')
        video.position = start
        video.bind(position=lambda inst, val: self._stop_at_end(inst, val, end))
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        layout.add_widget(video)
        row1 = BoxLayout(size_hint_y=None, height=40)
        row1.add_widget(Label(text='Início'))
        row1.add_widget(self.preview_start)
        row1.add_widget(self.slider_start)
        row2 = BoxLayout(size_hint_y=None, height=40)
        row2.add_widget(Label(text='Fim'))
        row2.add_widget(self.preview_end)
        row2.add_widget(self.slider_end)
        layout.add_widget(row1)
        layout.add_widget(row2)
        btn_save = Button(text='Salvar corte', size_hint_y=None, height=40)
        btn_cancel = Button(text='Cancelar', size_hint_y=None, height=40)
        btn_box = BoxLayout(size_hint_y=None, height=40)
        btn_box.add_widget(btn_save)
        btn_box.add_widget(btn_cancel)
        layout.add_widget(btn_box)
        popup = Popup(title='Prévia do corte', content=layout, size_hint=(0.9, 0.9))
        btn_cancel.bind(on_press=popup.dismiss)
        btn_save.bind(on_press=lambda *_: self.save_preview_cut(path))
        popup.open()
        self.preview_popup = popup

    def _stop_at_end(self, player, position, end):
        if position >= end:
            player.state = 'pause'

    def save_preview_cut(self, path):
        try:
            start = hms_to_seconds(self.preview_start.text)
            end = hms_to_seconds(self.preview_end.text)
        except ValueError:
            self.show_popup("Erro", "Tempos inválidos")
            return
        self.preview_popup.dismiss()
        threading.Thread(target=self._cut_video, args=(path, start, end), daemon=True).start()

    def cut_segment(self, start_str, end_str):
        self.preview_segment(start_str, end_str)

    def _cut_video(self, path, start, end):
        clip = VideoFileClip(path).subclip(start, end)
        start_str = seconds_to_hms(start)
        end_str = seconds_to_hms(end)
        out_dir = _get_platform_dir("gpt")
        out_file = os.path.join(
            out_dir,
            f"corte_gpt_{start_str.replace(':', '-')}_{end_str.replace(':', '-')}.mp4",
        )
        clip.write_videofile(out_file, codec="libx264", audio_codec="aac")
        Clock.schedule_once(lambda *_: self.show_popup("Sucesso", "Corte gerado"))
        Clock.schedule_once(self.hide_loading)
        Clock.schedule_once(lambda *_: ask_upload({"youtube": out_file}))

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
