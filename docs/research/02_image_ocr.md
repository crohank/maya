# 02: Image reading (OCR) model and the Qwen3-VL slowness

Researched 2026-11-18. Hardware target: RTX 5060 Laptop (sm_120, 8 GB, about 5 GB free), PyTorch 2.9.0+cu128, transformers 5.23, bitsandbytes 0.50.
Anything not confirmed from a primary source is marked UNVERIFIED. Nothing was run or installed for this report.

## 1. Recommendation

**Model:** keep `Qwen/Qwen3-VL-4B-Instruct` (Apache-2.0). It has the highest OCR scores of anything that fits under 4 GB (OCRBench 881, DocVQA 95.3, Qwen3-VL report Table 4), and it already beat Cosmos3-Edge on your set (6/10 vs 5/10, key recall 0.81 vs 0.71). Its only problem is speed, and that problem has a known cause with a 5 line fix.

**Runtime, tonight (lowest risk):** stay on transformers and replace the patch embedding Conv3d with an equivalent `F.linear` (code below). No install, no new weights, mathematically identical. This removes the 14 to 17 s patch embed. Expected result after the fix: vision tower well under 1 s for a 640x360 frame, total latency dominated by NF4 decode at your measured 15 tok/s, so about 2 to 4 s for a 20 to 40 token answer (UNVERIFIED estimate, measure it).

**Runtime, if decode speed matters more (second step):** llama.cpp `llama-server` with the official Qwen GGUF:
`Qwen/Qwen3-VL-4B-Instruct-GGUF`, files `Qwen3VL-4B-Instruct-Q4_K_M.gguf` (2.33 GB) + `mmproj-Qwen3VL-4B-Instruct-F16.gguf` (0.78 GB). About 3.1 GB of weights plus KV cache, fits in 5 GB. llama.cpp CUDA builds with CUDA 12.8+ compile `120a-real` (sm_120) by default, and its official CUDA Docker image uses CUDA 12.8.1. llama.cpp does not use PyTorch, so the Conv3d bug cannot occur there. Decode speed on a 5060 Laptop: UNVERIFIED (no published measurement found; expect several times faster than bitsandbytes NF4, which is known to decode slowly).

**Not recommended for this deadline:** vLLM. Its current Dockerfile builds for arch `12.0` on CUDA 13.2.1, and vLLM already patched the Conv3d in its own Qwen3-VL code (PR #27418), but with about 5 GB free the FP8 4B checkpoint plus vLLM's KV preallocation is tight, community reports on sm_120 needed workarounds (Triton attention backend, `awq_marlin`), and FP8 kernel coverage on consumer sm_120 is UNVERIFIED.

**Settings (transformers):**
- Patch embed fix applied before the first call (section 3).
- Cap image size: the shipped `preprocessor_config.json` allows `longest_edge` 16,777,216 pixels (16.7 MP). A full phone photo would become about 12,000 visual tokens. Pass `size={"longest_edge": 1_310_720, "shortest_edge": 65_536}` (about 1,280 visual tokens max; one token covers 32x32 px after the 2x2 merge).
- Greedy decoding for reading tasks (`do_sample=False`), `max_new_tokens` 96, `repetition_penalty` about 1.05 to stop the line-looping seen on busy signs.
- `attn_implementation="sdpa"` is fine; flash-attn 2 is optional and not the cause of the slowness.
- Keep the vision tower in BF16 (as you do). The fix depends on `proj.weight` being a plain tensor, which it is when the vision tower is skipped by bitsandbytes.

**Expected accuracy:** about 6/10 on your current set, likely 7/10 or more with zoom crops for the small-text items (UNVERIFIED). Two of the four Qwen "fails" look like grader strictness, not misreads: `syn_slide.png` ("Revenue increased by 12%" vs key "up 12%") and `syn_medicine.png` (content correct, phrasing differs). Worth loosening those keys before reporting. The two real misses are `real_kiosk_sign.png` (read "LOCO" for "Kiosk") and `real_lunch_sign.png` (read "FAPCORP"), both small text in real street frames, which is what crops fix.

## 2. Comparison: OCR-capable models under about 4 GB

Scores are as reported by the model authors. TextVQA is not reported in the Qwen3-VL report. OCRBench is out of 1000.

| Model (exact HF ID) | Params | License | OCRBench | TextVQA (val) | DocVQA (test) | Source / note |
|---|---|---|---|---|---|---|
| `Qwen/Qwen3-VL-4B-Instruct` | 4B | Apache-2.0 | 881 | not reported | 95.3 | Qwen3-VL report Table 4 (InfoVQA 80.3, ChartQA 84.6, CC-OCR 76.2) |
| `Qwen/Qwen3-VL-2B-Instruct` | 2B | Apache-2.0 | 858 | not reported | 93.3 | Table 4 (InfoVQA 72.4, ChartQA 79.1) |
| `Qwen/Qwen3-VL-8B-Instruct` (reference, over 4 GB in NF4 with vision) | 8B | Apache-2.0 | 896 | not reported | 96.1 | Table 4 |
| `openbmb/MiniCPM-V-4` | 4.1B | Apache-2.0 | 894 (card) / 862 (InternVL3.5 paper) | 80.8 (card) / 81.4 | 92.9 (card) / 94.0 | Numbers disagree between sources; GGUF at `openbmb/MiniCPM-V-4-gguf` |
| `OpenGVLab/InternVL3_5-4B` | 4.7B | Apache-2.0 | 822 | 77.9 | 92.4 | InternVL3.5 paper OCR table (InfoVQA 78.0) |
| `OpenGVLab/InternVL3_5-2B` | 2.3B | Apache-2.0 | 836 | 76.5 | 89.4 | same table (InfoVQA 70.8) |
| `Qwen/Qwen2.5-VL-3B-Instruct` | 3.8B | Qwen Research (non-commercial) | 797 | 79.3 | 93.9 | InternVL3.5 paper table |
| `vikhyatk/moondream2` (rev 2025-04-15 numbers) | 1.9B | Apache-2.0 | 612 | 76.3 | 79.3 | model card |
| `HuggingFaceTB/SmolVLM2-2.2B-Instruct` | 2.2B | Apache-2.0 | 729 | 73.2 | 80.0 (val) | model card |
| `google/gemma-3n-E4B-it` / `-E2B-it` | 8B raw / 4B effective | Gemma terms (gated) | not on card | not on card | not on card | images fixed at 256 tokens (max 768x768), weak for small text |
| `PaddlePaddle/PaddleOCR-VL` | 0.9B | Apache-2.0 | not reported | not reported | not reported | document parsing only (OmniDocBench), no scene-text VQA |
| `PaddlePaddle/PP-OCRv5_server_rec` (+ PP-OCRv5 det) | small | Apache-2.0 | n/a | n/a | n/a | pure OCR; line accuracy 0.84 avg but 0.59 on "General Scenario" (scene text) |
| `microsoft/Florence-2-large` | 0.77B | MIT | n/a | n/a | n/a | OCR task token only, no free-form Q&A; scores not checked |
| `stepfun-ai/GOT-OCR-2.0-hf` | 0.58B | Apache-2.0 | n/a | n/a | n/a | dense document OCR; scene-text numbers not checked |
| `nvidia/Cosmos3-Edge` (your baseline) | n/a | NVIDIA "other" | n/a | n/a | n/a | your test: 5/10, 1.2 s median |

Notes on reliability:
- Qwen3-VL Table 4 was read from the PDF text layer (arXiv 2511.21631v2), where labels and numbers are misaligned. Column order (2B thinking/instruct, 4B thinking/instruct, 8B thinking/instruct, GPT-5 nano high/minimal) and row identity were confirmed by matching the Thinking columns against an independent copy of the same release numbers (OCRBench 808/819, DocVQA 94.2/95.3, InfoVQA 83.0/86.0 for 4B/8B Thinking). A third-party paper (Qianfan-OCR, arXiv 2603.13398) reports 873 OCRBench for Qwen3-VL-4B under its own protocol.
- The InternVL3.5 OCR table PDF text has the OCRBench column shifted down one row. I corrected it by checking known values (InternVL3-2B 835, Qwen2.5-VL-3B 797, Qwen2.5-VL-7B 864, InternVL3-8B 880 all line up after the shift). Treat the InternVL3.5 and MiniCPM-V-4 OCRBench values as UNVERIFIED until read off the rendered table.
- Moondream2 OCRBench "61.2" on the card is a percent; shown as 612 for consistency. The newest revision (2025-06-21) has no published OCR numbers.

**Dedicated OCR + small LLM vs one VLM, for street signs:** one VLM wins for this task. PP-OCRv5 reads about 59% of scene-text lines fully correctly (its "General Scenario" score), it cannot answer "which bus" or "what does the sign on the right say", and a second model adds load time and VRAM. The useful part of a detector is finding where text is so the VLM gets a zoomed crop (section 4). No published head-to-head on street signs was found (UNVERIFIED either way).

## 3. The Conv3d slowness: findings

**What you measured:** `Qwen3VLVisionPatchEmbed.proj` is `nn.Conv3d(3, 1024, kernel=(2,16,16), stride=(2,16,16))`. Your 640x360 frame becomes 880 patches (40x22 grid), `pixel_values` (880, 1536) bf16, and this one op takes 14 to 17 s. The same op is a matrix multiply of (880 x 1536) by (1536 x 1024) and should take well under 1 ms.

**Root cause (well documented):**
1. cuDNN 9.10 to 9.14 had broken 3D convolution paths, so PyTorch 2.9.0 disabled cuDNN for 3D convs and fell back to the native `vol2col` path, which is extremely slow (and memory hungry) for bf16/fp16 with this shape. Maintainer eqy in pytorch#166643 attributes the 2.9.0 regression to this fallback.
2. pytorch PR #166480 "[cuDNN][conv] Re-enable cuDNN for 3D convolutions (fixed in 9.15+)" (merged 2025-10-30, milestone 2.9.1) turns cuDNN back on only when the runtime cuDNN is 9.15 or newer.
3. That explains your observation that `torch.backends.cudnn.enabled` on or off makes no difference: on 2.9.0 cuDNN is never used for this conv, so both settings hit `vol2col`.
4. It is not Blackwell specific. Reports exist on H100, H200, RTX 4090, RTX 6000 Blackwell and RTX 5090. fp32 is fast (about 2 to 70 ms) because the bf16/fp16 path is the one that regressed.

**Evidence:**
- pytorch/pytorch#168167 "Severe Performance Regression in Conv3D / bf16 in PyTorch 2.9.1": H200, cuDNN 9.10.2, input (6900, 3, 2, 16, 16) bf16, about 40 s vs about 1 ms on 2.8. Maintainers: known issue, fix is nightly/2.10, or 2.9.1 with cuDNN 9.15+ installed manually. Closed 2025-11-26.
- pytorch/pytorch#166643 "Significant Memory Regression in F.conv3d with bfloat16 Inputs in PyTorch 2.9.0": fixed by cuDNN 9.15+; torch 2.10.0 RC (cu128 and cu130) shows fixed behavior. Closed 2026-01-12, milestone 2.10.0. PR #169412 proposed bumping the bundled cuDNN to 9.15.1 for 2.10 (UNVERIFIED that the final 2.10 wheel ships it).
- pytorch/pytorch#166790 (Conv3d OOM on RTX 4090, 2.9.0+cu128): reporter confirmed PyTorch 2.10 fixed it (2026-01-30).
- discuss.pytorch.org "Conv3D runs very slow in fp16 and bf16" (topic 223940): exact Qwen3-VL patch embed shape on RTX 6000 Blackwell, torch 2.9.0+cu128, cuDNN 9.10.2. Conv3d bf16 42.1 s, fp16 42.6 s, fp32 0.067 s, equivalent Linear bf16 0.00088 s. Version matrix from the thread: 2.9.0 + cuDNN 9.10 slow, **2.9.0 + cuDNN 9.15 still slow**, 2.8.0 + cuDNN 9.10 fine, 2.9.1 + cuDNN 9.15 fine.
- NVIDIA forum "cuDNN Bug Report: Conv3d Performance Regression with bfloat16/float16 on H100" (topic 355210): names Qwen3-VL `Qwen3VLVisionPatchEmbed` and Qwen2-VL; bf16 about 35 s per forward; workaround is fp32 conv with autocast off. NVIDIA escalated, no fixed version stated.
- vllm-project/vllm#27406 "MM performance regression from upgrading to torch 2.9" (closed 2025-10-27) and vllm PR #27418 "[MM][Bugfix] Replace PatchEmbed's conv3d to linear layer" (merged 2025-10-24): Qwen2-VL, Qwen2.5-VL, Qwen3-VL, Qwen3-Omni, GLM-4.1V.
- sgl-project/sglang PR #20282 "Add Conv2dLayer/Conv3dLayer to fix PyTorch 2.9.1 CuDNN Conv3d bug" (merged 2026-03-15): unfold + linear when kernel == stride for qwen3_vl, qwen2_vl, glm4v; OCRBench unchanged (0.896 before, 0.903 after).
- transformers: `main` still uses `nn.Conv3d` in `Qwen3VLVisionPatchEmbed` (checked `src/transformers/models/qwen3_vl/modeling_qwen3_vl.py` on 2026-11-18). No transformers version carries the Linear fix, so upgrading transformers will not help.

**Fix options, best first:**

1. **Replace the Conv3d with a Linear at load time (no install).** Kernel equals stride, so the conv is exactly a matmul over flattened patches. Equivalent to what vLLM and SGLang ship.

```python
import torch.nn.functional as F
from transformers.models.qwen3_vl import modeling_qwen3_vl as qwen3_vl

def _patch_embed_as_linear(self, hidden_states):
    # Conv3d with kernel == stride is a matmul over flattened (C, T, P, P) patches.
    # torch 2.9.0 runs bf16 Conv3d through vol2col: 14 to 17 s for 880 patches on the 5060.
    # See pytorch/pytorch#168167 and #166643.
    w = self.proj.weight
    x = hidden_states.reshape(-1, w[0].numel()).to(w.dtype)
    return F.linear(x, w.reshape(w.shape[0], -1), self.proj.bias)

qwen3_vl.Qwen3VLVisionPatchEmbed.forward = _patch_embed_as_linear
```

   Check once with `torch.allclose(old_out.float(), new_out.float(), atol=1e-2)` on one image (the conv in fp32 vs the linear in bf16), then drop the check.

2. **Upgrade torch** to 2.9.1 plus `nvidia-cudnn-cu12>=9.15`, or to 2.10.x. Fixes every Conv3d in the process, but costs a container rebuild the day before the deadline. torch 2.9.0 plus new cuDNN alone does not work (forum version matrix above).

3. **Run only the conv in fp32:** `self.proj.float()` and cast input/output. Tens of ms, no install, but option 1 is faster and just as simple.

Not fixes: toggling `torch.backends.cudnn.enabled` or `benchmark` (no effect on 2.9.0, as you saw), switching sdpa to flash-attn (the attention is not the slow part), `channels_last` (suggested in #168167 but irrelevant for a 1x1x1 output).

## 4. Small text in phone photos

- **Know the token budget.** Qwen3-VL: one visual token per 32x32 px (patch 16, merge 2). 640x360 is only 220 tokens, which is why the tiny kiosk and lunch signs fail. A full 1080p frame is about 2,000 tokens; prefer sending more pixels over a downscaled frame for reading tasks.
- **Set a ceiling, not a low cap.** Default `longest_edge` is 16.7 MP. Use about 1.0 to 1.6 MP for a full frame (1,000 to 1,600 tokens). Raise `shortest_edge` (min pixels) so a small crop is upscaled rather than processed at a few dozen tokens.
- **Zoom crops on demand.** Two-pass: ask the full frame first; if the answer contains "can't read", or the question is "what does it say", send 2x2 overlapping tiles (about 15% overlap) or a center crop of the region the model named, at the same per-image token budget. This gives roughly 4x the pixels per character.
- **Detect then crop.** A text detector (PP-OCRv5 mobile det, Apache-2.0) gives boxes in tens of ms; pad each box by 20 to 30%, merge nearby boxes, upscale so letters are at least about 20 to 30 px tall (heuristic, UNVERIFIED threshold), and send the top 1 to 3 crops with the full frame. Use the detector only for locating text; let the VLM read it.
- **Prompt for reading first.** "Transcribe all visible text exactly, then answer: ..." reduces paraphrase (which is also why two of your Qwen answers failed string matching).
- **Stop loops.** Greedy decode with `repetition_penalty` about 1.05 and a hard `max_new_tokens`; dedupe repeated lines in post-processing (Cosmos3-Edge's "EXIT ONLY PARKING" loop).
- **llama.cpp equivalent:** `--image-min-tokens` and `--image-max-tokens` on `llama-server` control the same budget for dynamic-resolution models such as Qwen3-VL.

## 5. Runtimes and quantized checkpoints

| Item | Status | Detail |
|---|---|---|
| `Qwen/Qwen3-VL-4B-Instruct-FP8` | exists, official, Apache-2.0 | fine-grained FP8, block size 128 |
| `Qwen/Qwen3-VL-2B-Instruct-FP8`, `Qwen/Qwen3-VL-8B-Instruct-FP8` | exist, official, Apache-2.0 | |
| Official Qwen3-VL AWQ | not found | `Qwen/Qwen3-VL-4B-Instruct-AWQ` does not exist. Community: `cpatonn/Qwen3-VL-4B-Instruct-AWQ-4bit`, `cpatonn/Qwen3-VL-8B-Instruct-AWQ-4bit` (Apache-2.0 tag) |
| `Qwen/Qwen3-VL-4B-Instruct-GGUF` | official, Apache-2.0 | `Qwen3VL-4B-Instruct-Q4_K_M.gguf` 2.33 GB, `Q8_0` 3.99 GB, `F16` 7.5 GB; `mmproj-Qwen3VL-4B-Instruct-F16.gguf` 0.78 GB, `mmproj-...-Q8_0.gguf` 0.42 GB |
| `Qwen/Qwen3-VL-2B-Instruct-GGUF` | official, Apache-2.0 | Q4_K_M 1.03 GB, Q8_0 1.71 GB, mmproj F16 0.76 GB |
| `Qwen/Qwen3-VL-8B-Instruct-GGUF` | official, Apache-2.0 | Q4_K_M, Q8_0, F16 + mmproj |
| `unsloth/Qwen3-VL-4B-Instruct-GGUF` | community, Apache-2.0 | many quants incl. UD-Q4_K_XL; `mmproj-F16.gguf`, `mmproj-BF16.gguf` |
| llama.cpp Qwen3-VL | supported | PR #16780 "[model] add support for qwen3vl series", merged 2025-10-30 |
| llama.cpp on sm_120 | supported | CUDA 12.8+ builds add `120a-real`; `.devops/cuda.Dockerfile` uses CUDA 12.8.1 |
| vLLM Qwen3-VL | supported | Conv3d already replaced by Linear (PR #27418) |
| vLLM on sm_120 | supported in current Dockerfile | arch list includes `12.0`, base CUDA 13.2.1 (needs a recent driver, UNVERIFIED for your WSL2 driver); latest release v0.34.0 (2026-11-16). Earlier field reports needed `--attention-backend TRITON_ATTN` and `awq_marlin` on RTX 50 cards (UNVERIFIED for current release) |
| SGLang | Conv3d fixed (PR #20282) | sm_120 support not checked |
| LMDeploy | not checked | |

## 6. Sources

- PyTorch issue #168167, Conv3D bf16 regression in 2.9.1: https://github.com/pytorch/pytorch/issues/168167
- PyTorch issue #166643, conv3d bf16 memory regression in 2.9.0: https://github.com/pytorch/pytorch/issues/166643
- PyTorch issue #166790, conv3d OOM on 2.9.0, fixed in 2.10: https://github.com/pytorch/pytorch/issues/166790
- PyTorch PR #166480, re-enable cuDNN for 3D conv on cuDNN 9.15+: https://github.com/pytorch/pytorch/pull/166480
- PyTorch forum, Conv3D slow in fp16 and bf16 (Qwen3-VL shape, RTX 6000 Blackwell): https://discuss.pytorch.org/t/conv3d-runs-very-slow-in-fp16-and-bf16/223940
- NVIDIA forum, cuDNN Conv3d bf16 regression report: https://forums.developer.nvidia.com/t/cudnn-bug-report-conv3d-performance-regression-with-bfloat16-float16-on-h100/355210
- vLLM issue #27406: https://github.com/vllm-project/vllm/issues/27406
- vLLM PR #27418, PatchEmbed conv3d to linear: https://github.com/vllm-project/vllm/pull/27418
- SGLang PR #20282, Conv3dLayer: https://github.com/sgl-project/sglang/pull/20282
- transformers Qwen3-VL modeling (main): https://github.com/huggingface/transformers/blob/main/src/transformers/models/qwen3_vl/modeling_qwen3_vl.py
- vLLM Dockerfile: https://github.com/vllm-project/vllm/blob/main/docker/Dockerfile
- llama.cpp PR #16780, Qwen3-VL support: https://github.com/ggml-org/llama.cpp/pull/16780
- llama.cpp CUDA CMake (sm_120): https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-cuda/CMakeLists.txt
- llama.cpp server README (image token flags): https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- Qwen3-VL Technical Report, Table 4: https://arxiv.org/abs/2511.21631
- InternVL3.5 paper, OCR table: https://arxiv.org/abs/2508.18265
- Qianfan-OCR paper (third-party Qwen3-VL-4B numbers): https://arxiv.org/abs/2603.13398
- Qwen3-VL-4B-Instruct card and configs: https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct
- Qwen3-VL-4B-Instruct-FP8: https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-FP8
- Qwen3-VL-4B-Instruct-GGUF: https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF
- unsloth Qwen3-VL-4B GGUF: https://huggingface.co/unsloth/Qwen3-VL-4B-Instruct-GGUF
- MiniCPM-V 4: https://huggingface.co/openbmb/MiniCPM-V-4
- InternVL3.5-4B: https://huggingface.co/OpenGVLab/InternVL3_5-4B
- SmolVLM2-2.2B: https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct
- moondream2: https://huggingface.co/vikhyatk/moondream2
- Gemma 3n E4B: https://huggingface.co/google/gemma-3n-E4B-it
- PaddleOCR-VL: https://huggingface.co/PaddlePaddle/PaddleOCR-VL
- PP-OCRv5 server rec: https://huggingface.co/PaddlePaddle/PP-OCRv5_server_rec
- Licenses for all HF IDs above were read from the Hugging Face model API tags on 2026-11-18.
