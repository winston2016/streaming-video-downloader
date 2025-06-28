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
import json

VIDEO_CODEC = "h264_nvenc" if os.getenv("VIDEO_HWACCEL") else "libx264"

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
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from urllib.parse import urlparse
import re
import openai
from dotenv import load_dotenv
import whisper

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
from moviepy.editor import VideoFileClip, concatenate_videoclips
from PIL import Image

# Pillow >=10 removed the Image.ANTIALIAS constant used by MoviePy.
# Provide a fallback for compatibility with older MoviePy versions.
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

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


def parse_suggestions(text):
    """Parse ChatGPT response into a list of suggestions."""
    try:
        data = json.loads(text)
    except Exception:
        data = None

    suggestions = []
    if isinstance(data, list):
        for item in data:
            suggestions.append(
                {
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "start": item.get("start", ""),
                    "end": item.get("end", ""),
                }
            )
        if suggestions:
            return suggestions

    for line in text.splitlines():
        m = re.search(
            r"(\d{2}:\d{2}:\d{2}).*?(\d{2}:\d{2}:\d{2})(?:\s*-?\s*(.*))?",
            line,
        )
        if not m:
            continue
        start, end, title = m.group(1), m.group(2), (m.group(3) or "").strip()
        if not title:
            title = f"Corte {len(suggestions) + 1}"
        suggestions.append({"start": start, "end": end, "title": title, "description": ""})
    return suggestions


def extract_instagram_shortcode(url: str) -> str:
    """Return the shortcode from an Instagram URL.

    Raises ``ValueError`` if no shortcode can be determined.
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        raise ValueError("URL inválida")
    shortcode = path.split("/")[-1]
    if not shortcode or shortcode.startswith("?"):
        raise ValueError("URL inválida")
    # remove any possible trailing parameters
    shortcode = re.split(r"[/?#]", shortcode)[0]
    if not shortcode:
        raise ValueError("URL inválida")
    return shortcode


class MyLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)


def open_post_screen(path):
    """Open the posting screen pre-filled with ``path``."""
    app = App.get_running_app()
    if not app:
        return
    try:
        screen = app.root.get_screen("post")
    except Exception:
        return
    screen.set_video(path)
    app.root.current = "post"


def ask_upload(paths):
    # Deprecated popup used in older flows. Now it simply opens the posting
    # screen for the generated file.
    path = next(iter(paths.values())) if paths else ""
    open_post_screen(path)


def upload_videos(paths, descriptions=None):
    """Upload video to available platforms using provided descriptions."""
    from uploader import youtube, instagram, tiktok, facebook, x
    if "youtube" in paths:
        try:
            youtube.upload_video(paths["youtube"], title="Corte")
        except Exception as exc:
            print("YouTube upload failed:", exc)
    if "instagram" in paths:
        try:
            caption = "" if descriptions is None else descriptions.get("instagram", "")
            instagram.upload_video(paths["instagram"], caption=caption)
        except Exception as exc:
            print("Instagram upload failed:", exc)
    if "tiktok" in paths:
        try:
            tiktok.upload_video(paths["tiktok"])
        except Exception as exc:
            print("TikTok upload failed:", exc)
    if "facebook" in paths:
        try:
            facebook.upload_video(paths["facebook"], description=descriptions.get("facebook", "") if descriptions else "")
        except Exception as exc:
            print("Facebook upload failed:", exc)
    if "x" in paths:
        try:
            x.upload_video(paths["x"], description=descriptions.get("x", "") if descriptions else "")
        except Exception as exc:
            print("X upload failed:", exc)


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
        btn_saved = Button(text="Sugestões Salvas")
        btn_saved.bind(on_press=lambda *_: setattr(self.manager, "current", "suggestions"))
        layout.add_widget(btn_saved)
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
            layout.add_widget(Label(text="Aguarde..."))
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
        cookie_file = os.getenv("TIKTOK_COOKIES_FILE")
        cookie_browser = os.getenv("TIKTOK_COOKIES_BROWSER")
        if not cookie_file and not cookie_browser:
            Clock.schedule_once(
                lambda *_: self.show_popup(
                    "Erro",
                    "TikTok requer autenticação. Defina TIKTOK_COOKIES_FILE ou TIKTOK_COOKIES_BROWSER no .env",
                )
            )
            return
        if cookie_file:
            if not os.path.exists(cookie_file):
                Clock.schedule_once(
                    lambda *_: self.show_popup(
                        "Erro", f"Arquivo de cookies não encontrado: {cookie_file}"
                    )
                )
                return
            opts["cookiefile"] = cookie_file
        elif cookie_browser:
            opts["cookiesfrombrowser"] = cookie_browser
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                ydl.download([url])
            except yt_dlp.utils.DownloadError as exc:
                msg = str(exc)
                if "login" in msg.lower():
                    msg += "\nDefina TIKTOK_COOKIES_FILE ou TIKTOK_COOKIES_BROWSER no .env"
                Clock.schedule_once(lambda *_: self.show_popup("Erro", msg))
                return
        Clock.schedule_once(lambda *_: self.show_popup("Sucesso", "Download concluído"))

    def _download_instagram(self, url):
        path = _get_platform_dir("instagram")
        loader = instaloader.Instaloader(dirname_pattern=path, filename_pattern="{shortcode}")
        try:
            shortcode = extract_instagram_shortcode(url)
        except ValueError as exc:
            Clock.schedule_once(lambda *_: self.show_popup("Erro", str(exc)))
            return
        try:
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            loader.download_post(post, target="post")
        except Exception as exc:
            Clock.schedule_once(lambda *_: self.show_popup("Erro", f"Falha no download: {exc}"))
            return
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



class PostScreen(Screen):
    """Screen for selecting a video and generating descriptions for posting."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.file_path = TextInput(hint_text="Caminho do vídeo", readonly=True, size_hint_y=None, height=40)
        self.niche_input = TextInput(hint_text="Nicho/tema", size_hint_y=None, height=40)
        self.tiktok_desc = TextInput(hint_text="Descrição TikTok", size_hint_y=None, height=80)
        self.instagram_desc = TextInput(hint_text="Descrição Instagram", size_hint_y=None, height=80)
        self.facebook_desc = TextInput(hint_text="Descrição Facebook", size_hint_y=None, height=80)
        self.x_desc = TextInput(hint_text="Descrição X", size_hint_y=None, height=80)

        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        btn_video = Button(text="Selecionar Vídeo")
        btn_video.bind(on_press=self.choose_file)
        layout.add_widget(btn_video)
        layout.add_widget(self.file_path)
        layout.add_widget(self.niche_input)
        btn_gen = Button(text="Gerar Descrições", size_hint_y=None, height=40)
        btn_gen.bind(on_press=self.generate_descriptions)
        layout.add_widget(btn_gen)
        layout.add_widget(self.tiktok_desc)
        layout.add_widget(self.instagram_desc)
        layout.add_widget(self.facebook_desc)
        layout.add_widget(self.x_desc)
        btn_post = Button(text="Postar", size_hint_y=None, height=40)
        btn_post.bind(on_press=self.post_video)
        layout.add_widget(btn_post)
        back = Button(text="Voltar", size_hint_y=None, height=40)
        back.bind(on_press=lambda *_: setattr(self.manager, "current", "menu"))
        layout.add_widget(back)
        self.add_widget(layout)

    def set_video(self, path):
        self.file_path.text = path

    def choose_file(self, *_):
        if filedialog is None:
            return
        root = Tk(); root.withdraw()
        path = filedialog.askopenfilename(title="Selecione o vídeo")
        root.destroy()
        if path:
            self.file_path.text = path

    def generate_descriptions(self, *_):
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            self.show_popup("Erro", "Configure a chave da API")
            return
        if not self.niche_input.text.strip():
            self.show_popup("Erro", "Informe o nicho/tema")
            return
        openai.api_key = key
        prompt = (
            "Crie descrições curtas e engajantes para um vídeo sobre '"
            + self.niche_input.text.strip()
            + "'. Use o que está em alta no momento.\n"
            "Responda no formato:\n"
            "TikTok: ...\nInstagram: ...\nFacebook: ...\nX: ..."
        )
        try:
            completion = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
            )
            text = completion.choices[0].message.content
        except Exception as exc:
            self.show_popup("Erro", str(exc))
            return
        for line in text.splitlines():
            if line.lower().startswith("tiktok:"):
                self.tiktok_desc.text = line.split(":", 1)[1].strip()
            elif line.lower().startswith("instagram:"):
                self.instagram_desc.text = line.split(":", 1)[1].strip()
            elif line.lower().startswith("facebook:"):
                self.facebook_desc.text = line.split(":", 1)[1].strip()
            elif line.lower().startswith("x:"):
                self.x_desc.text = line.split(":", 1)[1].strip()

    def post_video(self, *_):
        path = self.file_path.text
        if not path:
            self.show_popup("Erro", "Selecione o vídeo")
            return
        descriptions = {
            "tiktok": self.tiktok_desc.text,
            "instagram": self.instagram_desc.text,
            "facebook": self.facebook_desc.text,
            "x": self.x_desc.text,
        }
        paths = {k: path for k, v in descriptions.items() if v}
        if not paths:
            self.show_popup("Aviso", "Nenhuma plataforma selecionada")
            return
        threading.Thread(target=upload_videos, args=(paths, descriptions), daemon=True).start()
        self.show_popup("Info", "Upload iniciado")

    def show_popup(self, title, message):
        popup_layout = BoxLayout(orientation="vertical", padding=10)
        popup_layout.add_widget(Label(text=message))
        btn = Button(text="Fechar", size_hint_y=None, height=40)
        popup_layout.add_widget(btn)
        popup = Popup(title=title, content=popup_layout, size_hint=(0.75, 0.5))
        btn.bind(on_press=popup.dismiss)
        popup.open()



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
            layout.add_widget(Label(text="Aguarde..."))
            self._loading = ModalView(size_hint=(0.5, 0.3), auto_dismiss=False)
            self._loading.add_widget(layout)
        self._loading.open()
    def hide_loading(self, *_):
        if self._loading is not None:
            self._loading.dismiss()
            self._loading = None

    def _cut_video(self, path, start, end):
        try:
            clip = VideoFileClip(path)
        except Exception as exc:
            Clock.schedule_once(lambda *_, exc=exc: self.show_popup("Erro", str(exc)))
            Clock.schedule_once(self.hide_loading)
            return

        duration = clip.duration
        if start >= end or start < 0 or end > duration:
            clip.close()
            Clock.schedule_once(
                lambda *_: self.show_popup(
                    "Erro", "Tempos fora da duração do vídeo"
                )
            )
            Clock.schedule_once(self.hide_loading)
            return

        clip = clip.subclip(start, end)

        # Keep the original resolution and store the cut alongside the source
        # video. The output file name includes the selected time span and the
        # original file name to make it easier to identify.
        start_str = seconds_to_hms(start).replace(":", "-")
        end_str = seconds_to_hms(end).replace(":", "-")
        base_dir = os.path.dirname(path)
        original_name = os.path.basename(path)
        out_file = os.path.join(
            base_dir, f"corte_{start_str}_{end_str}_{original_name}"
        )

        ext = os.path.splitext(out_file)[1].lower()
        if ext == ".webm":
            video_codec = "libvpx"
            audio_codec = "libvorbis"
        else:
            video_codec = VIDEO_CODEC
            audio_codec = "aac"

        clip.write_videofile(out_file, codec=video_codec, audio_codec=audio_codec)

        Clock.schedule_once(lambda *_: self.update_progress(100))
        Clock.schedule_once(
            lambda *_: self.show_popup("Sucesso", "Corte gerado")
        )
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
        self.niche_input = TextInput(
            text="Melhores lances de futebol",
            hint_text="Nicho/tema",
            size_hint_y=None,
            height=40,
        )
        self.suggestions_box = BoxLayout(orientation="vertical", size_hint_y=None)
        self.progress = ProgressBar(max=100, size_hint_y=None, height=30)
        self._loading = None
        self.cut_counter = 1
        self.generated_cuts = []
        self.current_suggestions = []

        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        btn_video = Button(text="Selecionar Vídeo")
        btn_video.bind(on_press=self.choose_file)
        layout.add_widget(btn_video)
        layout.add_widget(self.file_path)
        layout.add_widget(self.progress)
        layout.add_widget(self.niche_input)
        btn_analyze = Button(text="Gerar Sugestões", size_hint_y=None, height=40)
        btn_analyze.bind(on_press=self.generate)
        layout.add_widget(btn_analyze)
        layout.add_widget(Label(text="Sugestões:"))
        layout.add_widget(self.suggestions_box)
        btn_merge = Button(text="Mesclar Cortes", size_hint_y=None, height=40)
        btn_merge.bind(on_press=self.merge_cuts)
        layout.add_widget(btn_merge)
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

    @mainthread
    def update_progress(self, value):
        self.progress.value = value

    # Loading helpers -----------------------------------------------------
    def show_loading(self):
        if self._loading is None:
            layout = BoxLayout(orientation="vertical", padding=10)
            layout.add_widget(Label(text="Aguarde..."))
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
        path = self.file_path.text
        if not path:
            self.show_popup("Erro", "Selecione o vídeo")
            return
        self.show_loading()
        openai.api_key = key
        threading.Thread(target=self._generate_thread, args=(path,), daemon=True).start()

    def _generate_thread(self, path: str):
        try:
            model = whisper.load_model("base")
            result = model.transcribe(path, fp16=False)
            segments = result["segments"]
            transcript = "\n".join(
                f"{seconds_to_hms(s['start'])}-{seconds_to_hms(s['end'])} {s['text'].strip()}"
                for s in segments
            )
            Clock.schedule_once(lambda *_: self.update_progress(50))

            clip = VideoFileClip(path)
            duration = seconds_to_hms(clip.duration)
            clip.close()

            prompt = (
                "Sugira cortes interessantes no formato JSON com os campos "
                "title, description, start e end, baseados no nicho '"
                + self.niche_input.text
                + "'. O vídeo tem duração "
                + duration
                + ". Use quantos cortes forem relevantes.\n"
                + transcript
                + "\nReturn a JSON array of objects with `title`, `description`, `start`, `end`."
            )

            completion = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
            )
            text = completion.choices[0].message.content
            logging.info("Prompt:\n%s\nResponse preview:\n%s", prompt, text[:200])
            try:
                suggestions = json.loads(text)
            except Exception as exc:
                logging.exception("JSON parsing failed")
                Clock.schedule_once(lambda *_, exc=exc: self._generate_failed(exc))
                return
            date_dir = Path("videos") / datetime.now().strftime("%Y-%m-%d")
            date_dir.mkdir(parents=True, exist_ok=True)
            with open(date_dir / "suggestions.json", "w", encoding="utf-8") as f:
                json.dump({"file": path, "suggestions": suggestions}, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logging.exception("OpenAI request failed")
            Clock.schedule_once(lambda *_, exc=exc: self._generate_failed(exc))
            return
        Clock.schedule_once(lambda *_: self._generate_done(suggestions))

    def _generate_failed(self, exc):
        self.hide_loading()
        self.show_popup("Erro", str(exc))

    def _generate_done(self, suggestions):
        self.hide_loading()
        self.update_progress(100)
        self.show_suggestions(suggestions)

    def show_suggestions(self, suggestions):
        """Display buttons for each suggestion and store their metadata."""
        self.suggestions_box.clear_widgets()
        self.current_suggestions = []
        for idx, item in enumerate(suggestions, start=1):
            start_raw = item.get("start")
            end_raw = item.get("end")
            try:
                start_sec = float(start_raw)
                end_sec = float(end_raw)
            except (TypeError, ValueError):
                start_sec = hms_to_seconds(str(start_raw))
                end_sec = hms_to_seconds(str(end_raw))
            btn = Button(
                text=f"{idx}. {start_raw} - {end_raw}",
                size_hint_y=None,
                height=40,
            )
            btn.bind(on_press=lambda _btn, s=start_sec, e=end_sec: self.preview_segment(s, e))
            self.suggestions_box.add_widget(btn)
            self.current_suggestions.append(
                {
                    "start": start_sec,
                    "end": end_sec,
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                }
            )

    def preview_segment(self, start, end):
        """Open the preview popup for the selected time span."""
        path = self.file_path.text
        if not path:
            self.show_popup("Erro", "Selecione o vídeo")
            return
        try:
            start_sec = float(start)
            end_sec = float(end)
        except (TypeError, ValueError):
            self.show_popup("Erro", "Tempos inválidos")
            return
        self.show_preview(path, start_sec, end_sec)

    def show_preview(self, path, start, end):
        try:
            clip = VideoFileClip(path)
        except Exception as exc:
            self.show_popup("Erro", str(exc))
            return

        duration = clip.duration
        clip.close()

        if start >= end or start < 0 or end > duration:
            self.show_popup("Erro", "Tempos fora da duração do vídeo")
            return
        self.preview_start = TextInput(text=seconds_to_hms(start), size_hint_y=None, height=40)
        self.preview_end = TextInput(text=seconds_to_hms(end), size_hint_y=None, height=40)
        self.slider_start = Slider(min=0, max=duration, value=start)
        self.slider_end = Slider(min=0, max=duration, value=end)
        self.slider_start.bind(value=lambda _, v: setattr(self.preview_start, 'text', seconds_to_hms(v)))
        self.slider_end.bind(value=lambda _, v: setattr(self.preview_end, 'text', seconds_to_hms(v)))
        # Use an absolute URI to improve cross-platform compatibility
        video = VideoPlayer(source=Path(path).absolute().as_uri(), state='play')
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
        self.preview_popup = popup
        btn_cancel.bind(on_press=popup.dismiss)
        btn_save.bind(on_press=lambda *_: self.save_preview_cut(path))
        popup.open()



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

    def cut_segment(self, start, end):
        self.preview_segment(start, end)

    def _cut_video(self, path, start, end):
        try:
            clip = VideoFileClip(path)
        except Exception as exc:
            Clock.schedule_once(lambda *_, exc=exc: self.show_popup("Erro", str(exc)))
            Clock.schedule_once(self.hide_loading)
            return

        duration = clip.duration
        if start >= end or start < 0 or end > duration:
            clip.close()
            Clock.schedule_once(
                lambda *_: self.show_popup(
                    "Erro", "Tempos fora da duração do vídeo"
                )
            )
            Clock.schedule_once(self.hide_loading)
            return

        clip = clip.subclip(start, end)
        start_str = seconds_to_hms(start)
        end_str = seconds_to_hms(end)
        out_dir = _get_platform_dir("gpt")
        original_name = os.path.basename(path)
        out_file = os.path.join(
            out_dir,
            f"corte_{self.cut_counter}_gpt_{start_str.replace(':', '-')}_{end_str.replace(':', '-')}_{original_name}",
        )
        ext = os.path.splitext(out_file)[1].lower()
        if ext == ".webm":
            video_codec = "libvpx"
            audio_codec = "libvorbis"
        else:
            video_codec = VIDEO_CODEC
            audio_codec = "aac"

        clip.write_videofile(out_file, codec=video_codec, audio_codec=audio_codec)
        self.cut_counter += 1
        self.generated_cuts.append(out_file)
        Clock.schedule_once(lambda *_: self.show_popup("Sucesso", "Corte gerado"))
        Clock.schedule_once(self.hide_loading)
        Clock.schedule_once(lambda *_: open_post_screen(out_file))

    def merge_cuts(self, *_):
        if not self.generated_cuts:
            self.show_popup("Aviso", "Nenhum corte para mesclar")
            return

        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        grid = GridLayout(cols=1, size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        checks = []
        for path in self.generated_cuts:
            row = BoxLayout(size_hint_y=None, height=40)
            chk = CheckBox(active=True)
            row.add_widget(chk)
            row.add_widget(Label(text=os.path.basename(path)))
            grid.add_widget(row)
            checks.append((chk, path))
        layout.add_widget(grid)
        btn_merge = Button(text="Mesclar", size_hint_y=None, height=40)
        btn_cancel = Button(text="Cancelar", size_hint_y=None, height=40)
        row_btn = BoxLayout(size_hint_y=None, height=40)
        row_btn.add_widget(btn_merge)
        row_btn.add_widget(btn_cancel)
        layout.add_widget(row_btn)
        popup = Popup(title="Selecionar Cortes", content=layout, size_hint=(0.8, 0.8))

        def do_merge(_):
            popup.dismiss()
            selected = [p for c, p in checks if c.active]
            if selected:
                threading.Thread(target=self._merge_files, args=(selected,), daemon=True).start()

        btn_merge.bind(on_press=do_merge)
        btn_cancel.bind(on_press=popup.dismiss)
        popup.open()

    def _merge_files(self, paths):
        try:
            clips = [VideoFileClip(p) for p in paths]
            final = concatenate_videoclips(clips)
            out_dir = os.path.dirname(paths[0])
            out_file = os.path.join(out_dir, f"merged_{datetime.now().strftime('%H-%M-%S')}.mp4")
            final.write_videofile(out_file, codec=VIDEO_CODEC, audio_codec="aac")
            for clip in clips:
                clip.close()
            final.close()
            Clock.schedule_once(lambda *_: self.show_popup("Sucesso", f"Mesclado em {out_file}"))
        except Exception as exc:
            Clock.schedule_once(lambda *_, exc=exc: self.show_popup("Erro", str(exc)))

    def show_popup(self, title, message):
        popup_layout = BoxLayout(orientation="vertical", padding=10)
        popup_layout.add_widget(Label(text=message))
        btn = Button(text="Fechar", size_hint_y=None, height=40)
        popup_layout.add_widget(btn)
        popup = Popup(title=title, content=popup_layout, size_hint=(0.75, 0.5))
        btn.bind(on_press=popup.dismiss)
        popup.open()


class SuggestionsScreen(Screen):
    """Display saved suggestions from ``suggestions.json`` files."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.suggestions_box = BoxLayout(orientation="vertical", size_hint_y=None)
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        layout.add_widget(Label(text="Sugestões Salvas", font_size="20sp"))
        layout.add_widget(self.suggestions_box)
        btn_refresh = Button(text="Recarregar", size_hint_y=None, height=40)
        btn_refresh.bind(on_press=self.load_suggestions)
        layout.add_widget(btn_refresh)
        back = Button(text="Voltar", size_hint_y=None, height=40)
        back.bind(on_press=lambda *_: setattr(self.manager, "current", "menu"))
        layout.add_widget(back)
        self.add_widget(layout)
        Clock.schedule_once(self.load_suggestions, 0)

    def load_suggestions(self, *_):
        self.suggestions_box.clear_widgets()
        root = Path("videos")
        if not root.exists():
            return
        for date_dir in sorted(root.iterdir()):
            sug_file = date_dir / "gpt" / "suggestions.json"
            if not sug_file.exists():
                continue
            try:
                with open(sug_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as exc:
                print("Erro ao ler", sug_file, exc)
                continue
            video_path = data.get("file", "")
            for item in data.get("suggestions", []):
                title = item.get("title", f"{item['start']} - {item['end']}")
                desc = item.get("description", "")
                text = title if not desc else f"{title} - {desc}"
                row = BoxLayout(size_hint_y=None, height=40)
                row.add_widget(Label(text=text))
                btn_prev = Button(text="Prévia", size_hint_x=None, width=80)
                btn_cut = Button(text="Cortar", size_hint_x=None, width=80)
                start = item["start"]
                end = item["end"]
                btn_prev.bind(on_press=lambda _, p=video_path, s=start, e=end: self.preview(p, s, e))
                btn_cut.bind(on_press=lambda _, p=video_path, s=start, e=end: self.cut(p, s, e))
                row.add_widget(btn_prev)
                row.add_widget(btn_cut)
                self.suggestions_box.add_widget(row)

    def preview(self, path, start, end):
        auto = self.manager.get_screen("auto")
        auto.file_path.text = path
        try:
            s = float(start)
            e = float(end)
        except (TypeError, ValueError):
            s = hms_to_seconds(str(start))
            e = hms_to_seconds(str(end))
        auto.preview_segment(s, e)

    def cut(self, path, start, end):
        auto = self.manager.get_screen("auto")
        auto.show_loading()
        try:
            s = float(start)
            e = float(end)
        except (TypeError, ValueError):
            s = hms_to_seconds(str(start))
            e = hms_to_seconds(str(end))
        threading.Thread(target=auto._cut_video, args=(path, s, e), daemon=True).start()
# App ---------------------------------------------------------------------

class VideoApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(DownloadScreen(name="download"))
        sm.add_widget(CutScreen(name="cut"))
        sm.add_widget(AutoCutScreen(name="auto"))
        sm.add_widget(SuggestionsScreen(name="suggestions"))
        sm.add_widget(PostScreen(name="post"))
        sm.add_widget(ConfigScreen(name="config"))
        return sm


if __name__ == "__main__":
    VideoApp().run()
