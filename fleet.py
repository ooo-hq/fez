"""Persistent Fez fleet on a private LAN; optional, explicit testnet weight publication."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request
import uuid

from bittensor_wallet import Keypair
import fez
import rehearsal as wire

ROOT = Path(__file__).resolve().parent
LIMIT = 64 * 1024


def canonical(payload):
    return b"fez-fleet/v1\0" + json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def signed(payload, key):
    return {"payload": dict(payload), "signature": key.sign(canonical(payload)).hex()}


def verified(message, hotkey):
    if not isinstance(message, dict) or set(message) != {"payload", "signature"}:
        raise ValueError("invalid signed message")
    if not isinstance(message["signature"], str) or not re.fullmatch("[a-f0-9]{128}", message["signature"]):
        raise ValueError("invalid message signature")
    if not isinstance(message["payload"], dict) or not Keypair(ss58_address=hotkey).verify(
            canonical(message["payload"]), bytes.fromhex(message["signature"])):
        raise ValueError("validator or miner signature failed")
    return message["payload"]


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


@contextmanager
def locked(path, wait=False):
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | (0 if wait else fcntl.LOCK_NB))
        except BlockingIOError as error:
            raise RuntimeError("this service is already running") from error
        yield


def run_child(command, log, device, timeout=3600):
    environment = {**os.environ, "HF_HOME": os.environ.get("HF_HOME", str(ROOT / ".cache/huggingface")), "HF_HUB_OFFLINE": "1",
                   "TRANSFORMERS_OFFLINE": "1", "TORCH_FORCE_WEIGHTS_ONLY_LOAD": "1",
                   "HF_HUB_DISABLE_TELEMETRY": "1", "PYTORCH_ENABLE_MPS_FALLBACK": "1",
                   "PYTHONPATH": str(ROOT) + os.pathsep + os.environ.get("PYTHONPATH", "")}
    # ponytail: one GPU job per user/device; add device-index locks only when multi-GPU hosts exist.
    lock = Path(tempfile.gettempdir()) / f"fez-compute-{os.getuid()}-{device}.lock"
    with locked(lock, wait=True), Path(log).open("ab") as output:
        process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT, env=environment,
                                   start_new_session=True, cwd=ROOT)
        try:
            if process.wait(timeout=timeout):
                raise RuntimeError(f"worker failed; inspect {log}")
        finally:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=6)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL); process.wait(timeout=6)


def signing_key(config):
    if "wallet" in config:
        from bittensor.wallet import Wallet
        key = Wallet(**config["wallet"]).hotkey
        if key.ss58_address != config.get("hotkey", config["validator_hotkey"]):
            raise ValueError("wallet hotkey does not match the configured identity")
        return key
    if "chain" in config:
        raise ValueError("testnet services require a registered wallet hotkey")
    return Keypair.create_from_seed(config["seed"])


def initialize(out, benchmark_path, checkpoint, host, port, miner_ports, identities=None):
    import benchmark
    endpoint = f"http://{host}:{port}"
    wire.endpoint_ok(endpoint, allowed=[endpoint])
    if not 1 <= len(miner_ports) <= 16 or len(set([port, *miner_ports])) != len(miner_ports) + 1:
        raise ValueError("require 1..16 miners and distinct validator/miner ports")
    for p in miner_ports:
        wire.endpoint_ok(f"http://{host}:{p}", allowed=[f"http://{host}:{p}"])
    if identities is not None:
        from testnet import check_config
        check_config(identities)
        if len(identities["miners"]) != len(miner_ports):
            raise ValueError("one registered identity is required per miner port")
        fez.weight_vector([{**m, "skill": 0.} for m in identities["miners"]])
        hotkeys = [identities["validator"]["hotkey"], *[m["hotkey"] for m in identities["miners"]]]
        if len(set(hotkeys)) != len(hotkeys):
            raise ValueError("validator and miners must have distinct hotkeys")
        for item in [identities["validator"], *identities["miners"]]:
            Keypair(ss58_address=item["hotkey"])
            if set(item["wallet"]) - {"name", "hotkey", "path"} or not {"name", "hotkey"} <= item["wallet"].keys():
                raise ValueError("wallet requires name and hotkey, with optional path; never put keys in the roster")
    benchmark_path = Path(benchmark_path)
    benchmark.audit(benchmark_path)
    entry = fez.submission(checkpoint, 0)
    out = Path(out); out.mkdir(mode=0o700, parents=True, exist_ok=False)
    validator_dir = out / "validator"; validator_dir.mkdir(mode=0o700)
    data = validator_dir / "benchmark"; data.mkdir(mode=0o700)
    for name in (*benchmark.FILES, "manifest.json"):
        shutil.copyfile(benchmark_path / name, data / name); (data / name).chmod(0o600)
    validator_seed = "0x" + secrets.token_hex(32)
    validator_identity = {"seed": validator_seed}
    validator_hotkey = Keypair.create_from_seed(validator_seed).ss58_address
    if identities is not None:
        validator_identity = {"wallet": identities["validator"]["wallet"]}
        validator_hotkey = identities["validator"]["hotkey"]
    shared = {"validator": endpoint, "validator_hotkey": validator_hotkey,
              "base_revision": wire.BASE_REVISION, "initial_sha256": entry["sha256"],
              "training_sha256": digest(data / "miner-training.jsonl")}
    if identities is not None:
        shared["chain"] = dict(identities["chain"])
    members = {}
    for index, miner_port in enumerate(miner_ports, 1):
        identity = identities["miners"][index - 1] if identities is not None else None
        uid = identity["uid"] if identity else index
        directory = out / f"miner-{uid}"; directory.mkdir(mode=0o700)
        seed = "0x" + secrets.token_hex(32)
        key = Keypair.create_from_seed(seed)
        secret = {"wallet": identity["wallet"]} if identity else {"seed": seed}
        hotkey = identity["hotkey"] if identity else key.ss58_address
        members[uid] = {"hotkey": hotkey, "port": miner_port}
        wire.write_json(directory / "config.json", {**shared, "uid": uid, **secret, "hotkey": hotkey, "port": miner_port})
        shutil.copyfile(data / "miner-training.jsonl", directory / "miner-training.jsonl")
        fez.stage(entry, directory / "reference")
        for name in ("fleet.py", "rehearsal.py", "fez.py", "kev_runner.py", "testnet.py", "requirements-testnet.txt",
                     "requirements-model.txt", "requirements-rehearsal.txt", "FLEET.md"):
            shutil.copyfile(ROOT / name, directory / name)
        launcher = directory / "start-miner"
        launcher.write_text('#!/bin/sh\nset -eu\ncd "$(dirname "$0")"\nexec "${FEZ_PYTHON:-.venv-kev/bin/python}" fleet.py miner --config config.json "$@"\n')
        launcher.chmod(0o700)
        archive = out / f"miner-{uid}.tar.gz"
        with tarfile.open(archive, "w:gz") as stream:
            stream.add(directory, arcname=directory.name)
        archive.chmod(0o600)
    wire.write_json(validator_dir / "config.json", {**shared, **validator_identity, "members": members,
                    "benchmark_sha256": digest(data / "manifest.json"), "round_timeout": 3600,
                    "round_pause": 60, "result_grace": 30})
    return out


def request(config, path, message=None):
    data = json.dumps(message).encode() if message is not None else None
    req = Request(config["validator"] + path, data, {"Content-Type": "application/json"})
    with wire.opener().open(req, timeout=10) as response:
        body = response.read(LIMIT + 1)
    if len(body) > LIMIT:
        raise ValueError("validator response too large")
    return verified(json.loads(body), config["validator_hotkey"])


def train_candidate(config, directory, job, runtime, device):
    directory = Path(directory)
    for name in ("base_revision", "initial_sha256", "training_sha256"):
        if job.get(name) != config[name]:
            raise ValueError("validator round differs from the installed training configuration")
    if not re.fullmatch("[a-f0-9]{32}", job.get("round_id", "")):
        raise ValueError("invalid round id")
    if digest(directory / "miner-training.jsonl") != config["training_sha256"]:
        raise ValueError("training data changed")
    if fez.checkpoint_hash(directory / "reference") != config["initial_sha256"]:
        raise ValueError("initial checkpoint changed")
    work = directory / "state/jobs" / job["round_id"]; work.mkdir(mode=0o700, parents=True, exist_ok=True)
    candidate = work / "candidate.json"
    if candidate.exists():
        entry = json.loads(candidate.read_text())
        if fez.checkpoint_hash(entry["checkpoint"]) != entry["sha256"]:
            raise ValueError("saved submission was modified")
        return entry
    if shutil.disk_usage(work).free < 2 * 1024**3:
        raise RuntimeError("less than 2 GiB free; archive completed rounds before training again")
    if not (work / "job.json").exists():
        wire.write_json(work / "job.json", job)
    identity = config.get("seed") or config["hotkey"]
    seed = int(hashlib.sha256((config["validator_hotkey"] + identity + job["round_id"]).encode()).hexdigest()[:8], 16) % 2**31
    raw = work / ("training-" + uuid.uuid4().hex)
    command = [runtime, "-u", "-m", "kev.train", "--data", str(directory / "miner-training.jsonl"),
               "--base", fez.BASE, "--base_revision", config["base_revision"], "--init_from", str(directory / "reference"),
               "--epochs", "1", "--lr", "2e-5", "--batch", "1", "--accum", "4", "--dtype", "fp32",
               "--device", device, "--p_none", "0", "--p_none_distract", "0", "--p_distract", "0",
               "--seed", str(seed), "--out", str(raw)]
    print(f"miner {config['uid']}: training round {job['round_id']} on {device}; log {work / 'training.log'}", flush=True)
    run_child(command, work / "training.log", device)
    frozen = work / ("artifacts-" + uuid.uuid4().hex)
    fez.stage(fez.submission(raw, config["uid"]), frozen)
    entry = fez.submission(frozen, config["uid"])
    wire.write_json(candidate, entry)
    return entry


def miner(config, directory, args):
    key = signing_key(config)
    address = urlsplit(config["validator"])
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
        route.connect((address.hostname, address.port)); host = route.getsockname()[0]
    endpoint = f"http://{host}:{config['port']}"
    wire.endpoint_ok(endpoint, allowed=[endpoint])

    class Artifacts(wire.Handler):
        def do_GET(self):
            match = re.fullmatch(r"/artifacts/([a-f0-9]{32})/([^/]+)", self.path)
            if not match or match[2] not in fez.ARTIFACT_FILES:
                self.reply(404, {"error": "unknown artifact"}); return
            try:
                entry = json.loads((directory / "state/jobs" / match[1] / "candidate.json").read_text())
                path = Path(entry["checkpoint"]) / match[2]
                with path.open("rb") as source:
                    self.send_response(200); self.send_header("Content-Length", str(os.fstat(source.fileno()).st_size))
                    self.end_headers(); shutil.copyfileobj(source, self.wfile)
            except FileNotFoundError:
                self.reply(404, {"error": "checkpoint not ready"})

    finished, last_error = set(), None
    with wire.local_server(Artifacts, host, config["port"]):
        print(f"miner {config['uid']}: serving {endpoint}; waiting for validator", flush=True)
        while not args.rounds or len(finished) < args.rounds:
            try:
                job = request(config, "/round")
                if job.get("kind") != "round" or job.get("round_id") in finished:
                    time.sleep(args.poll); continue
                rid = job["round_id"]
                if not re.fullmatch("[a-f0-9]{32}", rid):
                    raise ValueError("invalid validator round")
                work = directory / "state/jobs" / rid
                if job["status"] == "collecting":
                    if "chain" in config:
                        import testnet
                        if job.get("chain") != config["chain"]:
                            raise ValueError("validator round is not for this testnet")
                        if not (work / "candidate.json").exists():
                            with testnet.connect(config) as sub:
                                testnet.preflight(config, sub)
                    entry = train_candidate(config, directory, job, args.runtime_python, args.device)
                    claim = {"round_id": rid, "uid": config["uid"], "hotkey": key.ss58_address,
                             "sha256": entry["sha256"], "endpoint": endpoint}
                    reply = request(config, "/submit", {"claim": claim, "signature": key.sign(wire.canonical(claim)).hex()})
                    if reply.get("status") != "accepted" or reply.get("round_id") != rid:
                        raise ValueError("validator did not acknowledge this round's submission")
                result = request(config, "/results/" + rid)
                if result.get("kind") == "result" and result.get("round_id") == rid:
                    work.mkdir(mode=0o700, parents=True, exist_ok=True)
                    if not (work / "result.json").exists():
                        wire.write_json(work / "result.json", result)
                    ack = {"kind": "ack", "uid": config["uid"], "round_id": rid}
                    request(config, "/ack", signed(ack, key))
                    finished.add(rid)
                    print(f"miner {config['uid']}: round complete; proposed weight {result['weights'].get(str(config['uid']), 0):.4f}", flush=True)
                last_error = None
            except HTTPError as error:
                if error.code not in (404, 409, 503):
                    raise RuntimeError(f"validator rejected request (HTTP {error.code}); check config and validator log") from error
            except (URLError, TimeoutError, ConnectionError, http.client.HTTPException) as error:
                message = str(error)
                if message != last_error:
                    print(f"miner {config['uid']}: validator unavailable; retrying: {message}", flush=True)
                    last_error = message
            time.sleep(args.poll)


def evaluate_round(config, directory, work, registry, args):
    import benchmark
    import calibrate
    if shutil.disk_usage(work).free < 2 * 1024**3:
        raise RuntimeError("less than 2 GiB free; archive completed rounds before evaluating again")
    data = directory / "benchmark"
    if digest(data / "manifest.json") != config["benchmark_sha256"]:
        raise ValueError("benchmark manifest changed")
    benchmark.audit(data)
    entries, failed = [], {}
    attempt = work / ("evaluation-" + uuid.uuid4().hex); attempt.mkdir(mode=0o700)
    for uid, message in sorted(registry.items()):
        claim = message["claim"]; path = attempt / f"raw-{uid}"
        try:
            wire.fetch_checkpoint(claim, path, expected_endpoint=claim["endpoint"], round_scoped=True)
            entries.append(fez.submission(path, uid))
        except (ValueError, OSError, http.client.HTTPException) as error:
            failed[uid] = str(error)

    def evaluate(submissions, cases, name):
        manifest = attempt / f"{name}-submissions.json"; wire.write_json(manifest, submissions)
        report = attempt / f"{name}.json"
        command = [sys.executable, str(ROOT / "fez.py"), "evaluate", "--submissions", str(manifest),
                   "--cases", str(cases), "--base-revision", config["base_revision"],
                   "--runner-python", args.runtime_python, "--device", args.device, "--report", str(report)]
        run_child(command, attempt / f"{name}.log", args.device, timeout=120 + 600 * len(submissions))
        return json.loads(report.read_text())

    fitted = []
    if entries:
        calibration = evaluate(entries, data / "calibration.jsonl", "calibration")
        for entry, row in zip(entries, calibration["miners"]):
            if row["status"] != "evaluated":
                failed[entry["uid"]] = row.get("error", "calibration inference failed"); continue
            target = attempt / f"calibrated-{entry['uid']}"
            try:
                calibrate.fit(data, calibration, entry["uid"], entry["checkpoint"], target)
                fitted.append(fez.submission(target, entry["uid"]))
            except (ValueError, OSError) as error:
                failed[entry["uid"]] = str(error)
    report = evaluate(fitted, data / "test.jsonl", "evaluation") if fitted else {"miners": [], "weights": {}}
    present = {m["uid"] for m in report["miners"]}
    for uid in sorted(int(k) for k in config["members"]):
        if uid not in present:
            report["miners"].append({"uid": uid, "status": "rejected" if uid in failed else "missing", "skill": 0.,
                                     "error": failed.get(uid, "no submission before deadline")})
    report.update(mode="private-lan-development", chain_write=False, benchmark_use="repeated-local-development",
                  weights=fez.weight_vector(report["miners"]), submitted={uid: m["claim"]["sha256"] for uid, m in registry.items()})
    if "chain" in config:
        report.update(mode="testnet-closed-development", chain=config["chain"],
                      identities={uid: item["hotkey"] for uid, item in config["members"].items()})
    wire.write_json(work / "report.json", report)
    return report


def validator(config, directory, args):
    key = signing_key(config)
    members = {int(uid): item["hotkey"] for uid, item in config["members"].items()}
    condition = threading.Condition()
    current, registry, acks = {}, {}, set()
    rounds = directory / "state/rounds"; rounds.mkdir(mode=0o700, parents=True, exist_ok=True)

    class API(wire.Handler):
        def send(self, code, payload):
            self.reply(code, signed(payload, key))

        def do_GET(self):
            with condition:
                if self.path == "/round":
                    self.send(200, current or {"kind": "idle"}); return
                match = re.fullmatch(r"/results/([a-f0-9]{32})", self.path)
                if match:
                    path = rounds / match[1] / "result.json"
                    if path.exists():
                        self.reply(200, json.loads(path.read_text())); return
                self.send(404, {"error": "result not ready"})

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", "-1"))
                if not 0 < length <= wire.MAX_ANNOUNCEMENT or self.headers.get("Transfer-Encoding"):
                    raise ValueError("invalid message size")
                message = json.loads(self.rfile.read(length))
                if not isinstance(message, dict):
                    raise ValueError("message must be an object")
                with condition:
                    if self.path == "/submit":
                        if current.get("status") != "collecting":
                            self.send(409, {"error": "round is not collecting"}); return
                        claim = message.get("claim")
                        if not isinstance(claim, dict):
                            raise ValueError("claim must be an object")
                        uid = claim.get("uid")
                        if type(uid) is not int or uid not in members:
                            raise ValueError("unknown miner")
                        if claim.get("round_id") != current["round_id"]:
                            self.send(409, {"error": "round has changed; request the current round"}); return
                        # Pin downloads to the authenticated caller's TCP source address and assigned artifact port.
                        endpoint = f"http://{self.client_address[0]}:{config['members'][str(uid)]['port']}"
                        updated = dict(registry)
                        wire.register(message, current["round_id"], members, updated, endpoints={uid: endpoint})
                        path = rounds / current["round_id"] / "submissions" / f"{uid}.json"
                        if not path.exists():
                            wire.write_json(path, message)
                        registry.clear(); registry.update(updated)
                        self.send(200, {"status": "accepted", "round_id": current["round_id"]})
                    elif self.path == "/ack":
                        if not isinstance(message.get("payload"), dict):
                            raise ValueError("payload must be an object")
                        uid = message["payload"].get("uid")
                        if type(uid) is not int or uid not in members:
                            raise ValueError("unknown miner")
                        payload = verified(message, members[uid])
                        if payload != {"kind": "ack", "uid": uid, "round_id": current.get("round_id")} or current.get("status") != "complete":
                            self.send(409, {"error": "ack does not match completed round"}); return
                        acks.add(uid); self.send(200, {"status": "acknowledged"})
                    else:
                        self.send(404, {"error": "unknown endpoint"}); return
                    condition.notify_all()
            except (ValueError, TypeError, KeyError, OSError) as error:
                self.send(400, {"error": str(error)[:200]})

    address = urlsplit(config["validator"])
    with wire.local_server(API, address.hostname, address.port):
        print(f"validator: listening at {config['validator']} for {len(members)} miners", flush=True)
        completed = 0
        while not args.rounds or completed < args.rounds:
            chain_state = None
            if "chain" in config:
                import testnet
                with testnet.connect(config) as sub:
                    chain_state = testnet.preflight(config, sub)
            pending = sorted((p for p in rounds.iterdir() if p.is_dir() and (p / "job.json").exists()
                              and not (p / "result.json").exists()), key=lambda p: p.stat().st_mtime)
            if pending:
                work = pending[-1]; job = json.loads((work / "job.json").read_text())
            else:
                rid = uuid.uuid4().hex; work = rounds / rid; work.mkdir(mode=0o700)
                (work / "submissions").mkdir(mode=0o700)
                job = {"kind": "round", "round_id": rid, "status": "collecting", "deadline": time.time() + config["round_timeout"],
                       **{k: config[k] for k in ("base_revision", "initial_sha256", "training_sha256")}}
                if chain_state is not None:
                    job["chain"] = config["chain"]
                wire.write_json(work / "job.json", job)
            if chain_state is not None and not (work / "chain-snapshot.json").exists():
                wire.write_json(work / "chain-snapshot.json", chain_state)
            with condition:
                registry.clear(); acks.clear(); current.clear(); current.update(job)
                for path in (work / "submissions").glob("*.json"):
                    message = json.loads(path.read_text()); c = message["claim"]
                    wire.register(message, job["round_id"], members, registry, endpoints={c["uid"]: c["endpoint"]})
                while len(registry) < len(members) and time.time() < job["deadline"]:
                    condition.wait(min(1, max(.01, job["deadline"] - time.time())))
                current["status"] = "evaluating"
            print(f"validator: evaluating round {job['round_id']} ({len(registry)}/{len(members)} submissions)", flush=True)
            report = json.loads((work / "report.json").read_text()) if (work / "report.json").exists() else evaluate_round(config, directory, work, registry, args)
            fields = ("uid", "status", "skill", "accuracy", "brier", "confident_errors", "median_ms", "p95_ms")
            public = {"kind": "result", "round_id": job["round_id"], "weights": {str(k): v for k, v in report["weights"].items()},
                      "miners": [{k: m[k] for k in fields if k in m} for m in report["miners"]], "chain_write": False}
            if chain_state is not None:
                from bittensor.wallet import Wallet
                with locked(work / "chain.lock"), testnet.connect(config) as sub:
                    outcome = testnet.publish_round(config, work, report, sub, Wallet(**config["wallet"]),
                                                   publish=args.publish_weights)
                public.update(chain=outcome, chain_write=outcome["chain_write"])
                print(f"validator: testnet weights {outcome['status']}", flush=True)
            wire.write_json(work / "result.json", signed(public, key))
            with condition:
                current["status"] = "complete"
                deadline = time.monotonic() + config["result_grace"]
                while not set(registry) <= acks and time.monotonic() < deadline:
                    condition.wait(min(1, max(.01, deadline - time.monotonic())))
            completed += 1
            print(f"validator: completed round {completed}; proposed weights {public['weights']}", flush=True)
            if not args.rounds or completed < args.rounds:
                time.sleep(config["round_pause"])


def prepare_base():
    from huggingface_hub import snapshot_download
    from huggingface_hub.errors import LocalEntryNotFoundError
    cache = Path(os.environ.get("HF_HOME", str(ROOT / ".cache/huggingface"))) / "hub"
    options = {"repo_id": fez.BASE, "revision": wire.BASE_REVISION, "cache_dir": str(cache),
               "allow_patterns": ["*.json", "*.safetensors", "*.txt", "*.jinja"]}
    try:
        snapshot_download(**options, local_files_only=True)
    except LocalEntryNotFoundError:
        print("Downloading the pinned base model for this machine's first start.", flush=True)
        snapshot_download(**options)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="role", required=True)
    create = commands.add_parser("init")
    create.add_argument("--out", required=True)
    create.add_argument("--benchmark", default=".private/benchmarks/fez-v1-002")
    create.add_argument("--checkpoint", default="models/reference")
    create.add_argument("--host", default="127.0.0.1")
    create.add_argument("--port", type=int, default=8900)
    create.add_argument("--miner-ports", type=int, nargs="+", default=[8901, 8902, 8903])
    create.add_argument("--testnet-identities", help="JSON roster of registered UIDs, public hotkeys and wallet paths")
    for role in ("miner", "validator"):
        command = commands.add_parser(role)
        command.add_argument("--config", required=True)
        command.add_argument("--device", choices=("auto", "cpu", "mps", "cuda"), default="auto")
        command.add_argument("--runtime-python", default=sys.executable)
        command.add_argument("--rounds", type=int, default=0, help="0 keeps running; a positive number stops after that many rounds")
        command.add_argument("--poll", type=float, default=5)
        command.add_argument("--no-download", action="store_true", help="use an already-provisioned model cache")
        if role == "validator":
            command.add_argument("--publish-weights", action="store_true", help="publish configured testnet weights after evaluation")
    args = parser.parse_args()
    def stop(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        if args.role == "init":
            identities = json.loads(Path(args.testnet_identities).read_text()) if args.testnet_identities else None
            out = initialize(args.out, args.benchmark, args.checkpoint, args.host, args.port, args.miner_ports, identities)
            print(f"Created validator config and {len(args.miner_ports)} separate miner bundles in {out}"); return
        if args.rounds < 0 or not math.isfinite(args.poll) or args.poll <= 0:
            raise ValueError("rounds must be nonnegative and poll must be positive")
        path = Path(args.config).resolve(); directory = path.parent
        config = json.loads(path.read_text())
        if getattr(args, "publish_weights", False) and "chain" not in config:
            raise ValueError("--publish-weights requires a testnet fleet config")
        signing_key(config)
        if "chain" in config:
            import testnet
            with testnet.connect(config) as sub:
                testnet.preflight(config, sub)
        wire.endpoint_ok(config["validator"], allowed=[config["validator"]])
        args.runtime_python = str(Path(args.runtime_python).absolute())
        state = directory / "state"; state.mkdir(mode=0o700, exist_ok=True)
        with locked(state / "service.lock"):
            if not args.no_download:
                prepare_base()
            if args.device == "auto":
                import torch
                args.device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
            (miner if args.role == "miner" else validator)(config, directory, args)
    except KeyboardInterrupt:
        print("Fez service stopped.", flush=True)
    except (ValueError, OSError, RuntimeError, KeyError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"fez fleet: {error}\n")


if __name__ == "__main__":
    main()
