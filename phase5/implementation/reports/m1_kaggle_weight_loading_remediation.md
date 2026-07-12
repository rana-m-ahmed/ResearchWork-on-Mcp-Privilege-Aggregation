# M1 Kaggle Weight-Loading Remediation

## Finding

The frozen M1 checkpoint contains 15,231,233,024 bytes of safetensor weights. The
Phase 4 authority records float16 execution on an RTX 4090 with 64 GB system RAM.
Common Kaggle T4/P100 sessions expose 16 GB VRAM, leaving insufficient headroom
when the previous unconstrained `device_map="auto"` placement filled the GPU before
generation allocations. The resulting CPU or disk spill depended on transient free
memory and presented as weight materialization stalling at varying percentages.

Hugging Face authentication was not causal. The observed stall occurred after the
pinned snapshot download, while Transformers was materializing parameters.

## Remediation

- Preserve the frozen M1 identity, revision, float16 dtype, and automatic device map.
- Derive placement limits from current free GPU and CPU memory.
- Enumerate both Kaggle T4 devices and reserve 2 GiB VRAM on each for CUDA and generation allocations.
- Reserve 4 GiB system RAM and permit controlled CPU/offload placement.
- Enable low-CPU-memory safetensor loading and four-worker parallel shard loading.
- Fail closed unless the notebook sees exactly two NVIDIA T4 GPUs and the loaded device map uses both.
- Fail closed before loading when usable GPU or CPU memory is below 4 GiB.
- Expose the existing campaign `max_batches` bound through the CLI.
- Bound the M1 proof notebook to one batch instead of the full safety horizon.
- Package final evidence only after credential purge and frozen-source reverification.

## Verification

- Notebook JSON and all code cells compile.
- Focused loader, campaign, CLI, and Kaggle handoff tests: 39 passed.
- Full Phase 5 suite: 240 passed.
- No files under `phase4/` or `phase4_5/` were modified.
