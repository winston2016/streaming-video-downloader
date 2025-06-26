from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.progressbar import ProgressBar
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.clock import Clock, mainthread
import yt_dlp
import instaloader
import threading
import re


# Configuração de cores e tamanho da janela
Window.size = (400, 300)
Window.clearcolor = (1, 1, 1, 1)

class DownloaderApp(App):
    def build(self):
        self.root = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Adicionando um título
        self.title_label = Label(text="Downloader de Vídeos", font_size='20sp', color=(0, 0, 0, 1))
        self.root.add_widget(self.title_label)

        self.url_label = Label(text="URL do vídeo:", color=(0, 0, 0, 1))
        self.root.add_widget(self.url_label)

        self.url_input = TextInput(multiline=False, size_hint_y=None, height=30)
        self.root.add_widget(self.url_input)

        self.download_button = Button(text="Baixar Vídeo", size_hint_y=None, height=50, background_color=(0.1, 0.5, 0.8, 1))
        self.download_button.bind(on_press=self.escolher_plataforma)
        self.root.add_widget(self.download_button)
        
        # Adicionando a barra de progresso
        self.progress_bar = ProgressBar(max=100, size_hint_y=None, height=30)
        self.root.add_widget(self.progress_bar)
        
        return self.root

    @mainthread
    def update_progress(self, value):
        self.progress_bar.value = value
        
        
    def show_popup(self, title, message):
        def create_popup(dt):
            popup_layout = BoxLayout(orientation='vertical', padding=10)
            popup_label = Label(text=message)
            popup_button = Button(text='Fechar', size_hint_y=None, height=40)
            popup_layout.add_widget(popup_label)
            popup_layout.add_widget(popup_button)
            popup = Popup(title=title, content=popup_layout, size_hint=(0.75, 0.5))
            popup_button.bind(on_press=popup.dismiss)
            popup.open()
        
        Clock.schedule_once(create_popup)

    def download_video_youtube(self, url):
        try:
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best',
                'outtmpl': '%(title)s.%(ext)s',  # Salvar com o título do vídeo e a extensão apropriada
                'quiet': True,  # Desativar log
                'no_warnings': True,  # Desativar avisos
                'logger': MyLogger(),  # Logger customizado
                'progress_hooks': [self.my_hook],  # Hook de progresso
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            Clock.schedule_once(lambda dt: self.show_popup("Sucesso", "Download concluído"))
        except Exception as ex:
            error_message = str(ex)
            Clock.schedule_once(lambda dt: self.show_popup("Erro", f"Erro ao baixar o vídeo: {error_message}"))

    def my_hook(self, d):
        if d['status'] == 'downloading':
            percent_str = re.sub(r'\x1b\[[0-9;]*m', '', d['_percent_str']).strip('%')
            progress = float(percent_str)
            self.update_progress(progress)
        elif d['status'] == 'finished':
            self.update_progress(100)
            print('Download completo.')
            

    def download_video_instagram(self, url):
        try:
            loader = instaloader.Instaloader()
            media_id = url.split('/')[-2]
            post = instaloader.Post.from_shortcode(loader.context, media_id)
            loader.download_post(post, target=post.owner_username)
            Clock.schedule_once(lambda dt: self.show_popup("Sucesso", "Download concluído"))
        except Exception as ex:
            error_message = str(ex)
            Clock.schedule_once(lambda dt: self.show_popup("Erro", f"Erro ao baixar o vídeo: {error_message}"))

    def download_video_tiktok(self, url):
        try:
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best',
                'outtmpl': 'tiktok_video.%(ext)s',
                'merge_output_format': 'mp4',
                'quiet': True,  # Desativar log
                'no_warnings': True,  # Desativar avisos
                'logger': MyLogger(),  # Logger customizado
                'progress_hooks': [self.my_hook],  # Hook de progresso
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            Clock.schedule_once(lambda dt: self.show_popup("Sucesso", "Download concluído"))
        except Exception as ex:
            error_message = str(ex)
            Clock.schedule_once(lambda dt: self.show_popup("Erro", f"Erro ao baixar o vídeo: {error_message}"))

    def escolher_plataforma(self, instance):
        self.progress_bar.value = 0
        url = self.url_input.text
        if "youtube" in url:
            threading.Thread(target=self.download_video_youtube, args=(url,)).start()
        elif "instagram" in url:
            threading.Thread(target=self.download_video_instagram, args=(url,)).start()
        elif "tiktok" in url:
            threading.Thread(target=self.download_video_tiktok, args=(url,)).start()

class MyLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)

if __name__ == '__main__':
    DownloaderApp().run()
