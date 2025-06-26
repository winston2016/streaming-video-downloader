from moviepy.editor import VideoFileClip, CompositeVideoClip
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import threading
import numpy as np

def resize_with_lanczos(image, new_size):
    pil_image = Image.fromarray(image)
    resized_image = pil_image.resize(new_size[::-1], Image.LANCZOS)
    return np.array(resized_image)

def create_tiktok_video(video_top_path, video_bottom_path, output_path, audio_from_top, progress_var, on_complete):
    # Atualiza a barra de progresso
    def update_progress(progress):
        progress_var.set(progress)
        root.update_idletasks()

    try:
        # Resolução sugerida pelo TikTok para cada vídeo empilhado
        target_width = 720
        target_height = 640  # Metade da altura de 1280 px para empilhamento vertical

        # Carregar os vídeos
        video_top = VideoFileClip(video_top_path)
        video_bottom = VideoFileClip(video_bottom_path)

        update_progress(20)

        # Ajustar a duração dos vídeos para que o mais curto se repita
        if audio_from_top:
            video_bottom = video_bottom.loop(duration=video_top.duration)
        else:
            video_top = video_top.loop(duration=video_bottom.duration)

        update_progress(40)

        # Redimensionar vídeos para a resolução alvo
        video_top = video_top.fl_image(lambda image: resize_with_lanczos(image, (target_width, target_height)))
        video_bottom = video_bottom.fl_image(lambda image: resize_with_lanczos(image, (target_width, target_height)))

        update_progress(60)

        # Combinar vídeos verticalmente
        final_clip = CompositeVideoClip([
            video_top.set_position(("center", "top")),
            video_bottom.set_position(("center", video_top.h))
        ], size=(target_width, target_height * 2))

        update_progress(80)

        # Selecionar áudio
        if audio_from_top:
            final_clip = final_clip.set_audio(video_top.audio)
        else:
            final_clip = final_clip.set_audio(video_bottom.audio)

        # Exportar vídeo final
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")

        update_progress(100)
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao criar vídeo: {str(e)}")
    finally:
        on_complete()

class VideoEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Editor for TikTok")

        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=1)

        canvas = tk.Canvas(main_frame)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        scrollbar = tk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        second_frame = tk.Frame(canvas)
        canvas.create_window((0,0), window=second_frame, anchor="nw")

        self.video_top_path = ""
        self.video_bottom_path = ""

        self.top_video_label = tk.Label(second_frame, text="Selecione o vídeo de cima")
        self.top_video_label.pack()

        self.top_video_button = tk.Button(second_frame, text="Escolher Vídeo de Cima", command=self.choose_top_video)
        self.top_video_button.pack()

        self.bottom_video_label = tk.Label(second_frame, text="Selecione o vídeo de baixo")
        self.bottom_video_label.pack()

        self.bottom_video_button = tk.Button(second_frame, text="Escolher Vídeo de Baixo", command=self.choose_bottom_video)
        self.bottom_video_button.pack()

        self.audio_option = tk.BooleanVar()
        self.audio_option.set(True)
        self.audio_top_radio = tk.Radiobutton(second_frame, text="Usar áudio do vídeo de cima", variable=self.audio_option, value=True)
        self.audio_top_radio.pack()

        self.audio_bottom_radio = tk.Radiobutton(second_frame, text="Usar áudio do vídeo de baixo", variable=self.audio_option, value=False)
        self.audio_bottom_radio.pack()

        self.create_button = tk.Button(second_frame, text="Criar Vídeo", command=self.create_video)
        self.create_button.pack()

        self.top_video_frame = tk.Label(second_frame)
        self.top_video_frame.pack()

        self.bottom_video_frame = tk.Label(second_frame)
        self.bottom_video_frame.pack()

        self.progress_var = tk.DoubleVar()
        self.progress_bar = tk.Scale(second_frame, variable=self.progress_var, from_=0, to=100, orient="horizontal", length=400, label="Progresso")
        self.progress_bar.pack()

    def choose_top_video(self):
        self.video_top_path = filedialog.askopenfilename(title="Escolha o vídeo de cima")
        if self.video_top_path:
            self.display_video_frame(self.video_top_path, self.top_video_frame)

    def choose_bottom_video(self):
        self.video_bottom_path = filedialog.askopenfilename(title="Escolha o vídeo de baixo")
        if self.video_bottom_path:
            self.display_video_frame(self.video_bottom_path, self.bottom_video_frame)

    def display_video_frame(self, video_path, label):
        # Extrair o primeiro frame do vídeo
        video = VideoFileClip(video_path)
        frame = video.get_frame(0)
        image = Image.fromarray(frame)
        image = image.resize((400, 300), Image.LANCZOS)
        photo = ImageTk.PhotoImage(image)

        label.config(image=photo)
        label.image = photo  # Manter referência para evitar garbage collection

    def on_video_creation_complete(self):
        messagebox.showinfo("Sucesso", "Vídeo criado com sucesso!")

    def create_video(self):
        if not self.video_top_path or not self.video_bottom_path:
            messagebox.showerror("Erro", "Por favor, selecione ambos os vídeos.")
            return

        output_path = filedialog.asksaveasfilename(defaultextension=".mp4", title="Salvar vídeo como")
        if output_path:
            audio_from_top = self.audio_option.get()
            threading.Thread(target=create_tiktok_video, args=(self.video_top_path, self.video_bottom_path, output_path, audio_from_top, self.progress_var, self.on_video_creation_complete)).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoEditorApp(root)
    root.mainloop()
