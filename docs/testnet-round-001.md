# First verified Fez testnet round

On September 25, 2026, Fez completed a fresh training → signed submission →
validator evaluation → timelocked weight publication → on-chain verification
round on **Bittensor testnet subnet 579**. This was a closed rehearsal with three
controlled miner identities and one validator on one host.

The [aggregate evidence](data/testnet-round-001.json) records checkpoint hashes,
methodology, scores, the successful transaction, and observed chain weights.

## Results

| Miner UID | Correct / 224 | Family-macro Brier ↓ | Requested weight | Observed chain value |
| --- | ---: | ---: | ---: | ---: |
| 1 | 183 (81.70%) | 0.273177 | 34.09% | 65,535 |
| 2 | 180 (80.36%) | 0.278502 | 33.60% | 64,598 |
| 3 | 180 (80.36%) | 0.292567 | 32.31% | 62,125 |

Weights use `max(0, 1 - brier / uniform_brier)`, normalized across eligible
candidates. The chain stores maximum-scaled integers, not percentages. Their
normalized proportions matched the SDK-quantized requested vector within
`2 / 65535`. Accuracy alone does not determine the allocation.

## Chain evidence and interruption

The weight commit succeeded in **block 8,081,301**, extrinsic **8081301-0008**:
`0xccf932d531bd995c6e87dd8e4749e8f0996cc9d24fe92ff388e36ba4a582b36c`.
The validator hotkey was UID 0. Commit–reveal remained enabled.

The RPC connection dropped while awaiting confirmation. The SDK returned an
uncertain result that Fez initially labeled `failed`. Inspection of the block
found both `TimelockedWeightsCommitted` and `ExtrinsicSuccess`. The original
receipt was preserved and reconciled with that evidence; **no transaction was
resent**. Fez now records unknown SDK outcomes as `unknown`, with no automatic
retry. The regression check and all 12 project tests passed.

After reveal, Fez verified the actual weights at **block 8,081,345**, observed at
**2026-09-25 06:40:01 UTC**. Verification checked registered identities, a newer
validator `LastUpdate`, the exact target UIDs, and normalized weight proportions.
Transaction inclusion alone was not treated as proof of revealed weights.

## Method and limits

Each miner trained a distinct checkpoint from the same pinned 0.8B reference:
Qwen3.5-0.8B-Base, revision `dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68`, with
rank-16 LoRA and a 256-dimensional decision head. Training used one epoch over
224 examples, learning rate 2e-5, microbatch 1, accumulation 4, FP32, and a seed
derived from each hotkey and the fresh round identifier.

The validator downloaded and verified the signed artifacts, fitted temperature
on 112 separate calibration questions, and evaluated each calibrated checkpoint
on the same 224 test questions. Calibration minimized equal-family NLL over 81
temperatures from 0.25 to 4. The [synthetic benchmark](benchmark.md) was reused
development data; it is not an independent generalization test.

All four processes ran on an Apple M4 Pro with 24 GiB unified memory using MPS.
A shared compute lock serialized GPU work. This establishes the registered
training-to-chain path, not participation by independent operators or isolation
between hostile miners. The private inputs prevent exact reproduction of these
scores from a public checkout; [the testnet guide](testnet.md) describes how to
run a new rehearsal.

The one-round services exited afterward. The subnet remains registered and
activated, but this report does not claim continuous fleet availability,
mainnet deployment, miner earnings, an open competition, a model release, or
automatic winner promotion. The separate 4B experiment was not used in this run.
