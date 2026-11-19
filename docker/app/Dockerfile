# Maya app runtime: the cosmos-tf image plus speech input.
# faster-whisper runs on CPU (CTranslate2 int8), so the GPU stays with the vision models.
FROM maya-cosmos-tf

RUN pip install --no-cache-dir faster-whisper pyyaml pytest

WORKDIR /app
