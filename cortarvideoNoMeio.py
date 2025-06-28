import tkinter as tk
from tkinter import filedialog, messagebox
from video_cut_utils import cut_vertical_halves

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
        output_file_esquerda = filedialog.asksaveasfilename(
            defaultextension=".mp4", title="Salvar parte esquerda como"
        )
        if not output_file_esquerda:
            return
        output_file_direita = filedialog.asksaveasfilename(
            defaultextension=".mp4", title="Salvar parte direita como"
        )
        if not output_file_direita:
            return

        cut_vertical_halves(input_file, output_file_esquerda, output_file_direita)

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
