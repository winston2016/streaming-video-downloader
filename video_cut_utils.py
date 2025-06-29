import os
import datetime
import subprocess

# Codec principal
VIDEO_CODEC = "libx264"

# Configuração de qualidade
CRF = "18"
PRESET = "veryslow"

def format_seconds(seconds: int) -> str:
    """Formata segundos em HH:MM:SS."""
    return str(datetime.timedelta(seconds=int(seconds)))

def parse_time(hms: str) -> float:
    """Converte HH:MM:SS para segundos."""
    parts = hms.strip().split(":")
    if len(parts) != 3:
        raise ValueError("Formato de tempo inválido")
    hours, minutes, seconds = parts
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)

def cut_video(input_path: str, output_path: str, start: float, end: float) -> None:
    """Corta trecho de vídeo sem reencodar (quando possível)."""
    cmd = [
        "ffmpeg",
        "-ss", str(start),
        "-to", str(end),
        "-i", input_path,
        "-c", "copy",
        output_path
    ]
    subprocess.run(cmd, check=True)

def crop_sides(input_path: str, output_path: str, left: int, right: int) -> None:
    """Corta as laterais horizontalmente, mantendo máxima qualidade."""
    # Pega dimensões originais
    probe_cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0:s=x",
        input_path
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    width, height = map(int, result.stdout.strip().split("x"))

    # Calcula nova largura e garante múltiplo de 2
    new_width = width - left - right
    if new_width % 2 != 0:
        new_width -= 1

    # Altura deve ser par também
    if height % 2 != 0:
        height -= 1

    x = left
    y = 0

    # Validação
    if new_width <= 0:
        raise ValueError("Nova largura ficou negativa ou zero.")
    if new_width + x > width:
        raise ValueError("Crop excede largura original.")

    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-filter:v", f"crop={new_width}:{height}:{x}:{y}",
        "-c:v", VIDEO_CODEC,
        "-crf", CRF,
        "-preset", PRESET,
        "-c:a", "copy",
        output_path
    ]
    subprocess.run(cmd, check=True)

def cut_vertical_halves(input_path: str, left_output: str, right_output: str) -> None:
    """Divide vídeo em metades verticais com máxima qualidade."""
    # Pega dimensões originais
    probe_cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0:s=x",
        input_path
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    width, height = map(int, result.stdout.strip().split("x"))

    # Calcula metade e garante múltiplo de 2
    half_width = width // 2
    if half_width % 2 != 0:
        half_width -= 1

    if height % 2 != 0:
        height -= 1

    # Metade esquerda
    left_cmd = [
        "ffmpeg",
        "-i", input_path,
        "-filter:v", f"crop={half_width}:{height}:0:0",
        "-c:v", VIDEO_CODEC,
        "-crf", CRF,
        "-preset", PRESET,
        "-c:a", "copy",
        left_output
    ]
    subprocess.run(left_cmd, check=True)

    # Metade direita
    right_cmd = [
        "ffmpeg",
        "-i", input_path,
        "-filter:v", f"crop={half_width}:{height}:{half_width}:0",
        "-c:v", VIDEO_CODEC,
        "-crf", CRF,
        "-preset", PRESET,
        "-c:a", "copy",
        right_output
    ]
    subprocess.run(right_cmd, check=True)
