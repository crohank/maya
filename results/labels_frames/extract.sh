#!/bin/bash
# Contact sheets for hand labelling: one frame every 0.5 s, timestamp burned in.
# Run inside maya-cosmos-tf from /app: bash results/labels_frames/extract.sh
F=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
for spec in "fifth-avenue-point-of-view-manhattan-nyc-looking-around-day:400:-2:4x3" \
            "3874684_720p:400:-2:4x3" "london_walking:400:-2:4x3" \
            "197531-905015052_medium:-2:400:6x2"; do
  IFS=: read stem w h t <<< "$spec"
  mkdir -p results/labels_frames/$stem
  rm -f results/labels_frames/$stem/sheet_*.jpg
  ffmpeg -hide_banner -loglevel error -y -i test_videos/$stem.mp4 \
    -vf "fps=2,scale=$w:$h,drawtext=fontfile=$F:text='%{eif\:n/2\:d}.%{eif\:mod(n,2)*5\:d}s':x=5:y=5:fontsize=26:fontcolor=yellow:box=1:boxcolor=black@0.7,tile=$t:padding=2" \
    -q:v 3 results/labels_frames/$stem/sheet_%02d.jpg
  echo "$stem $(ls results/labels_frames/$stem | wc -l) sheets"
done
