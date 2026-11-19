"""ffmpeg helpers for uploaded clips and photos."""
import subprocess

from PIL import Image, ImageOps


def _run(cmd, timeout):
    subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)


def duration(path, timeout):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True, timeout=timeout,
    )
    return float(out.stdout.strip())


def last_window(src, dst, work_dir, window_s, fps, long_side, timeout):
    """Cut the last `window_s` seconds at `fps`, long side bounded to `long_side`.

    MediaRecorder WebM has no duration in its header and cannot be seeked, so the
    clip is first decoded once at the target fps and size into an MP4, which can.
    """
    vf = (f"fps={fps},scale={long_side}:{long_side}:force_original_aspect_ratio=decrease:"
          "force_divisible_by=2")
    norm = f"{work_dir}/norm.mp4"
    enc = ["-an", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vf", vf, *enc, norm], timeout)
    start = max(0.0, duration(norm, timeout) - window_s)
    _run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.2f}", "-i", norm,
          "-t", f"{window_s:.2f}", *enc, dst], timeout)


def last_frame(src, dst, timeout):
    # -update 1 rewrites one file per decoded frame, so the last frame wins even
    # when the container has no duration to seek from.
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-an", "-update", "1", dst], timeout)


def load_image(path, long_side):
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    img.thumbnail((long_side, long_side))
    return img
