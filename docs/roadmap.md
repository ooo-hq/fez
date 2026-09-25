# Next milestones

The local training loop and guarded testnet integration are implemented. The
[first registered training-to-chain round](testnet-round-001.md) completed on
testnet subnet 579, including verification after commit–reveal.
Public discovery, isolated untrusted-model evaluation, benchmark refresh, and
model release/promotion rules remain work for an open competition.

## Dashboard

Planned dashboard capabilities:

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

The [public model page](https://fez.chat/model) presents recorded benchmark results
and the verified testnet round. Live subnet views require an explicit public
aggregate feed; unavailable data stays labeled.
