# H3 Meta Batch Overlap

Loop a long source video through MiniMax H3 (e.g. the Character Swap LoRA) with a VHS **Meta Batch Manager**, chaining the clips with [H3 Motion Context](https://github.com/NikoDemon80/ComfyUI-H3-Motion-Context) for seamless joins.

Motion Context pins the previous clip's last `context_length` frames at the head of each new clip, so every generated clip is `context_length` frames longer than the batch, and those frames are trimmed off afterward. For the reference video to stay frame-aligned with the generated clip, it has to start with those same frames. **H3 Meta Batch Overlap** does that: it prepends the previous batch's last `overlap` frames to each batch, and gives the batch index used to load and save the Motion Context latents.

**Live demo:** https://youtu.be/Rt_X0STyIZc

## Installation

```
cd ComfyUI/custom_nodes
git clone https://github.com/shisa84/ComfyUI-H3MetaBatchOverlap
git clone https://github.com/NikoDemon80/ComfyUI-H3-Motion-Context
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite
```

Restart ComfyUI. No extra Python dependencies.

The example workflow also uses [ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes) (sampling preview) and [ComfyUI_essentials](https://github.com/cubiq/ComfyUI_essentials) (Display Any), both optional.

### Models (example workflow)

- MiniMax H3 models (ref2va diffusion model, video/audio VAEs, text encoder): [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3). The workflow's "Model Links" note lists each file and its folder.
- Character Swap LoRA: [akatz-ai/MiniMax-H3-Character-Swap-LoRA](https://huggingface.co/akatz-ai/MiniMax-H3-Character-Swap-LoRA) · [download `h3_character_swap_pro4500_1000.safetensors`](https://huggingface.co/akatz-ai/MiniMax-H3-Character-Swap-LoRA/resolve/main/h3_character_swap_pro4500_1000.safetensors), into `ComfyUI/models/loras/`, strength 1.0.

## Node

**H3 Meta Batch Overlap** (category `video/minimax`)

| Input | |
|---|---|
| meta_batch | The same Meta Batch Manager as the Load Video. |
| images | This batch's frames, from the meta-batched Load Video. |
| overlap | Frames carried over from the previous batch. Same value as Motion Context's `context_length`. |

| Output | |
|---|---|
| images | The previous batch's last `overlap` frames followed by this batch. On the first batch, its first frame is repeated instead. |
| batch_index | 0 for the first batch, then 1, 2, ... |

## Wiring

See `example_workflows/H3_Character_Swap_Meta_Batch_Overlap.json`.

- **Meta Batch Manager** → Load Video `meta_batch` and Overlap `meta_batch` (and Video Combine `meta_batch`).
- **Load Video** `IMAGE` → Overlap `images`. Set `force_rate` to 24 and `format` to `None` (the Wan preset rejects batch sizes that aren't 4k+1).
- **Overlap** `images` → MiniMaxH3ReferenceToVideo `ref_video`, and → Get Image Size, whose `batch_size` goes into the H3 `length`.
- **Motion Context** between MiniMaxH3ReferenceToVideo and the guider, `context_length` = `overlap`.
- **Motion Context Load Latent** `clip_index` = `batch_index` (0 loads nothing, so the first clip runs without context).
- **Motion Context Save Latent** after the sampler, `clip_index` = `batch_index + 1` (e.g. a Math Expression `a + 1`). Use the same folder on both: Load `latent_path` `h3_swap_context`, Save `filename_prefix` `h3_swap_context/clip`.
- **Motion Context Trim** after the decode, `trim_frames` typed in as `overlap`. Don't wire it from Motion Context's `trim_frames`: that one is 0 on the first batch, which would leave the first clip `overlap` frames too long.

## Settings

H3 only generates 17k+5 frames and `overlap` is one of 5, 22, 39, 56, so the batch must be a multiple of 17.

| overlap | Meta Batch | H3 length (= batch + overlap) | frame_load_cap (= batch × n) |
|---|---|---|---|
| 5 | 119 | 124 | 119 × n (4.96 s × n) |
| 5 | 136 | 141 | 136 × n (5.67 s × n) |
| 5 | 170 | 175 | 170 × n (7.08 s × n) |
| 5 | 238 | 243 | 238 × n (9.92 s × n) |
| 22 | 85 | 107 | 85 × n (3.54 s × n) |
| 22 | 102 | 124 | 102 × n (4.25 s × n) |
| 22 | 119 | 141 | 119 × n (4.96 s × n) |
| 22 | 136 | 158 | 136 × n (5.67 s × n) |
| 22 | 153 | 175 | 153 × n (6.38 s × n) |
| 22 | 170 | 192 | 170 × n (7.08 s × n) |
| 22 | 187 | 209 | 187 × n (7.79 s × n) |
| 22 | 204 | 226 | 204 × n (8.50 s × n) |
| 22 | 221 | 243 | 221 × n (9.21 s × n) |
| 22 | 238 | 260 | 238 × n (9.92 s × n) |
| 22 | 289 | 311 | 289 × n (12.04 s × n) |
| 22 | 340 | 362 | 340 × n (14.17 s × n) |
| 39 | 119 | 158 | 119 × n (4.96 s × n) |
| 39 | 170 | 209 | 170 × n (7.08 s × n) |
| 39 | 238 | 277 | 238 × n (9.92 s × n) |
| 56 | 119 | 175 | 119 × n (4.96 s × n) |
| 56 | 170 | 226 | 170 × n (7.08 s × n) |
| 56 | 238 | 294 | 238 × n (9.92 s × n) |

- overlap = context_length = trim_frames.
- n = number of loops: the largest whole number with batch × n ≤ (video seconds × 24 − skip_first_frames). `skip_first_frames` and `frame_load_cap` both count frames after `force_rate` 24.
- With `frame_load_cap` = 0 the last batch only gets the leftover frames: H3 rounds its length up to the next 17k+5, so the output ends up to 16 frames longer than the source, and that last clip has a very short reference video.
- H3's trained range is about 124-362 frames.

## Notes

- Always run the meta batch from the start. The previous batch's frames are kept in memory only, so after a ComfyUI restart mid-run the next batch stops with an error.
- The previous batch's tail is kept at the Load Video's resolution. With a 4K source, set Load Video `custom_width` (e.g. 1344) to save RAM; H3 resizes the reference video to the generation size anyway.
