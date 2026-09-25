# Fez

**A small decision model improved through a Bittensor training competition.**
Fez builds on [Kev](https://github.com/jaredpalmer/kev)'s 0.8B model to return
probabilities for yes/no decisions, choices, and scores without generating text.
This repository contains the miner, validator, benchmark, and testnet integration.

Miners fine-tune the model and submit checkpoints. The validator runs those
checkpoints on its own evaluation data, scores their probabilities, and assigns
weights. The resulting adapter and decision head can be loaded with the pinned
base model for applications to use.

**Status:** local training and evaluation work on Apple Silicon and an RTX 4090.
Registered testnet mode is implemented; the first live training-to-chain round
is pending. A Fez testnet subnet ID has not been published.
There is no published Fez model release or automatic winner promotion yet.

[Documentation](docs/README.md) covers operation, development, evaluation, and
measured results.

## How it works

1. **Train:** each miner fine-tunes the pinned reference and freezes a candidate.
2. **Submit:** the miner signs its checkpoint hash and serves its three artifact files.
3. **Evaluate:** the validator verifies the bytes, calibrates confidence, and runs its private test cases.
4. **Reward:** probability quality determines weights; testnet publication requires an explicit flag.

The current fleet uses a fixed one-epoch training recipe with different seeds.
It exercises the whole loop; model improvements still require controlled training
experiments. Validators measure model outputs themselves rather than accepting
miner-reported scores. See the [evaluation contract](docs/evaluation.md).

## Setup

Use macOS, Linux, or WSL 2 with Python 3.13, Git, and `uv` installed.
Run these commands from the repository root:

```bash
git clone git@github.com:ooo-hq/fez.git
cd fez
uv venv --python 3.13 .venv-kev
uv pip install --python .venv-kev/bin/python -r requirements/model.txt -r requirements/rehearsal.txt
.venv-kev/bin/python -m scripts.download_models
```

Dependencies, Kev's source, the public reference checkpoint, and the base model
are pinned. Downloads happen once; model workers run from the local cache.
For Windows GPU and network setup, follow the [miner guide](docs/mining.md).
The Bittensor SDK is optional until [testnet setup](docs/testnet.md).

## Run a local fleet

1. Generate a benchmark and three miner bundles. Use new output directories:

   ```bash
   .venv-kev/bin/python -m fez.benchmark build --out .private/benchmarks/local
   .venv-kev/bin/python -m fez.fleet init --out .private/fleet-local \
     --benchmark .private/benchmarks/local --host 127.0.0.1
   ```

2. Start the validator for one round:

   ```bash
   .venv-kev/bin/python -m fez.fleet validator \
     --config .private/fleet-local/validator/config.json --rounds 1
   ```

3. In separate terminals at the repository root, start each miner. Repeat for
   `miner-2` and `miner-3`:

   ```bash
   FEZ_PYTHON="$PWD/.venv-kev/bin/python" HF_HOME="$PWD/.cache/huggingface" \
     .private/fleet-local/miner-1/start-miner --rounds 1
   ```

The device is selected automatically: CUDA, Apple MPS, then CPU. Services sharing
one device run their model work sequentially. Reports appear in
`.private/fleet-local/validator/state/rounds/`. No chain writes occur in local mode.
For separate machines, generate bundles using the validator's private IPv4
address and follow [miner setup](docs/mining.md). After setup, each miner needs
one command: `./start-miner`.

## Repository layout

```text
fez/             Scoring, benchmark, calibration, validator, and testnet code
miner/           Training and signed checkpoint submission
scripts/         Pinned model download and two-miner rehearsal
tests/          Scoring, protocol, process, and chain integration checks
docs/           Setup details, benchmark methodology, and experiment history
examples/       Public diagnostic cases and smoke-training data
requirements/   Pinned model, signing, and optional testnet dependencies
```

## Development

```bash
.venv-kev/bin/python -m unittest discover -v
```

Tests exercise real signatures, HTTP transfers, subprocesses, and restart
recovery, with fixture model workers and fake chain RPC. They do not train a
model or send transactions. `python3 -m unittest discover -v` also runs the
stdlib checks; tests requiring unavailable dependencies are skipped.

See [local development](docs/development.md) for checkpoint scoring and the
shorter two-miner rehearsal. Commands use `python -m ...`; old flat script paths
have been replaced. Existing standalone miner bundles keep their bundled code;
regenerate bundles when upgrading them.

## Results and limits

The latest larger-data experiment scored **976/1,120 correct (87.14%)**, versus
958/1,120 (85.54%) for the previous Fez candidate. Equal-source Brier loss fell
9.59%, while high-confidence mistakes increased from 18 to 23. This is an
experimental comparison, not a general claim that Fez beats Kev.
[Experiment history](docs/experiments.md#optimized-4090-training-and-a-larger-dataset)
records the datasets, settings, and tradeoffs.

On the separate [JevBench public comparison](docs/jevbench-public.md), current
Fez and published Kev tied at 147/231 correct (63.64%); Fez's confidence quality
regressed. No official JevBench rank has been measured.

The [synthetic benchmark](docs/benchmark.md) has shared templates and is reused
for development. The current private-LAN services are for operator-controlled
checkpoints; their subprocesses are not an untrusted-model security sandbox.
Public discovery, independent hidden evaluation, and model promotion remain
[future work](docs/roadmap.md).

Model weights, wallets, private datasets, bundles, and raw runs are excluded
from Git. A fresh clone downloads the public Kev reference and generates new
local data; it does not contain the experimental Fez checkpoints.
