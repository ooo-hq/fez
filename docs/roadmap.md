# Next milestones

The local training loop and guarded testnet integration are implemented. The next
milestone is one registered training-to-chain round on a fresh testnet subnet.
Public discovery, isolated untrusted-model evaluation, benchmark refresh, and
model release/promotion rules remain work for an open competition.

## Dashboard

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
suites must not be presented as directly comparable.

The [website handoff](website-handoff.md) defines an initial read-only dashboard
using recorded public benchmark data. Live subnet views follow a verified testnet
round and an explicit public aggregate feed; unavailable data stays labeled.
