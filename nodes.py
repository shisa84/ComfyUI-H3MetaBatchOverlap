from __future__ import annotations

import torch
from comfy_api.latest import io

# ComfyUI-VideoHelperSuite's Meta Batch Manager (the BatchManager instance itself).
MetaBatch = io.Custom("VHS_BatchManager")


class H3MetaBatchOverlap(io.ComfyNode):
    """Prepend the previous meta batch's last frames to this batch, so a reference video lines up frame for frame
    with an H3 clip whose head is pinned by H3 Motion Context (context_length frames of the previous clip)."""

    # Last `overlap` frames of the previous batch, per node. Only one batch's tail is kept.
    _tails = {}

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="H3MetaBatchOverlap",
            display_name="H3 Meta Batch Overlap",
            category="video/minimax",
            description="Place after a VHS Load Video driven by a Meta Batch Manager. Outputs this batch's frames "
                        "preceded by the previous batch's last `overlap` frames (the first batch repeats its first "
                        "frame instead), and the 0-based batch index for H3 Motion Context Load/Save Latent. Set "
                        "overlap = Motion Context's context_length, H3 length = frames_per_batch + overlap (must be "
                        "17k+5), and trim `overlap` frames off every clip.",
            inputs=[
                MetaBatch.Input("meta_batch", tooltip="The same Meta Batch Manager as the Load Video."),
                io.Image.Input("images", tooltip="This batch's frames, from the meta-batched Load Video."),
                io.Int.Input("overlap", default=22, min=0, max=4096,
                             tooltip="Frames carried over from the previous batch. Same as Motion Context's context_length."),
            ],
            outputs=[
                io.Image.Output(id="images", display_name="images"),
                io.Int.Output(id="batch_index", display_name="batch_index",
                              tooltip="0 for the first batch. Load Latent clip_index = this, Save Latent clip_index = this + 1."),
            ],
            hidden=[io.Hidden.prompt, io.Hidden.unique_id],
        )

    @classmethod
    def execute(cls, meta_batch, images, overlap) -> io.NodeOutput:
        # VHS counts its requeues on the Batch Manager's own prompt inputs (videohelpersuite/utils.py).
        batch_index = cls.hidden.prompt[meta_batch.unique_id]["inputs"].get("requeue", 0)
        if batch_index == 0:
            head = images[:1].repeat(overlap, 1, 1, 1)
        elif cls.hidden.unique_id in cls._tails:
            head = cls._tails[cls.hidden.unique_id]
        else:
            raise ValueError("H3 Meta Batch Overlap: no frames kept from batch %d (ComfyUI restarted mid-run?). "
                             "Restart the meta batch from the beginning." % (batch_index - 1))
        cls._tails[cls.hidden.unique_id] = images[len(images) - overlap:].clone()
        return io.NodeOutput(torch.cat([head, images]), batch_index)


NODES = [H3MetaBatchOverlap]
