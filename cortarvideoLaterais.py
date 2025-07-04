import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from moviepy.editor import VideoFileClip
from video_cut_utils import crop_sides

class VideoCropperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Cropper")

        self.label = tk.Label(root, text="Escolha o vídeo para cortar")
        self.label.pack(pady=10)

        self.select_button = tk.Button(root, text="Selecionar Vídeo", command=self.select_video_file)
        self.select_button.pack(pady=5)

        self.progress_label = tk.Label(root, text="")
        self.progress_label.pack(pady=5)

        self.progress_bar = ttk.Progressbar(root, length=300, mode='determinate')
        self.progress_bar.pack(pady=5)

        self.save_button = tk.Button(root, text="Salvar Vídeo Cortado", command=self.save_video_file, state=tk.DISABLED)
        self.save_button.pack(pady=5)

        self.input_video_path = ""
        self.output_video_path = ""

    def select_video_file(self):
        self.input_video_path = filedialog.askopenfilename(title="Selecione o vídeo", filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")])
        if self.input_video_path:
            self.label.config(text="Vídeo selecionado: " + self.input_video_path)
            self.save_button.config(state=tk.NORMAL)
        else:
            self.label.config(text="Escolha o vídeo para cortar")

    def save_video_file(self):
        self.output_video_path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")])
        if self.output_video_path:
            self.progress_label.config(text="Processando...")
            self.root.update_idletasks()
            self.crop_video()

    def crop_video(self):
        video = VideoFileClip(self.input_video_path)
        width, _ = video.size
        left = 200
        right = width - 200
        video.close()

        self.progress_bar['maximum'] = 100
        crop_sides(self.input_video_path, self.output_video_path, left, right)
        self.progress_bar['value'] = 100

        messagebox.showinfo("Concluído", "O vídeo foi cortado e salvo com sucesso!")
        self.progress_label.config(text="Processo concluído!")
        self.progress_bar['value'] = 0

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoCropperApp(root)
    root.mainloop()
