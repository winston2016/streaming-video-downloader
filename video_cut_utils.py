import os
import datetime
from moviepy.editor import VideoFileClip
from moviepy.video.fx.all import crop

VIDEO_CODEC = "h264_nvenc" if os.getenv("VIDEO_HWACCEL") else "libx264"

def format_seconds(seconds: int) -> str:
    """Return time formatted as HH:MM:SS."""
    return str(datetime.timedelta(seconds=int(seconds)))

def parse_time(hms: str) -> float:
    """Return seconds from an ``HH:MM:SS`` string.

    Supports fractional seconds in the ``SS`` component.
    """
    parts = hms.strip().split(":")
    if len(parts) != 3:
        raise ValueError("Tempo inválido")
    hours, minutes, seconds = parts
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)

def cut_video(input_path: str, output_path: str, start: float, end: float) -> None:
    """Cut ``input_path`` between ``start`` and ``end`` seconds and save to ``output_path``."""
    output_path = os.path.abspath(output_path)
    temp_audio = os.path.splitext(output_path)[0] + "_temp_audio.m4a"
    with VideoFileClip(input_path) as src:
        sub = src.subclip(start, end)
        sub.write_videofile(
            output_path,
            codec=VIDEO_CODEC,
            audio_codec="aac",
            temp_audiofile=temp_audio,
            remove_temp=True,
        )
        sub.close()

def cut_vertical_halves(input_path: str, left_output: str, right_output: str) -> None:
    """Split the video vertically into left and right halves."""
    clip = VideoFileClip(input_path)
    width, height = clip.size
    half = width // 2
    left_clip = clip.crop(x1=0, y1=0, x2=half, y2=height)
    right_clip = clip.crop(x1=half, y1=0, x2=width, y2=height)
    left_clip.write_videofile(left_output, codec=VIDEO_CODEC, audio_codec="aac")
    right_clip.write_videofile(right_output, codec=VIDEO_CODEC, audio_codec="aac")
    left_clip.close()
    right_clip.close()
    clip.close()

def crop_sides(input_path: str, output_path: str, left: int, right: int) -> None:
    """Crop the video horizontally between ``left`` and ``right`` coordinates."""
    clip = VideoFileClip(input_path)
    cropped = crop(clip, x1=left, x2=right)
    cropped.write_videofile(output_path, codec=VIDEO_CODEC, audio_codec="aac")
    cropped.close()
    clip.close()
