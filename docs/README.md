# Documentation

Fez is a decision-model training subnet under development. Start with the
[repository README](../README.md) for installation and a local fleet. Registered
testnet integration is implemented; its first live training-to-chain round is
pending. No Fez model release has been published.

| Task | Documentation |
| --- | --- |
| Run a miner or validator | [Miner setup](mining.md), [testnet integration](testnet.md) |
| Develop and evaluate checkpoints | [Local development](development.md), [evaluation contract](evaluation.md) |
| Understand benchmark methodology | [Synthetic benchmark](benchmark.md) |
| Inspect measured results | [Experiment results](experiments.md), [public JevBench comparison](jevbench-public.md), [aggregate JSON](data/jevbench-public-001.json) |
| Review planned capabilities | [Roadmap](roadmap.md), [website specification](website-handoff.md) |

Example paths in setup guides are relative to the repository root. Private
datasets, wallets, generated bundles, checkpoints, and raw experiment records
are excluded from Git. Reports identify where private inputs prevent exact
reproduction from a public checkout; measured hardware is included where it
affects interpretation.
