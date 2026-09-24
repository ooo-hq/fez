# Local development

Run commands from the repository root. Install the model environment using the
[README](../README.md#setup). No GPU is needed for the regression suite.

```bash
.venv-kev/bin/python -m unittest discover -v
```

The process tests run real HTTP, signatures, checkpoint transfer, calibration,
and restart handling. Expensive training and inference use fixture workers;
passing these tests is not evidence of model quality or GPU performance.
Chain RPC is faked; tests never submit transactions.

## Score a checkpoint

```bash
python3 -m fez submit --checkpoint models/reference --uid 1 > submissions-reference.json
python3 -m fez evaluate \
  --submissions submissions-reference.json --cases examples/cases.jsonl \
  --base-revision dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68 \
  --runner-python .venv-kev/bin/python --device cpu --report round-local.json
```

Use fresh output/report paths. For multiple candidates, put their submission
objects in one JSON list; every UID and checkpoint hash must be distinct.
The example questions are public diagnostics, not an emissions benchmark.
Use `mps` on Apple Silicon or `cuda` on a configured NVIDIA machine.

## Rehearse two existing checkpoints

After producing the probe below:

```bash
PYTORCH_ENABLE_MPS_FALLBACK=1 .venv-kev/bin/python -m scripts.rehearsal run \
  --checkpoints models/reference models/fez-local-probe-002 \
  --device mps --out runs/rehearsal-new
```

This starts two miners and one validator as separate processes, then stops all
three when evaluation finishes or fails. It generates disposable local signing
keys and saves the report under `validator/report.json` in the run directory.
The [persistent fleet](mining.md) additionally trains a candidate each round.

## Training on this Mac

Local training was verified on an Apple M4 Pro with 24 GiB of unified memory.
PyTorch MPS is available outside the Codex filesystem sandbox; its sandboxed
availability check returned false. The four short training examples in
`examples/train-smoke.jsonl` completed four optimizer steps in 7.84 seconds
(training loop only, excluding model loading and saving), with peak process RSS
3.76 GiB and sampled GPU allocation 3.31 GiB. These measurements overlap in
unified memory and must not be added together.

The probe updated all 372 adapter tensors and all four pointer-head tensors;
all saved tensors were finite and the original reference checkpoint was unchanged.
The saved probe is `models/fez-local-probe`; its `training_metrics.json` records
the measurements. Four examples verify hardware and checkpoint handling, not
model improvement. Longer sequences and larger batches need more memory and time.

To repeat in a local terminal, select an unused output directory:

```bash
HF_HOME="$PWD/.cache/huggingface" HF_HUB_OFFLINE=1 \
TRANSFORMERS_OFFLINE=1 TORCH_FORCE_WEIGHTS_ONLY_LOAD=1 \
PYTORCH_ENABLE_MPS_FALLBACK=1 .venv-kev/bin/python -m kev.train \
  --data examples/train-smoke.jsonl \
  --base Qwen/Qwen3.5-0.8B-Base \
  --base_revision dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68 \
  --init_from models/reference \
  --epochs 1 --lr 2e-5 --batch 1 --accum 1 --dtype fp32 --device mps \
  --p_none 0 --p_none_distract 0 --p_distract 0 --seed 553 \
  --out models/fez-local-probe-002
```

The benchmark now supplies separate training, calibration, and test scenarios.
Use its `miner-training.jsonl` as the next experiment's training input. Training
resets the saved temperature to 1.0; calibrate on the separate development split
before comparing probability quality with the published calibrated baseline.
