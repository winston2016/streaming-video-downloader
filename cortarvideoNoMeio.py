import tkinter as tk
from tkinter import filedialog, messagebox
from moviepy.editor import VideoFileClip, vfx
import os

VIDEO_CODEC = "h264_nvenc" if os.getenv("VIDEO_HWACCEL") else "libx264"

def escolher_video():
    input_file = filedialog.askopenfilename(title="Selecione o arquivo de vídeo")
    if input_file:
        input_file_path.set(input_file)
        cortar_verticalmente()

def cortar_verticalmente():
    input_file = input_file_path.get()
    if not input_file:
        messagebox.showerror("Erro", "Nenhum arquivo de vídeo selecionado")
        return

    try:
        video = VideoFileClip(input_file)
        width, height = video.size
        metade_largura = width // 2

        output_file_esquerda = filedialog.asksaveasfilename(defaultextension=".mp4", title="Salvar parte esquerda como")
        if not output_file_esquerda:
            return
        output_file_direita = filedialog.asksaveasfilename(defaultextension=".mp4", title="Salvar parte direita como")
        if not output_file_direita:
            return

        video_esquerda = video.crop(x1=0, y1=0, x2=metade_largura, y2=height)
        video_direita = video.crop(x1=metade_largura, y1=0, x2=width, y2=height)

        video_esquerda.write_videofile(output_file_esquerda, codec=VIDEO_CODEC, audio_codec="aac")
        video_direita.write_videofile(output_file_direita, codec=VIDEO_CODEC, audio_codec="aac")

        messagebox.showinfo("Sucesso", f"Vídeos cortados salvos como {output_file_esquerda} e {output_file_direita}")
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao cortar o vídeo: {e}")

# Configuração da interface gráfica
root = tk.Tk()
root.title("Cortar Vídeo ao Meio Verticalmente")

input_file_path = tk.StringVar()

tk.Label(root, text="Arquivo de Vídeo:").grid(row=0, column=0, padx=10, pady=10)
tk.Entry(root, textvariable=input_file_path, width=50).grid(row=0, column=1, padx=10, pady=10)
tk.Button(root, text="Escolher Vídeo", command=escolher_video).grid(row=0, column=2, padx=10, pady=10)

cut_button = tk.Button(root, text="Cortar Vídeo ao Meio", command=cortar_verticalmente)
cut_button.grid(row=1, column=0, columnspan=3, pady=20)

root.mainloop()
