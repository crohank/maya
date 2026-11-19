# Hardware

Measured 2026-11-18 with `nvidia-smi` and Windows system info.

| Item | Value |
|---|---|
| GPU | NVIDIA GeForce RTX 5060 Laptop GPU (Blackwell, compute capability 12.0) |
| VRAM | 8151 MiB total, about 2.9 GB used by the desktop at idle |
| Driver | 592.82 |
| CUDA (driver) | 13.1 |
| CPU | AMD Ryzen 9 8940HX |
| RAM | 31 GB (WSL2 sees 15 GB) |
| OS | Windows 11 Home 10.0.26200, models run in Docker on WSL2 (kernel 6.18.33.2) |

Note: the build brief assumed 16 GB+ VRAM on Linux. This dev machine has 8 GB, so
Cosmos3-Edge runs as the NF4 4-bit build, not BF16.
