# Fez

**Fez** is the working name for the decision model and its training subnet.
The current local baseline is the published Kev 0.8B adapter on Qwen3.5-0.8B.
The first 224-example fine-tune improved held-out accuracy from 65.18% to 81.70%
on the local synthetic benchmark, at about 172 ms per decision for both versions.
It also introduced seven high-confidence routing errors and remains an
experimental candidate. [Experiment results](experiments.md#first-trained-candidate-fez-candidate-001)
record that tradeoff. Kev supplies the model implementation, while this repository
supplies the local submission and scoring loop.

A new Python implementation for the decision-model vertical. Fez will use a
fresh testnet subnet; the existing Bazaar subnet 553 remains separate. No Bazaar
runtime is imported.

The implemented loop includes signed miner announcements, checkpoint transfer,
validator-owned inference, probability scoring, and a dry-run weight vector.
An optional [testnet mode](TESTNET.md) checks registered hotkeys and can
publish weights through the pinned Bittensor SDK. The default remains local.
The subnet ID must be explicit. Mainnet is rejected.

## Next milestones and planned dashboard

This repository versions the local prototype and testnet integration before deployment.
It includes source, tests, pinned dependencies, setup instructions, and
experiment summaries. Keep wallets, signing
keys, machine-specific bundles, private evaluation data, model checkpoints,
and raw run directories outside Git. Model releases should be referenced by
immutable artifact hashes and download locations.

Paths under `runs/`, `models/`, and `.private/`, and generated submission/round
JSON files, refer to local artifacts excluded from Git. A fresh clone does not
include trained Fez candidates or the private evaluation data. The runtime
setup below downloads the pinned public reference; `benchmark.py` and `fleet.py`
generate new local benchmark and miner bundles.

Testnet integration uses a configured roster of registered hotkeys and the
existing private LAN transport. It still needs matching wallet files and a
bounded live training-to-chain rehearsal. Public discovery, an open competition
sandbox, and continuous deployment are not implemented. See [TESTNET.md](TESTNET.md).

Dashboard requirements saved from the Teutonic discussion (2026-09-24):

- Current winning Fez checkpoint, version/hash, download, and winner history.
- Decision accuracy, Brier probability score, and highly confident mistakes;
  show dataset/rubric versions and comparable evaluation settings.
- Median and p95 response latency, with the measured hardware and timing scope.
- Submission queue, evaluation progress, and per-round candidate comparisons.
- Miner/validator health and published chain weights/reward allocation, with
  testnet status clearly labeled.

Use Teutonic's visibility into model progress as inspiration. Fez's dashboard
should report its decision-model results; percentages from different benchmark
suites must not be presented as directly comparable. Dashboard implementation
is deferred until the subnet loop works on testnet.

The latest larger-data experiment scored 976/1,120 correct (87.14%) versus
the previous Fez's 958/1,120 (85.54%), with a 9.59% lower equal-source Brier.
Highly confident mistakes increased from 18 to 23, so the candidate remains
experimental. These results use a different test from the older 224-question
benchmark below. See [the experiment summary](experiments.md#optimized-4090-training-and-a-larger-dataset).

## Benchmark

The [Fez benchmark](BENCHMARK.md) is built locally at
`.private/benchmarks/fez-v1-002`: 224 training questions, 112 calibration
questions, and 224 held-out questions across policy, routing, evidence, and
severity. Rule scenarios and paired variants stay within one split. It is a
synthetic local benchmark with shared templates; the private files and seed
do not provide production anti-gaming protection.

```bash
.venv-kev/bin/python benchmark.py audit --benchmark .private/benchmarks/fez-v1-002
```

The published checkpoint scored 146/224 correct (65.18%), with mean family
Brier loss 0.458716 and 173 ms median decision time on the Mac GPU. The linked
benchmark notes include the frozen-data contract, reproduction command, and
limitations. Distribute only `miner-training.jsonl` to miners.

The trained candidate is saved at `models/fez-candidate-001-calibrated`.
Its matched comparison against a separately calibrated reference is recorded
in `runs/fez-candidate-001/test-summary.json`: 183/224 correct, Brier 0.294902,
and seven wrong answers at 90% or higher confidence. The reference remains
unchanged. `calibrate.py` fits only the calibration split and saves new copies.

## One startup command per miner

The [persistent fleet launcher](FLEET.md) packages three separate miners for
this Mac, the Mac mini, and the RTX 4090 PC. After one-time machine setup, run
`./start-miner` inside each miner's folder. It trains, signs and submits a
checkpoint, receives the result, and repeats. The validator runs separately
on this Mac and retains the private calibration and evaluation data.

The fixed training recipe starts from the same reference each round with
different seeds. It tests the complete loop; it does not automatically search
for better training recipes. Three real miner processes and one validator
completed a training-to-score round on this Mac in 7 minutes 45 seconds;
all three miners received their results. The Mac mini is now installed and has
completed a real round with this Mac's validator in 4 minutes 40 seconds.
The Windows RTX 4090 PC is also installed and has completed a real CUDA
training-to-validator round; see [the fleet setup](FLEET.md).
The older two-miner launcher below remains available for a single round with
already-trained checkpoints.

## Two miners and one validator

From this directory, using the existing model environment and checkpoints:

```bash
PYTORCH_ENABLE_MPS_FALLBACK=1 .venv-kev/bin/python rehearsal.py run \
  --device mps --out runs/rehearsal-004
```

Use a fresh output directory each time. The launcher supports macOS, Linux, and
WSL. Use `--device cuda` on a configured NVIDIA machine or `--device cpu` without
an accelerator. In Codex, localhost ports and
the Mac GPU require execution outside its filesystem sandbox. Install the one
extra signing dependency with
`uv pip install --python .venv-kev/bin/python -r requirements-rehearsal.txt`.

The launcher starts **three separate processes** and stops them when the round
finishes or fails. It creates fresh, throwaway SS58 hotkeys in an owner-only run
directory; it never opens an existing wallet. No manual submission manifest is
needed. The default miners publish `models/reference` and
`models/fez-local-probe`; select two other checkpoints with
`--checkpoints /path/to/first /path/to/second`. Training is a separate miner step;
this command rehearses publication, discovery, evaluation, and reward allocation.

1. Each miner freezes its checkpoint and serves only the three artifact files on
   a dynamically assigned localhost port. It signs an announcement containing its
   identity, UID, endpoint, checkpoint hash, and a fresh round ID.
2. The validator accepts announcements from its two allowed hotkeys. Wrong
   signatures, another round's announcements, changed submissions, and identical
   checkpoints from different identities are rejected.
3. The validator downloads each checkpoint over HTTP, checks the size and content
   hash, and runs the existing inference worker. Miners receive neither questions
   nor labels over the protocol. A failed download is ineligible; runtime setup
   failures abort the round.
4. Scores and proposed weights are written to `validator/report.json` inside the
   run directory. Signed announcements, downloaded snapshots, process IDs, and
   individual process logs remain there for inspection.

`runs/rehearsal-003/validator/report.json` records the latest successful real-weight run:
both miners were discovered, authenticated, downloaded, and evaluated on 40
diagnostic questions. See `experiments.md` for the results. The earlier run 001
aborted on an interpreter-path bug that is now covered by a regression test.

Protocol tests use actual signatures, HTTP transfers, and separate miner/validator
processes. Only the process test's model inference is a deterministic fixture;
it is not a model-quality or speed measurement:

```bash
.venv-kev/bin/python -m unittest -v
```

This is a **closed local rehearsal**. The allowlist simulates registration; these
UIDs and hotkeys have not been registered on subnet 553. All processes share the
operator's OS account, so file permissions and separate processes do not isolate
untrusted code or make this public diagnostic corpus secret. The HTTP client is
restricted to numeric localhost endpoints, disables proxies and redirects, and
bounds artifact transfers. Exact-duplicate detection does not detect near-copies.
An open network still needs live chain identity, isolated evaluation, and a
private, versioned benchmark before testnet migration.

### Speed measurements

The runner keeps each model loaded across its evaluation batch and makes typed
decisions without text generation. `model_load_ms` records loading and device
synchronization separately. `median_ms` and `p95_ms` include request encoding,
forward inference, and synchronization; they include the first question and
exclude model loading, checkpoint transfer, and application HTTP overhead.
These timings are diagnostic and do not affect rewards in this rubric.

The measured Mac M4 Pro FP32 path took approximately **122 ms median / 180 ms
p95 per question** on the latest 40-case run. Model loading is measured separately.
This is not a Jev comparison. The competition selects downloadable weights;
an application can keep its chosen Fez checkpoint resident without routing every
decision through the miner/validator network. CUDA kernels, serving precision,
and batching need a separate, quality-checked benchmark on the target hardware.

## Run locally

```bash
git clone git@github.com:ooo-hq/fez.git
cd fez
python3 -m unittest discover -v
```

This offline contract check needs only Python 3.11+. It checks scoring,
malformed predictions, checkpoint changes, duplicate submissions, and failed
evaluations. Handwritten prediction fixtures are not model-quality results.

For real inference, use the project's Python 3.13 environment and cached model:

```bash
python3 fez.py submit --checkpoint models/reference --uid 1 > submissions-reference.json
python3 fez.py evaluate \
  --submissions submissions-reference.json \
  --cases examples/cases.jsonl \
  --base-revision dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68 \
  --runner-python .venv-kev/bin/python \
  --device cpu \
  --report round-local.json
```

Use a new report filename on each run. Reports are never overwritten. The six
public examples only exercise the inference path; they are not a hidden
benchmark and must not determine real emissions.

To compare two models, make `submissions.json` a JSON list containing both
submission objects. They must have different local UIDs and artifact hashes.
The validator evaluates them sequentially, keeping one model in memory at a time.
UIDs in this local manifest are operator-supplied test identities, not verified
Bittensor registrations.

## Local model experiments

`examples/diagnostics.jsonl` contains 40 handwritten cases: 32 clean questions
across refund policy, support routing, evidence entailment, and incident severity,
plus eight matched variants that reverse choice order or insert misleading
instructions. The rules explicitly cover thresholds, missing facts, and issue
priority. These are public diagnostics, not a held-out benchmark or an emissions
dataset. Paired examples are correlated and must not be counted as independent
evidence of generalization.

The current `submissions.json` compares the published checkpoint (UID 1,
temperature approximately 2.406) with the same trained weights at temperature
1.0 (UID 2). Temperature changes confidence, not the highest-probability answer.
These are local candidate IDs, not actual miners. The temperature-1.0 checkpoint
is an experiment, not a trained improvement.

```bash
python3 fez.py evaluate \
  --submissions submissions.json \
  --cases examples/diagnostics.jsonl \
  --base-revision dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68 \
  --runner-python .venv-kev/bin/python \
  --device cpu --timeout 900 \
  --report round-fez-diagnostics-002.json
```

The existing manifest and checkpoints are local generated artifacts; include both
submission objects when repeating the comparison. Change the report filename for
each run. The first diagnostic run and its interpretation are recorded in
`experiments.md`.

The eight-case follow-up in `examples/severity-explicit.jsonl` keeps the same
severity facts and instructions, but spells out each level's rule in its option
description. Repeat it with the command above using
`--submissions submissions-reference.json`,
`--cases examples/severity-explicit.jsonl`, and a new report filename.
This follows up known errors, so it measures input-format sensitivity rather
than performance on unseen cases.

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

## What miners and validators do

| Part | Responsibility |
| --- | --- |
| Miner | Train a compatible adapter and pointer head; submit the three artifact files and their content hash. |
| Validator | Freeze the submitted bytes, load them using its own Kev runner, and evaluate a private corpus. |
| Scorer | Measure probability quality on each task family and produce candidate weights. |
| Bittensor integration | Eventually resolve authenticated submissions to current registered hotkeys/UIDs and publish weights for testnet 553. |

Miners do not send their own scores or host the evaluation endpoint. Training
can use Kev's existing training pipeline; this repository does not add another
trainer. There is no need for a relay, web UI, database, or HTTP inference service
in the local evaluation loop.

The initial competition fixes the backbone to `Qwen/Qwen3.5-0.8B-Base` at the
specified commit, rank-16 LoRA, a 256-dimensional pointer head, and a 512 MiB
adapter-file limit. All candidates use the same
device, Torch backend and FP32 load request. The pinned runner uses an 8,192-token
row budget and rejects overflow instead of silently truncating evidence. Larger
backbones or different execution profiles should be separate competitions.

## Submission and evaluation contract

A local submission contains `uid`, an absolute `checkpoint` directory, and
`sha256`. Only `adapter_config.json`, `adapter_model.safetensors`, and `head.pt`
are copied into the evaluation snapshot. Hashing covers their filenames and
contents. Symlinks are refused; download adapters with `local_dir` to obtain real
files. Duplicate UIDs and identical checkpoint hashes reject the local batch.
This detects exact duplicates only; it is not plagiarism or Sybil resistance.

Each JSONL case has `id`, `family`, `state`, `question`, and `label`. Questions use
Kev's `noul`, `choice`, or `score` format. Labels are strings: `false`/`true`, a
Choice option key, or a Score level index. Each question needs at least two
outcomes. All benchmark metadata and ground-truth labels stay out of the inference
request. Model confidence fields are never treated as measured accuracy.

The scorer calculates multiclass Brier loss for every question, then averages
within each task family and across families equally. Score questions are scored
as categorical distributions in v1. Accuracy, high-confidence mistakes, and
per-question p95 inference latency are diagnostics.

```text
skill  = max(0, 1 - mean_family_brier / mean_family_uniform_brier)
weight = skill / sum(eligible_skills)
```

If no candidate beats the uniform baseline, the proposed weight map is empty.
Missing answers, invalid probabilities, changed artifacts, and failed model runs
are ineligible. Missing runtime packages or unavailable base-model caches abort
the round; they must not manufacture a bad score for a miner.

This is a starting reward rule for local experiments. Brier is a proper scoring
rule, but thresholding and relative payouts do not by themselves establish an
incentive-compatible mechanism. Uniform prediction is a floor, not a sufficient
production baseline. Benchmark refresh, copying resistance, and submission timing
need explicit rules before opening the competition.

## Runtime setup on another machine

Kev currently needs Python 3.12 or 3.13. Scoring and tests run on Python 3.14 too.
Install the pinned inference dependencies in a separate environment:

```bash
uv venv --python 3.13 .venv-kev
uv pip install --python .venv-kev/bin/python -r requirements-model.txt -r requirements-rehearsal.txt
```

`requirements-model.txt` records the exact installed versions and pins Kev's
source commit. Download the pinned public
artifacts once before offline inference:

```bash
HF_HOME="$PWD/.cache/huggingface" .venv-kev/bin/python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download(
    'jaredpalmer/kev-0.8b', revision='54f4f8777356cd5bbbb6c6919c657f26e6f2f6d8',
    local_dir='models/reference',
    allow_patterns=['adapter_config.json', 'adapter_model.safetensors', 'head.pt'],
)
snapshot_download(
    'Qwen/Qwen3.5-0.8B-Base', revision='dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68',
    allow_patterns=['*.json', '*.safetensors', '*.txt', '*.jinja'],
)
PY
```

The inference worker uses Hugging Face offline mode and Torch weights-only
loading. It runs in a child process with a wall-time limit. **That process is not
an OS security sandbox.** This local version is for operator-trusted checkpoints.
An open miner network needs a runner without network access, credentials, or
access to the validator's private corpus, with enforced RAM/GPU limits. Do not
execute miner-provided Python code.

## Connecting to 553

The new miner and validator programs can replace the deployed Bazaar programs
while retaining the subnet registration. That migration needs an authenticated
checkpoint registry, fresh hotkey-to-UID resolution, independent validator
evaluation, and the Bittensor weight call. A rubric/version transition must keep
old research scores out of new model rewards. Old validators need to be retired
or upgraded; deploying one new validator does not update everyone else.

The chain write can be a direct Python SDK call. A Node-to-Python sidecar is
unnecessary here. Use testnet explicitly, inspect live subnet settings, and
verify applied weights after submission. An empty local weight map must not be
treated as proof that previous on-chain weights were cleared.

Sources checked for this implementation:

- [Kev source and training interface](https://github.com/jaredpalmer/kev)
- [TypeSafe decision primitives](https://docs.typesafe.ai/introduction)
- [Bittensor validator and weight interface](https://www.bittensor.com/docs/guides/validating)
- [Bittensor local chain development](https://www.bittensor.com/docs/guides/local-development)
