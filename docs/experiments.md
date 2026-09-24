# Fez local experiments

Run date: 2026-09-24. The first two experiments used CPU, Torch, FP32 and performed no training. A subsequent local GPU training probe is recorded at the end. No experiment made chain calls.

This file is the versioned experiment summary. Model checkpoints, private
datasets, generated round JSON, and the detailed `runs/` evidence referenced
below remain local and are excluded from Git.

Fez is the project/model name. Both candidates start from the published Kev 0.8B checkpoint on Qwen3.5-0.8B. UID 1 retains its published temperature; UID 2 changes only temperature to 1.0. Adapter files and all other head fields were checked for equality.

## Results

| Candidate | Temperature | Correct / 40 | Family-macro Brier ↓ | Skill | Wrong at ≥90% confidence | Dry-run weight |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| UID 1 | 2.4061 | 28 | 0.462489 | 0.2839 | 0 | 0.4904 |
| UID 2 | 1.0000 | 28 | 0.455276 | 0.2951 | 3 | 0.5096 |

Uniform baseline Brier: 0.645833. Lower Brier is better. Weights are the output of the provisional local reward formula; they were not submitted to subnet 553.

| Family | Cases | Correct, both candidates | Brier, published temperature | Brier, temperature 1 |
| --- | ---: | ---: | ---: | ---: |
| evidence | 12 | 11 | 0.270447 | 0.152248 |
| policy | 8 | 5 | 0.417533 | 0.396712 |
| routing | 12 | 10 | 0.312161 | 0.264986 |
| severity | 8 | 2 | 0.849818 | 1.007160 |

On the 32 clean cases: both candidates got 21/32 correct; macro Brier was 0.438190 versus 0.442291. The other eight cases reuse facts, so the 40 outcomes are not independent observations.

## Matched perturbations

| Change | Pairs | Answer changed | Correct → wrong | Wrong → correct |
| --- | ---: | ---: | ---: | ---: |
| choice_order | 4 | 1 | 1 | 0 |
| instruction_injection | 4 | 0 | 0 | 0 |

Counts apply to both candidates because temperature did not change any top answer. Four pairs per perturbation only identify failures in these examples; they do not certify robustness.

## Errors

| Case | Expected | Answer | Confidence, published temperature | Confidence, temperature 1 |
| --- | --- | --- | ---: | ---: |
| policy-day-30 | true | false | 50.316% | 50.761% |
| policy-opened-defective | true | false | 73.649% | 92.222% |
| policy-double-negative | true | false | 51.917% | 54.603% |
| routing-accounts-shipping | accounts | shipping | 55.777% | 83.896% |
| evidence-open-world | insufficient | contradicted | 39.575% | 45.580% |
| severity-minutes-10 | 1 | 0 | 57.299% | 77.577% |
| severity-users-100 | 1 | 0 | 47.060% | 60.077% |
| severity-minutes-59 | 1 | 0 | 37.997% | 43.275% |
| severity-minutes-60 | 2 | 0 | 37.710% | 44.142% |
| severity-urgent-word | 0 | 2 | 76.082% | 97.091% |
| severity-quiet-word | 2 | 0 | 83.480% | 99.163% |
| routing-denied-billing-reordered | shipping | billing | 53.481% | 76.814% |

## Interpretation

Temperature can improve probability scores without learning anything or correcting an answer. These results are descriptive diagnostics on handwritten public cases, not evidence that either setting is generally better. Do not tune on this corpus and then report it as an unseen test.

The apparent calibration winner changes with the case mix: temperature 1.0 has lower Brier over all 40 cases, but the published temperature has lower Brier on the 32 clean cases. Sharpening also increases high-confidence mistakes from zero to three. This is not enough evidence to replace the published temperature.

The request-to-model conversion was checked for every case: all instruction strings and option-key mappings reached the model correctly. Severity failed six of eight cases, including following emotional wording over the stated numerical rules. One routing answer became wrong solely after reversing option order.

The next training experiment should use separate training, calibration, and test data, with all paraphrases and perturbations of one underlying scenario kept in the same split. Freeze the unseen test before selecting a temperature or training an adapter.

## Reproducibility

- Cases: `examples/diagnostics.jsonl`; full predictions and measured latencies: `round-fez-diagnostics-001.json`.
- Dataset SHA-256: `b0d2ada1c44acd0feadede1f2c7335ab243a013754c0bb54cde245bb6112ebbc`.
- Base revision: `dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68`; Kev commit: `30c619b0527501cfdd448cb6eb9887e2af454603`.
- The README contains the rerun command. Scoring and proposed weights were independently recomputed from the saved probabilities.
- The two probability sets matched the expected temperature transform within a maximum absolute difference of 8.5e-08.

## Follow-up: explicit severity options

The same eight severity scenarios were run again with the published checkpoint. Each answer option now included its full rule; facts, question instructions, option order, and labels stayed the same. This change was chosen after inspecting errors, so it is an exploratory retest on known cases.

Result: 4/8 correct, Brier 0.711699, skill 0.0000, and 0 wrong answers at ≥90% confidence. The original short options scored 2/8 correct with Brier 0.849818.

| Case | Expected | Answer | Confidence |
| --- | --- | --- | ---: |
| severity-low-explicit | 0 | 1 | 53.329% |
| severity-minutes-10-explicit | 1 | 1 | 46.551% |
| severity-users-100-explicit | 1 | 0 | 45.695% |
| severity-minutes-59-explicit | 1 | 1 | 38.823% |
| severity-minutes-60-explicit | 2 | 2 | 43.354% |
| severity-data-loss-explicit | 2 | 2 | 40.584% |
| severity-urgent-word-explicit | 0 | 2 | 57.934% |
| severity-quiet-word-explicit | 2 | 0 | 56.396% |

Explicit descriptions improved this small retest from 2/8 to 4/8 correct: three answers were corrected and one previously correct answer became wrong. The model still followed emotional wording over the measurements in both conflicting-description cases. This does not establish a general improvement on unseen cases.

The severity-only round produced an empty weight map because the candidate did not beat the uniform Brier baseline. This also exercises the evaluator’s no-eligible-candidate path.

Cases: `examples/severity-explicit.jsonl`. Full report: `round-fez-severity-explicit-001.json`. Dataset SHA-256: `f7b763270d20b7c8133a4bb77b5ce4ed81debeb82f4691b791aa454c39af12a4`.

## Local GPU training probe

An Apple M4 Pro with 24 GiB of unified memory completed a real LoRA and pointer-head fine-tune. PyTorch MPS was available outside the Codex sandbox; sandboxed checks had reported it unavailable.

Four short, training-only routing examples in `examples/train-smoke.jsonl` produced four optimizer steps in **7.84 seconds** of training-loop time, excluding model load/save. Settings: FP32, batch 1, gradient accumulation 1, learning rate 2e-5, one epoch, seed 553. Peak process RSS was **3.76 GiB**; sampled GPU allocation was 3.31 GiB. These overlapping unified-memory measurements must not be added together.

All 372 adapter tensors and all four pointer-head tensors changed. Saved weights were finite, and the reference checkpoint hash stayed unchanged. The new checkpoint is `models/fez-local-probe`; measurements and initialization provenance are saved in its `training_metrics.json` and `training_config.json`.

The checkpoint reloaded through the normal Fez evaluator on MPS and answered all six public smoke questions correctly. Full report: `round-local-training-probe.json`. The original baseline already answered those six correctly. This confirms local training, checkpoint saving, and evaluation work; it does not demonstrate a quality improvement. The probe's temperature is 1.0, so its Brier score is not a controlled comparison with the published calibrated baseline.

The README contains the repeatable training command. A meaningful candidate experiment still needs separate training, calibration, and test scenarios.

## Two-miner, one-validator network rehearsal

Run 002 completed with two separate miner processes and one validator process. Both miners used fresh SS58 hotkeys. The validator authenticated signed announcements against a local allowlist, downloaded checkpoints from the miner HTTP endpoints, verified their hashes, and evaluated each on the same 40 diagnostic cases. No manual submission manifest or chain write was used.

| Miner | Checkpoint | Correct / 40 | Brier ↓ | Proposed weight | Median ms | p95 ms | Model load ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Published Kev baseline | 28 | 0.462489 | 0.4918 | 120.7 | 179.7 | 1330.8 |
| 2 | Four-example local training probe | 29 | 0.456368 | 0.5082 | 120.6 | 176.6 | 1134.4 |

Each checkpoint transfer was approximately 45.4 MB. Signatures, downloaded hashes, saved predictions, scores, and normalized weights were checked again from the saved artifacts. Model loading is excluded from per-question times; encoding and GPU synchronization are included. No serving HTTP request or Jev request was timed.

The training probe got one additional diagnostic answer correct. These public, small, correlated examples and different checkpoint temperatures do not establish a generally better model. The result proves the network submission-to-reward path, not production model quality.

Reports: `runs/rehearsal-002/validator/report.json`, `announcements.json`, and `submissions.json`; process identities: `runs/rehearsal-002/processes.json`. The launcher stops all child processes when it exits. Run 001 stopped before scoring because resolving the virtual-environment executable symlink removed its package environment; the launcher now preserves that symlink and the process test covers the regression.

Run 003 repeated the real-model round after adding process-group cleanup. Scores and proposed weights were identical; median latency was 122.0 ms for miner 1 and 122.1 ms for miner 2, with p95 latency of 180.2 ms and 177.6 ms respectively. Both signatures, downloaded hashes, scores, and weights were independently verified from the saved artifacts in `runs/rehearsal-003/validator/report.json`. All three tests passed, including the regression check that worker children stop with the launcher.

## Frozen benchmark baseline

The new synthetic benchmark separates 224 training, 112 calibration, and 224 test questions by rule scenario. Each base case has one matched perturbation, so the test contains 112 paired groups across 16 scenarios. Files were frozen before baseline inference. The native training export required a label-type correction; revision `.private/benchmarks/fez-v1-002` preserves all three original case files byte-for-byte. All 224 training exports then passed through Kev's real data loader and materializer.

The published checkpoint, with its original temperature, scored 146/224 (65.18%) overall and 80/112 (71.43%) on clean questions. Mean family Brier loss was 0.458716 against uniform 0.645833. No wrong answer had at least 90% confidence. Both members of 58/112 pairs were correct; 81/112 pairs received the same answer. Median inference latency was 173.0 ms, p95 177.0 ms, and model load 1.65 seconds on the M4 Pro FP32 path. These are measurements for a different workload from the earlier 40-case diagnostic; no Jev comparison was performed.

Per-family correct counts: policy 42/64, routing 44/64, evidence 21/48, severity 39/48. These are the initial reference scores, not a comparison with a newly trained update. The four-example probe was not selected or tuned on this benchmark. [benchmark.md](benchmark.md) records the procedure, commands, and limits of the shared synthetic templates. Full results are `.private/benchmarks/fez-v1-002/baseline-test.json` and `baseline-summary.json`.

## First trained candidate: fez-candidate-001

The recipe and input hashes were saved to `runs/fez-candidate-001/plan.json` before training. This candidate warm-starts the original published checkpoint, uses all 224 training exports for one epoch, and makes 56 optimizer steps: learning rate 2e-5, batch 1, accumulation 4, seed 553, MPS FP32. Kev's choice permutation remains enabled; none-of-the-above and distractor insertion are disabled. No calibration or test cases are included in the training export.

Training took 104.28 seconds, including saving but excluding initial model loading. No examples were dropped or truncated. All 372 adapter tensors and all four pointer-head tensors changed and remained finite. Peak process RSS was 4.87 GiB; sampled device allocation was 3.46 GiB. These overlap in unified memory. The original reference and frozen benchmark hashes were unchanged.

Both reference and candidate were evaluated at temperature 1.0 on the 112 calibration cases. The same declared macro-family NLL fitting procedure selected temperatures 2.0705298477 and 1.0717734625 respectively. Calibration accuracy was 71/112 (63.39%) for the reference and 93/112 (83.04%) for the candidate. These are development results, not held-out results. The fitter's NLL objective slightly increased the candidate's calibration Brier loss from 0.269228 to 0.269503; no additional fit or recipe change was made in response.

Raw training artifacts: `models/fez-candidate-001`. Calibrated artifacts: `models/fez-reference-calibrated-001` and `models/fez-candidate-001-calibrated`. `fez.calibrate` uses Kev's existing fitter; its regression check covers incorrect dataset, checkpoint hash, input temperature, and destination reuse, as well as preservation of weight tensors and answer rankings. The complete seven-test suite passed before the held-out run.

Both saved calibrated checkpoints then ran on the unchanged 224-case test set, with the same pinned backbone, validator, MPS device, Torch backend, and FP32 precision. No recipe or temperature was adjusted after this run.

| Held-out measure | Reference, calibrated on this workload | Fez candidate 001 |
| --- | ---: | ---: |
| Correct overall | 146/224 (65.18%) | 183/224 (81.70%) |
| Correct on clean cases | 80/112 (71.43%) | 91/112 (81.25%) |
| Mean family Brier loss ↓ | 0.460147 | 0.294902 |
| Wrong answers at ≥90% confidence ↓ | 0 | 7 |
| Pair agreement | 81/112 (72.32%) | 106/112 (94.64%) |
| Both answers in a pair correct | 58/112 (51.79%) | 89/112 (79.46%) |
| Median decision time | 172.01 ms | 172.05 ms |
| p95 decision time | 174.24 ms | 174.38 ms |

The candidate gained 16.52 percentage points in accuracy and reduced mean family Brier loss by 35.91%, with essentially identical measured latency in this run. The reference's original published temperature scored Brier 0.458716 in the earlier baseline; the table uses the matched calibration procedure instead. Latency excludes model loading and serving HTTP overhead. This was one run on the Mac, not a throughput study or Jev comparison.

| Family | Reference correct | Candidate correct | Candidate ≥90%-confidence errors |
| --- | ---: | ---: | ---: |
| Policy | 42/64 | 51/64 | 0 |
| Routing | 44/64 | 52/64 | 7 |
| Evidence | 21/48 | 36/48 | 0 |
| Severity | 39/48 | 44/48 | 0 |

The confidence tradeoff matters: aggregate Brier improved while high-confidence routing mistakes increased. Keep this as an experimental candidate; the original reference has not been replaced. The existing reward rubric proposes 34.60% to the calibrated reference and 65.40% to the candidate in this local comparison. No weights were sent to the chain, and these local evaluator UIDs do not represent newly connected machines.

Checkpoint hash: `dca402cef751ecafbc74e816b6de044a84eae736f52a334ff5ee2fc946d1e22d`. The final verification re-hashed both evaluated checkpoints, confirmed calibration changed no adapter/head tensors, checked runtime temperatures, recomputed scores and weights from saved predictions, and re-audited the frozen benchmark. Reports are `runs/fez-candidate-001/test-report.json`, `test-summary.json`, and `result.json`; training and calibration provenance are in the same experiment directory and checkpoint folders.

This is evidence of improvement on the small synthetic benchmark with shared templates and correlated scenarios. It does not establish broad real-world quality. Any further confidence work should use development data and fresh held-out scenarios for a new generalization claim, rather than tuning against the seven exposed test mistakes.

## Three-miner persistent fleet

`fez.fleet` packages a separate `start-miner` script and identity for each machine.
The real rehearsal used those scripts for three independent miners, plus one
validator, all on this M4 Pro. Connections used the Mac's private LAN interface;
this verifies the protocol locally, not connectivity to the Mac mini or 4090 PC.
Each process ran with `--rounds 1 --device mps --no-download --poll 1`, reusing
the existing Python environment and pinned base cache. The complete round took
464.76 seconds, including sequential training, transfer, calibration, evaluation,
and result acknowledgments. All four service processes exited with status zero.

Each miner began from the unchanged published reference, trained one epoch on
224 examples at learning rate 2e-5 with batch 1 and accumulation 4, and produced
a distinct checkpoint. Its seed is derived from the round and its own identity.
The shared compute lock serialized the three training jobs on this Mac. The
validator authenticated announcements and checkpoint hashes, calibrated each
candidate on its 112 private calibration questions, and evaluated the saved
calibrated copies on the 224-question frozen development benchmark.

| Miner | Correct / 224 | Brier ↓ | Temperature | ≥90%-confidence errors | Proposed weight | Median / p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 186 (83.04%) | 0.293305 | 0.965936 | 4 | 31.99% | 171.78 / 176.76 |
| 2 | 179 (79.91%) | 0.287240 | 1.071773 | 3 | 32.54% | 171.85 / 177.13 |
| 3 | 186 (83.04%) | 0.254880 | 0.901250 | 8 | 35.47% | 172.06 / 176.78 |

The reward follows probability quality, so miner 2 receives slightly more weight
than miner 1 despite lower accuracy. Miner 3 has the lowest Brier loss and most
high-confidence mistakes. No candidate was promoted to replace the reference.
These repeated, synthetic development measurements validate the automatic loop;
they do not establish fresh generalization, cross-hardware speed, or performance
relative to Jev. Timing includes encoding and synchronized inference and excludes
loading and HTTP serving. No weights were written to the chain.

The final check re-verified signatures, all submitted hashes, unchanged references,
benchmark integrity, recomputed scores and weights, and the results received by
all three miners. The summary and service logs are in `runs/fleet-001/`; the
private round is `.private/fleet-001/validator/state/rounds/ec9736aa349c48fa939daf4012960b83/`.
Portable archives were created before running, so they contain neither evaluation
data nor the local run's checkpoints or virtual environments.

## Mac mini cross-machine check

The Mac mini was discovered at `MINER_HOST` and reached using existing SSH
access. It is an Apple M4 with 16 GiB RAM. Miner 2 is installed at
`/home/operator/fez` using Python 3.13.14, Torch 2.8.0, and the same
pinned package requirements and Kev commit as the local rehearsal. The mini's
older uv did not list Python 3.13.15, so it installed its available Python 3.13
release. No system Python was replaced. All nine transferred base-model files
were hashed against this Mac's cache, and MPS availability was confirmed.

One bounded round trained on the mini and evaluated on this Mac's M4 Pro. The
mini's artifact endpoint was `http://PRIVATE_IPV4:8902`; the validator endpoint
was `http://PRIVATE_IPV4:8900`. Both directions worked without firewall changes.
A separate validator config admitted only miner 2 for this check, with the main
three-miner configuration left unchanged.

The round completed in 280.13 seconds. Accuracy was 178/224 (79.46%), mean family
Brier loss 0.321996, and four incorrect answers had at least 90% confidence.
Median/p95 inference time was 173.85/183.19 ms, measured on the validator's M4 Pro,
not the mini. Its sole-participant weight of 1.0 only normalizes this check; it is
not evidence of beating another candidate. The fixed synthetic benchmark remains
development data, and this candidate did not replace the reference.

The mini received its result and both services exited with status zero. Signatures,
checkpoint hash, unchanged reference, received result, and recomputed score were
checked against the saved artifacts. Records: `runs/fleet-mini-check-001/summary.json`
and `.private/fleet-mini-check-001/validator/state/rounds/fd0056dc506044ce8bb911360a820a61/`.
No chain weights were written. The Windows RTX 4090 PC still awaits setup.

## Published Kev 0.8B update comparison

Both published releases were evaluated again on the same 224 Fez development
questions on this M4 Pro, with the same pinned runtime, MPS FP32 path, and each
checkpoint's published temperature. The new Hub revision is
`9a45d25eb2ab761841196625383fa1dff0e56c1e`; its training provenance confirms it
started from our exact reference revision `54f4f8777356cd5bbbb6c6919c657f26e6f2f6d8`.

| Measure | Pinned release | New release |
| --- | ---: | ---: |
| Correct / 224 | 146 (65.18%) | 154 (68.75%) |
| Mean-family Brier loss, lower is better | 0.458716 | 0.425394 |
| Wrong answers at >=90% probability | 0 | 1 |
| Median / p95 decision time | 176.66 / 179.29 ms | 176.96 / 179.33 ms |

Evidence improved from 21/48 to 30/48 and routing from 44/64 to 49/64. Policy
stayed at 42/64; severity fell from 39/48 to 33/48. Clean-case accuracy also fell
from 80/112 to 75/112. The new release corrected 26 old mistakes and introduced
18 new ones. Its aggregate Brier loss improved 7.26%, with essentially unchanged
latency. The pinned release exactly reproduced its previous probabilities.

Checkpoint hashes, dataset integrity, runtime settings and recomputed scores
were verified. The comparison used published temperatures without local fitting
or training. Reused synthetic cases remain development data, and their paired
structure prevents treating all 224 questions as independent observations.
The current reference was not replaced. The next useful experiment compares
the same Fez fine-tuning recipe from both starting checkpoints while tracking
severity and clean-case regressions.

Full method, family breakdown and rerun commands:
local release comparison at `runs/kev-release-comparison-001/README.md`.

## Matched Fez fine-tuning from both Kev releases

Fresh runs trained from the pinned old and new Kev checkpoints with identical
data and settings: 224 training examples, one epoch, 56 optimizer steps, seed
553, learning rate 2e-5, batch 1, accumulation 4, MPS FP32. Both ran sequentially
on the same M4 Pro and took 98.74/98.73 seconds, including saving and excluding
initial loading. All examples fit the training context; both processed 30,397
forward tokens. All 372 adapter and four head tensors changed and stayed finite.

The same temperature fitter used only the 112 calibration questions, selecting
1.0717734625 for the old-base candidate and 1.4640856959 for the new-base
candidate. The calibrated copies then ran on the unchanged 224 comparison
questions. No setting was changed after seeing their results.

| Measure | Fez from old Kev | Fez from new Kev |
| --- | ---: | ---: |
| Correct / 224 | 183 (81.70%) | 186 (83.04%) |
| Mean-family Brier loss, lower is better | 0.294902 | 0.282746 |
| Wrong answers at >=90% probability | 7 | 6 |
| Clean cases correct / 112 | 91 | 92 |
| Median / p95 decision time | 176.20 / 179.29 ms | 167.90 / 179.50 ms |

New-base severity improved from 44/48 to 47/48 and policy from 51/64 to 53/64;
routing fell from 52/64 to 50/64 and evidence stayed at 36/48. The old-base
candidate's seven confident errors were in routing. The new-base candidate had
two in routing and four in evidence. It corrected six old-base mistakes and
introduced three, reducing aggregate Brier loss by 4.12%.

One seed and three extra correct answers on reused synthetic development data
do not establish a robust winner. The different median timings with nearly
identical p95 also do not establish a speedup. The new-base candidate is worth
further evaluation, with the old-base candidate retained as a control. Neither
replaced the reference and no chain weights were submitted.

Both starting checkpoints, data and runtime sources retained their hashes.
Training arguments matched except for initial checkpoint and output path;
calibration preserved weight tensors. Metrics were independently recomputed.
The old-base run reproduced candidate 001's adapter weights and calibrated
comparison predictions exactly. Full method, artifacts and rerun commands:
local fine-tuning comparison at `runs/kev-finetune-comparison-001/README.md`.

## Fresh authored scenarios for the two trained candidates

Both calibrated candidates were tested without further training or calibration
on 64 newly authored synthetic scenarios, 16 per task family. The cases were
written separately from the previous benchmark generator, checked for exact
prompt and state overlap against 608 earlier cases, and frozen with model hashes
before inference. Each has an answer rationale. Policy and numeric severity
labels were recomputed; other rationales were reviewed by the same author.
This was assistant authorship and review, not independent human adjudication.

| Measure | Fez from old Kev | Fez from new Kev |
| --- | ---: | ---: |
| Correct / 64 | 56 (87.50%) | 56 (87.50%) |
| Mean-family Brier loss, lower is better | 0.232845 | 0.194603 |
| Wrong answers at >=90% probability | 5 | 2 |
| Median / p95 decision time | 120.01 / 131.75 ms | 119.66 / 127.60 ms |

Each model got policy 13/16, routing 16/16, evidence 14/16, and severity 13/16.
New-base Brier loss was lower in all four families and 16.42% lower overall.
Both missed seven of the same cases; each got one other case correct that the
other missed. Shared weaknesses included numeric boundaries, unsuccessful
applications versus previous awards, and conclusions unsupported by current
or item-specific evidence.

Checkpoint hashes, temperatures, data, runtime sources, and recomputed metrics
were verified. This is a small new-scenario test using related task families,
one training seed, and same-author synthetic labels. It supports carrying the
newer base into the next experiment, not a general accuracy or speedup claim.
Both remained experimental and the reference was unchanged. These cases are
now exposed development data; no training was performed on them in this run.

Full method, cases, predictions and verified results:
local fresh-case comparison at `runs/fez-fresh-cases-001/README.md`.

## Windows RTX 4090: first complete miner round

The PC at `PRIVATE_IPV4` completed a real training-to-validator round in
133.85 seconds, including SSH startup and the returned result. Ubuntu 26.04.1
runs under WSL 2 mirrored networking; Python 3.13.15 and Torch 2.8.0+cu128 see
the RTX 4090 through the existing Windows NVIDIA 595.79 driver.

The original fleet recipe trained 224 examples for 56 optimizer steps in
38.75 seconds (FP32, batch 1, accumulation 4), with 4.18 GiB peak allocated
GPU memory. The validator on the M4 Pro independently fetched the signed
checkpoint, calibrated it, and evaluated 224 reused development questions:
183 correct (81.70%), macro Brier 0.286728, and six confident mistakes. The
167.39 ms median inference time belongs to the Mac validator, not the PC.
Two transient polling failures recovered through the existing retry path.

The repeatable check in `runs/fleet-pc-check-001/verify.py` verified signatures,
checkpoint hashes, unchanged input files, 372 changed finite adapter tensors,
four changed finite head tensors, calibration preserving learned weights,
recomputed scores, and the result received by the PC. Miner and validator
exited successfully. No chain weights were written and no model was promoted.

## Larger RTX 4090 Fez fine-tune

The 4090 trained three candidates from the existing newer Fez checkpoint using
2,878 labeled records, BF16 forward passes with FP32 master weights, batch 4,
and accumulation 4. The training-only batch probe selected batch 4 because
larger batches were slower and consumed more memory. The main runs took
645.34 seconds total; the selected two-epoch recipe peaked at 17.30 GiB.

Selection used macro-source Brier on a separate development partition, after
fitting each temperature only on calibration data. On the subsequently opened
1,208-question primary test, the selected candidate scored 1,032 correct
(85.43%) versus 1,005 (83.20%) for an equally recalibrated starting model.
Macro-source Brier fell from 0.314314 to 0.292107 (7.07%), and confident
mistakes fell from 13 to 10. Most accuracy gains were in generated policy
decisions; news and BoolQ each lost one correct answer. Both aggregate
macro-source Brier and accuracy improvements had paired 95% bootstrap
intervals excluding zero, within this corpus and one training seed.

The normal Fez validator loaded the selected artifact successfully. On the
older, reused development benchmark it improved from 186/224 to 195/224
correct, with confident mistakes falling from six to zero relative to the
previous saved calibration. Repeated 4090 inference medians were 42.34 ms for
the selected model and 42.71 ms for the control on the same 128 training
inputs, excluding loading, encoding, and networking. This supports retained
speed, not a training-induced speedup.

The candidate is saved as `models/fez-4090-001-confidence-calibrated`; it was
not promoted or deployed. Training inputs were isolated from the Mac-held
evaluation data, raw and fitted artifact hashes and tensors were verified,
and all PC jobs exited. Public-corpus overlap with upstream training is
unknown, policy templates are shared, and the test is now exposed. These
results do not establish parity across the full Kev benchmark suite.

Full protocol, results, artifacts, and the repeatable verification command:
local 4090 experiment at `runs/fez-4090-sweep-001/README.md`.

## Direct published Kev comparison after the 4090 sweep

The pinned published Kev 0.8B revision `9a45d25e` was subsequently scored on
the same larger test: 1,008/1,208 correct (83.44%), versus selected Fez's
1,032/1,208 (85.43%). The sweep's previous 83.20% control was an older Fez
fine-tune. No new training or candidate selection occurred for this comparison.

Giving Kev the same calibration method reduced its macro-source Brier to
0.312965; Fez scored 0.292107, a 6.66% reduction. Confident mistakes tied at
ten after matched calibration. The Brier paired interval excluded zero;
the equal-source accuracy interval included zero. All net additional correct
answers came from generated policy decisions, with other source changes
cancelling out. This is a task-specific result, not broad Kev benchmark parity.

Verified direct comparison: `runs/kev-vs-fez-4090-001/README.md` (local).

## Optimized 4090 training and a larger dataset

An isolated FLA 0.5.2 training-kernel overlay and WSL C compiler removed the
gated-delta-attention fallback. Forward and gradient checks agreed within 0.48%
relative L2 error on tested shapes. On a matched short workload, warm batch 4
improved throughput 35.2%; batch 8 improved 69.4%. Longer-input measurements
favored batch 4. Oversized attempts were stopped and retained; a CUDA allocator
cap prevented exhausting available GPU memory. No clock, fan, or power settings
were changed.

The final run trained on 21,694 records (18,816 fresh plus 2,878 replay), with
2.34 million forward tokens, in 865.10 seconds. Peak allocation was 13.52 GiB;
median GPU utilization was 44%, median power 187.76 W, peak power 256.43 W,
and maximum temperature 59°C. The 4090 was not saturated by this configuration.

On a fresh 1,120-question test, the larger-data Fez candidate scored 976 correct
(87.14%) versus the previous Fez's 958 (85.54%). Equal-source Brier improved
9.59%, from 0.270160 to 0.244245. All five sources gained correct answers, and
paired grouped 95% intervals excluded zero for macro Brier and accuracy.
However, mistakes at ≥90% confidence increased from 18 to 23. Both models used
the same fresh calibration method. Public upstream contamination and shared
synthetic templates remain limitations; this is not a new comparison with Kev.

The candidate passed the normal validator compatibility check on 32 existing
cases and remains an experimental artifact. No reference promotion or chain
write occurred; all PC training workers exited. The new test is now exposed.

Full measurements and artifact: `runs/fez-4090-opt-001/README.md` (local).
