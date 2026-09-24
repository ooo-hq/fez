# Fez benchmark v1

The local benchmark is built and verified at `.private/benchmarks/fez-v1-002`.
Start with its integrity check:

```bash
.venv-kev/bin/python benchmark.py audit --benchmark .private/benchmarks/fez-v1-002
```

The purpose is to compare updates to the same Fez model on explicit decision
rules, calibrated probabilities, and inference latency. It uses the existing
validator and reward calculation. No new model service, AI judge, or dependency
is required.

## Data and separation

| File | Questions | Paired groups | Rule scenarios | Use |
| --- | ---: | ---: | ---: | --- |
| `train.jsonl` | 224 | 112 | 16 | Inspect the training cases and their answer rules |
| `miner-training.jsonl` | 224 | 112 | 16 | The same training cases in Kev's native training format |
| `calibration.jsonl` | 112 | 56 | 8 | Development and temperature calibration |
| `test.jsonl` | 224 | 112 | 16 | Frozen held-out evaluation |

Each scenario, including its related cases and perturbations, belongs to one
split. Policy fields, evidence subjects, severity contexts, and routing domains
are separated between splits. The instruction templates and underlying rule
families are shared. This measures transfer within these synthetic tasks, not
generalization to unseen task families or representative customer traffic.

Only `miner-training.jsonl` is intended for distribution to miners. It contains
native boolean, choice-key, and integer labels and has passed Kev's actual
`load_records` and `materialize` path. Keep the full bundle, seed, calibration
cases, test cases, and prediction reports with the validator operator. The
bundle is owner-only and `.private/` is ignored by Git. This prevents accidental
sharing; it does not isolate processes running under the same OS account.

The benchmark builder is public and uses shared synthetic templates. Someone
with the generator can train on similar generated cases. A secret seed is not
an anti-gaming mechanism. Opening the subnet requires additional private,
independently authored scenarios and evaluation isolation.

## What has a correct answer

| Family | Rule | Cases in test |
| --- | --- | ---: |
| Policy | Age limit AND (verification OR exception) AND no exclusion; unknown facts cannot establish a condition | 64 |
| Routing | Highest-priority active issue; explicitly denied issues do not count | 64 |
| Evidence | Exact stated attributes, contradiction, and missing information; explicit negation is handled | 48 |
| Severity | Two numeric thresholds plus an overriding flag; higher severity takes precedence | 48 |

Answers come from small deterministic functions with independently specified
boundary tests. Case metadata records the inputs to those functions, allowing
the audit to recompute every label. Representative rendered prompts were also
checked for agreement with the rules. This is generated ground truth, not an
independent human annotation study.

Every base case has one matched variant: either reordered Choice options or a
note that tries to override the rules. Requested answers in those notes are
sampled independently of truth; always demanding the wrong answer would create
a shortcut. The test contains 112 clean cases, 84 note variants, and 28
option-order variants. Noul and Score outcome order is preserved.

The 224 questions are correlated: there are 112 matched pairs and only 16 rule
scenarios. Do not use 224 as the sample size for an independence-based confidence
interval. Variant slices contain different task mixes; compare matched pairs
before attributing a change specifically to an attack or reordered options.

## Freeze and evaluation

`manifest.json` records the benchmark version, generation seed, source hash,
file hashes, and counts. The builder refuses an existing output directory.
The audit checks hashes, labels, exact-prompt overlap, scenario separation,
paired-case integrity, and the training export. This is exact and declared-group
checking, not semantic deduplication. The generated cases also had no exact
prompt overlap with the previous public examples.

All three case files were frozen before baseline inference. Revision `-002`
corrected the training export's label types; its training, calibration, and test
case files are byte-for-byte identical to the first frozen bundle. Keep using
`-002`; the earlier bundle is retained only as a local build record.

Run a submitted checkpoint against this exact test set with the existing CLI:

```bash
PYTORCH_ENABLE_MPS_FALLBACK=1 .venv-kev/bin/python fez.py evaluate \
  --submissions submissions-reference.json \
  --cases .private/benchmarks/fez-v1-002/test.jsonl \
  --base-revision dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68 \
  --runner-python .venv-kev/bin/python --device mps \
  --report .private/benchmarks/fez-v1-002/repeat-test.json

.venv-kev/bin/python benchmark.py summarize \
  --benchmark .private/benchmarks/fez-v1-002 \
  --report .private/benchmarks/fez-v1-002/repeat-test.json \
  --out .private/benchmarks/fez-v1-002/repeat-summary.json
```

Use fresh report filenames. Summarizing a report from another dataset fails.
Reports recompute metrics from saved probabilities, with family and variant
breakdowns, pair agreement, and the fraction of pairs with both answers correct.
The network rehearsal can use this same file through its existing `--cases`
argument. `rehearsal.py` runs two local miners with existing checkpoints;
the [persistent fleet](FLEET.md) supplies three miners that train and submit
automatically. Its repeated rounds reuse this frozen set as development data.
The Mac mini has completed setup and a real cross-machine round. The Windows
RTX 4090 PC still needs its one-time machine setup.

## Baseline result

The published Kev 0.8B checkpoint is the initial Fez reference. Its hash is
`3574c638613970f6967e447a4747fb9815a910dfc59d4c2a2af2f09ee848b28a`.
It ran on the M4 Pro using Torch 2.8.0, FP32, and its published temperature
2.406050072164233. No checkpoint was trained or selected using these test results.

| Measure | Result |
| --- | ---: |
| Overall correct | 146 / 224 (65.18%) |
| Clean cases correct | 80 / 112 (71.43%) |
| Mean family Brier loss (lower is better) | 0.458716 |
| Uniform-prediction Brier loss | 0.645833 |
| Skill used by existing reward rule | 0.289730 |
| Wrong answers with at least 90% confidence | 0 |
| Same answer across a pair | 81 / 112 (72.32%) |
| Both answers in a pair correct | 58 / 112 (51.79%) |
| Median / p95 decision time | 173.0 / 177.0 ms |
| Model loading | 1.65 seconds |

Family accuracy was policy 42/64, routing 44/64, evidence 21/48, and severity
39/48. Evidence handling is a visible weakness; agreement alone would hide
pairs where both answers are wrong.

Brier loss averages equally across families. Accuracy is question-weighted.
Latency includes encoding, inference, and synchronization, excludes model
loading and serving HTTP overhead, and includes the first request. These are
measurements for this workload; they are not a comparison to Jev. Timing does
not currently affect rewards.

The raw local artifacts are `baseline-test.json` and `baseline-summary.json` in
the bundle. The single-reference evaluation's weight of 1.0 is a normalized
single-entry result, not evidence that the checkpoint is ready for production.

Use training cases for fine-tuning and the calibration split for temperature or
development choices. Compare candidates on the same frozen test set, device,
precision, runner, and declared calibration procedure. Repeatedly inspecting
test errors and tuning against them turns the test into development data;
refresh the held-out scenarios before claiming fresh generalization.

## Calibrating a candidate

`calibrate.py` uses the installed Kev temperature fitter and writes a new
checkpoint copy. It accepts only predictions from this bundle's calibration
split at temperature 1.0, checks that they belong to the supplied checkpoint,
and refuses to overwrite a destination. The adapter and head tensors stay
unchanged; the saved temperature and calibration provenance change.

The first experiment fits both reference and candidate with the same procedure:
minimize mean family negative log likelihood over 81 log-spaced temperatures
from 0.25 to 4, using all 112 calibration questions. Each family has equal
weight. The fitter uses a probability floor of 1e-9. Its internal `clean`
eligibility marker includes all of our declared calibration variants; their
original variant names are retained separately. The objective is NLL, so a
better fit need not also lower Brier loss on every set.

For example, after the first experiment's raw calibration evaluation:

```bash
.venv-kev/bin/python calibrate.py \
  --benchmark .private/benchmarks/fez-v1-002 \
  --report runs/fez-candidate-001/calibration-raw.json --uid 2 \
  --checkpoint models/fez-candidate-001 \
  --out models/fez-candidate-001-calibrated-repeat
```

The actual saved first candidate is `models/fez-candidate-001-calibrated`.
Temperature scaling preserves the chosen answer. Test inference runs again
from the saved checkpoint to measure its actual probabilities and latency;
postprocessed calibration timings are not a fresh speed measurement.

The [first candidate experiment](experiments.md#first-trained-candidate-fez-candidate-001)
completed training, calibration, and a frozen test comparison. Accuracy rose
from 65.18% to 81.70% with about 172 ms median latency for both, while wrong
answers at 90% or higher confidence increased from zero to seven. The candidate
is retained for further evaluation; it has not replaced the reference.
