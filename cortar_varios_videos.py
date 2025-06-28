import tkinter as tk
from tkinter import filedialog, messagebox
from moviepy.editor import VideoFileClip
import datetime
import os

VIDEO_CODEC = "h264_nvenc" if os.getenv("VIDEO_HWACCEL") else "libx264"

def escolher_video():
    input_file = filedialog.askopenfilename(title="Selecione o arquivo de vídeo")
    if input_file:
        input_file_path.set(input_file)

def converter_para_hms(segundos):
    return str(datetime.timedelta(seconds=segundos))

def converter_para_segundos(hms):
    partes = hms.split(':')
    return int(partes[0]) * 3600 + int(partes[1]) * 60 + int(partes[2])

def cortar_videos():
    input_file = input_file_path.get()
    if not input_file:
        messagebox.showerror("Erro", "Nenhum arquivo de vídeo selecionado")
        return

    intervalos = lista_intervalos.get("1.0", tk.END).strip().splitlines()
    if not intervalos:
        messagebox.showerror("Erro", "Nenhum intervalo de tempo foi fornecido")
        return

    pasta_saida = filedialog.askdirectory(title="Selecione a pasta para salvar os cortes")
    if not pasta_saida:
        return

    try:
        for i, intervalo in enumerate(intervalos, start=1):
            try:
                inicio, fim = intervalo.split(" até ")
                start_time = converter_para_segundos(inicio.strip())
                end_time = converter_para_segundos(fim.strip())

                video = VideoFileClip(input_file).subclip(start_time, end_time)
                output_file = os.path.join(pasta_saida, f"corte_{i}.mp4")
                video.write_videofile(output_file, codec=VIDEO_CODEC, audio_codec="aac")
                video.close()
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao processar o intervalo '{intervalo}': {e}")
                continue

        messagebox.showinfo("Sucesso", f"Todos os vídeos foram cortados e salvos na pasta: {pasta_saida}")
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao cortar os vídeos: {e}")

# Configuração da interface gráfica
root = tk.Tk()
root.title("Cortar Múltiplos Vídeos")

input_file_path = tk.StringVar()

tk.Label(root, text="Arquivo de Vídeo:").grid(row=0, column=0, padx=10, pady=10)
tk.Entry(root, textvariable=input_file_path, width=50).grid(row=0, column=1, padx=10, pady=10)
tk.Button(root, text="Escolher Vídeo", command=escolher_video).grid(row=0, column=2, padx=10, pady=10)

tk.Label(root, text="Lista de Intervalos (ex.: HH:MM:SS até HH:MM:SS):").grid(row=1, column=0, columnspan=3, padx=10, pady=10)
lista_intervalos = tk.Text(root, width=60, height=15)
lista_intervalos.grid(row=2, column=0, columnspan=3, padx=10, pady=10)

tk.Button(root, text="Cortar Vídeos", command=cortar_videos).grid(row=3, column=0, columnspan=3, pady=20)

root.mainloop()