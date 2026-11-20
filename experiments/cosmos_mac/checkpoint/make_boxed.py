import subprocess, sys, os
import annotate as A
for t0, t1, n in [(2.0, 4.0, "w1"), (8.0, 10.0, "w2"), (15.0, 17.0, "w3")]:
    fr = A.frames(t0, t1)
    d = f"boxed_{n}"; os.makedirs(d, exist_ok=True)
    for i, (_, im) in enumerate(fr):
        im.save(f"{d}/{i:03d}.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "4", "-i", f"{d}/%03d.png",
                    "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", f"walk_{n}_boxed.mp4"], check=True)
    print(n, len(fr), "frames")
