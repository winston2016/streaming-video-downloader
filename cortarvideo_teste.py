import tkinter as tk
from tkinter import filedialog, messagebox
from moviepy.editor import VideoFileClip
import datetime

def escolher_video():
    input_file = filedialog.askopenfilename(title="Selecione o arquivo de vídeo")
    if input_file:
        input_file_path.set(input_file)
        video = VideoFileClip(input_file)
        video_duration.set(int(video.duration))
        end_time.set(int(video.duration))
        start_slider.config(to=int(video.duration))
        end_slider.config(to=int(video.duration))
        start_slider.set(0)
        end_slider.set(int(video.duration))
        atualizar_inputs()

def converter_para_hms(segundos):
    return str(datetime.timedelta(seconds=segundos))

def converter_para_segundos(hms):
    partes = hms.split(':')
    return int(partes[0]) * 3600 + int(partes[1]) * 60 + int(partes[2])

def atualizar_inputs(event=None):
    start = start_slider.get()
    end = end_slider.get()
    start_time_entry.delete(0, tk.END)
    end_time_entry.delete(0, tk.END)
    start_time_entry.insert(0, converter_para_hms(start))
    end_time_entry.insert(0, converter_para_hms(end))

def atualizar_sliders(event=None):
    try:
        start = converter_para_segundos(start_time_entry.get())
        end = converter_para_segundos(end_time_entry.get())
        start_slider.set(start)
        end_slider.set(end)
    except ValueError:
        messagebox.showerror("Erro", "Por favor, insira tempos válidos no formato HH:MM:SS")

def ajustar_tempo(entry, ajuste):
    try:
        tempo_atual = converter_para_segundos(entry.get())
        tempo_novo = max(0, tempo_atual + ajuste)
        entry.delete(0, tk.END)
        entry.insert(0, converter_para_hms(tempo_novo))
        atualizar_sliders()
    except ValueError:
        messagebox.showerror("Erro", "Por favor, insira tempos válidos no formato HH:MM:SS")

def cortar_video():
    input_file = input_file_path.get()
    if not input_file:
        messagebox.showerror("Erro", "Nenhum arquivo de vídeo selecionado")
        return

    try:
        start_time = converter_para_segundos(start_time_entry.get())
        end_time = converter_para_segundos(end_time_entry.get())
    except ValueError:
        messagebox.showerror("Erro", "Por favor, insira tempos válidos no formato HH:MM:SS")
        return

    output_file = filedialog.asksaveasfilename(defaultextension=".mp4", title="Salvar vídeo cortado como")
    if not output_file:
        return

    try:
        video = VideoFileClip(input_file).subclip(start_time, end_time)
        video.write_videofile(output_file, codec="libx264", audio_codec="aac")
        messagebox.showinfo("Sucesso", f"Vídeo cortado salvo como {output_file}")
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao cortar o vídeo: {e}")

# Configuração da interface gráfica
root = tk.Tk()
root.title("Cortar Vídeo")

input_file_path = tk.StringVar()
video_duration = tk.IntVar()
start_time = tk.StringVar()
end_time = tk.StringVar()

tk.Label(root, text="Arquivo de Vídeo:").grid(row=0, column=0, padx=10, pady=10)
tk.Entry(root, textvariable=input_file_path, width=50).grid(row=0, column=1, padx=10, pady=10)
tk.Button(root, text="Escolher Vídeo", command=escolher_video).grid(row=0, column=2, padx=10, pady=10)

tk.Label(root, text="Tempo de Início (HH:MM:SS):").grid(row=1, column=0, padx=10, pady=10)
frame_start_time = tk.Frame(root)
frame_start_time.grid(row=1, column=1, padx=10, pady=10)
start_time_entry = tk.Entry(frame_start_time, textvariable=start_time, width=10)
start_time_entry.grid(row=0, column=0)
start_time_entry.bind("<KeyRelease>", atualizar_sliders)
tk.Button(frame_start_time, text="↑", command=lambda: ajustar_tempo(start_time_entry, 1)).grid(row=0, column=1)
tk.Button(frame_start_time, text="↓", command=lambda: ajustar_tempo(start_time_entry, -1)).grid(row=1, column=1)

tk.Label(root, text="Tempo de Término (HH:MM:SS):").grid(row=2, column=0, padx=10, pady=10)
frame_end_time = tk.Frame(root)
frame_end_time.grid(row=2, column=1, padx=10, pady=10)
end_time_entry = tk.Entry(frame_end_time, textvariable=end_time, width=10)
end_time_entry.grid(row=0, column=0)
end_time_entry.bind("<KeyRelease>", atualizar_sliders)
tk.Button(frame_end_time, text="↑", command=lambda: ajustar_tempo(end_time_entry, 1)).grid(row=0, column=1)
tk.Button(frame_end_time, text="↓", command=lambda: ajustar_tempo(end_time_entry, -1)).grid(row=1, column=1)

tk.Label(root, text="Selecione o intervalo de corte:").grid(row=3, column=0, columnspan=3, padx=10, pady=10)
start_slider = tk.Scale(root, from_=0, to=100, orient=tk.HORIZONTAL, command=atualizar_inputs)
start_slider.grid(row=4, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

end_slider = tk.Scale(root, from_=0, to=100, orient=tk.HORIZONTAL, command=atualizar_inputs)
end_slider.grid(row=5, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

cut_button = tk.Button(root, text="Cortar Vídeo", command=cortar_video)
cut_button.grid(row=6, column=0, columnspan=3, pady=20)

root.mainloop()
