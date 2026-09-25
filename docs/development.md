# Local development

Run commands from the repository root after the [installation steps](../README.md#setup).
Those steps create `.venv-kev`, download `models/reference`, and cache the pinned
base model. Python 3.13 is required; native Windows users should use WSL 2.

## Run the tests

```bash
.venv-kev/bin/python -m unittest discover -v
```

The process tests run real HTTP, signatures, checkpoint transfer, calibration,
and restart handling. Training and inference use fixture workers; chain RPC is
faked. Tests need no GPU and never submit transactions. Passing them does not
establish model quality or GPU performance.

## Score the reference checkpoint

```bash
.venv-kev/bin/python -m fez submit \
  --checkpoint models/reference --uid 1 > submissions-reference.json
.venv-kev/bin/python -m fez evaluate \
  --submissions submissions-reference.json --cases examples/cases.jsonl \
  --base-revision dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68 \
  --runner-python .venv-kev/bin/python --device cpu --report round-local.json
```

Use fresh output paths. For multiple candidates, combine their submission objects
into one JSON list; every UID and checkpoint hash must be distinct. The public
example questions are diagnostics, not an emissions benchmark.

The commands below also default to `cpu`. For GPU execution, replace that device
with `mps` on Apple Silicon or `cuda` on a configured NVIDIA host. See
[miner setup](mining.md) for Windows/WSL requirements.

## Train a smoke-test candidate

This four-example run verifies training and checkpoint handling. It is not a
model-quality experiment. Select an unused output directory:

```bash
HF_HOME="$PWD/.cache/huggingface" HF_HUB_OFFLINE=1 \
TRANSFORMERS_OFFLINE=1 TORCH_FORCE_WEIGHTS_ONLY_LOAD=1 \
.venv-kev/bin/python -m kev.train \
  --data examples/train-smoke.jsonl \
  --base Qwen/Qwen3.5-0.8B-Base \
  --base_revision dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68 \
  --init_from models/reference \
  --epochs 1 --lr 2e-5 --batch 1 --accum 1 --dtype fp32 --device cpu \
  --p_none 0 --p_none_distract 0 --p_distract 0 --seed 42 \
  --out models/fez-probe
```

The resulting checkpoint contains the adapter and decision head. Training resets
its saved temperature to 1.0. For a quality experiment, use separate training,
calibration, and test cases as described in the [benchmark guide](benchmark.md).

## Rehearse two existing checkpoints

After the smoke-test training command succeeds:

```bash
.venv-kev/bin/python -m scripts.rehearsal run \
  --checkpoints models/reference models/fez-probe \
  --device cpu --timeout 1800 --out runs/rehearsal
```

This starts two miners and one validator as separate processes, then stops all
three when evaluation finishes or fails. It generates disposable signing keys
and saves `validator/report.json` beneath the output directory. CPU evaluation
can take several minutes; the command allows up to 30 minutes per checkpoint.

This rehearsal submits existing checkpoints. The [persistent fleet](mining.md)
trains a new candidate each round. Neither local mode writes chain weights.
