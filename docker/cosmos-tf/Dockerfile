# Transformers + bitsandbytes runtime for ubr-physical-ai/Cosmos3-Edge-NF4-bnb.
# Base is cu128 because RTX 50-series (sm_120) needs CUDA >= 12.8.
FROM pytorch/pytorch:2.9.0-cuda12.8-cudnn9-runtime

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# transformers >= 5.16 is the first release with the cosmos3_edge model type (NF4 model card).
RUN pip install --no-cache-dir "transformers>=5.16" accelerate bitsandbytes av pillow \
    "huggingface_hub>=0.34" fastapi uvicorn python-multipart kernels

# The base image's conda brotli is too old for urllib3 2.x streaming decode
# ("process() takes no keyword arguments" during hf download).
RUN pip install --no-cache-dir -U brotli urllib3

# Piper TTS runs on CPU (onnxruntime), leaving the GPU to the vision model.
RUN pip install --no-cache-dir piper-tts

WORKDIR /app

# Perception layer. supervision 0.32 dropped sv.ByteTrack, so scripts/perception.py
# carries its own IoU tracker; supervision stays for its drawing and box utilities.
# --no-deps skips its opencv-python pin, which needs libGL; headless cv2 serves instead.
RUN pip install --no-cache-dir opencv-python-headless scipy matplotlib defusedxml pyyaml tqdm pyDeprecate \
    && pip install --no-cache-dir --no-deps supervision
