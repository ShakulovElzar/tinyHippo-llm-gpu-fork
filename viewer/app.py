#!/usr/bin/env python3
"""tinyHippo viewer: start runs and see what the neurons did.

    .venv/bin/python viewer/app.py            # then open http://127.0.0.1:8765

Reads runs from out/: <name>.h5 (spikes, written by replay_scaled.py),
<name>_wiring.h5 (connections, written by viewer/export_wiring.py),
<name>.log and <name>.flags.json. Standard library + numpy + h5py only.
Listens on 127.0.0.1 only.
"""

from __future__ import annotations

import glob
import json
import os
import re
import shlex
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import h5py
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, "out")
PY = sys.executable
PORT = int(os.environ.get("PORT", "8765"))
BIN_MS = 5.0          # rate trace bin
CAUSE_MS = 5.0        # a spike that ARRIVES this long before a spike counts as a cause

# Presets for the launcher. --scale/--threads/--seed/--n-swr/--out-hdf5 are added by the form.
PRESETS = {
    "full-loop": {
        "label": "Full loop: EC -> DG -> CA3 -> CA1 -> cortex, with sleep and lesion test",
        "flags": ("--ec-lii --ec-lii-k 50 --n-patterns 3 --schaffer-k 500 --schaffer-group-frac 0.7 "
                  "--ca1-ec-group-frac 0.7 --cortex-group-frac 0.7 --cortical-recall --cr-cue-frac 0.4 "
                  "--cr-prime-rate 120 --cr-prime-weight 1.0 --dg --dg-scale 1 --het 0.30 --het-wcomp 2.3 "
                  "--w-ec-dg 0.6 --pp-residual 0.9 --dg-delay-jitter 4.0 --pattern-source ca3 --stc "
                  "--epoch-ms 1000 --prp-threshold 14.0 --ec-lv --mpfc"),
    },
    "replay-dg": {
        "label": "Replay + dentate gyrus only (no cortex; faster)",
        "flags": "--dg --dg-scale 2",
    },
}

JOBS: dict[str, subprocess.Popen] = {}
_CACHE: dict[str, "Run"] = {}
_LOCK = threading.Lock()


# --------------------------------------------------------------------------- data

class Run:
    """One finished run: spikes per population, plus wiring if exported."""

    def __init__(self, name):
        self.name = name
        path = os.path.join(OUT, name + ".h5")
        self.mtime = os.path.getmtime(path)
        self.pops = []          # dicts: name, n, gid_first
        self.t = {}             # pop -> spike times, sorted by time
        self.i = {}             # pop -> cell index, same order as t
        self.by_cell = {}       # pop -> (times sorted by cell then time, offsets[n+1])
        with h5py.File(path, "r") as h5:
            self.attrs = {k: _py(v) for k, v in h5.attrs.items()}
            for name_ in h5:
                g = h5[name_]
                if not (isinstance(g, h5py.Group) and "spk_times" in g and "n_cells" in g.attrs):
                    continue
                n = int(g.attrs["n_cells"])
                gid0 = int(g.attrs["gid_first"])
                t = g["spk_times"][:].astype(np.float64)
                i = g["spk_senders"][:].astype(np.int64) - gid0
                ok = (i >= 0) & (i < n)
                t, i = t[ok], i[ok]
                o = np.argsort(t, kind="stable")
                self.t[name_], self.i[name_] = t[o], i[o]
                o2 = np.lexsort((t, i))
                self.by_cell[name_] = (t[o2], np.searchsorted(i[o2], np.arange(n + 1)))
                self.pops.append({"name": name_, "n": n, "gid_first": gid0})
            # CA3 SUP sequence groups (the learned order), as cell-index arrays.
            self.seq_groups = []
            if "ca3_sup" in h5 and "group_ids" in h5["ca3_sup"]:
                gid0 = int(h5["ca3_sup"].attrs["gid_first"])
                self.seq_groups = [np.asarray(g, dtype=np.int64) - gid0 for g in h5["ca3_sup"]["group_ids"][:]]
        self.pops.sort(key=lambda p: p["gid_first"])
        self.t_max = max((float(v[-1]) for v in self.t.values() if len(v)), default=1000.0)
        self.flags = _read_flags(name)
        self.wiring = None
        wpath = os.path.join(OUT, name + "_wiring.h5")
        if os.path.exists(wpath):
            self.wiring = Wiring(wpath, [p["name"] for p in self.pops])

    def cell_spikes(self, pop, idx):
        t, off = self.by_cell[pop]
        return t[off[idx]:off[idx + 1]]

    def summary(self):
        edges = np.arange(0.0, self.t_max + BIN_MS, BIN_MS)
        pops = []
        for p in self.pops:
            t = self.t[p["name"]]
            counts, _ = np.histogram(t, bins=edges)
            rate = counts / (p["n"] * BIN_MS / 1000.0)
            active = len(np.unique(self.i[p["name"]]))
            pops.append({**p, "n_spikes": int(len(t)), "active_frac": active / max(p["n"], 1),
                         "mean_rate": len(t) / (p["n"] * self.t_max / 1000.0),
                         "rate": np.round(rate, 2).tolist()})
        a = self.attrs
        if "n_epochs" in a and "epoch_ms" in a:          # written by replay_scaled.py
            n_swr, epoch_ms = int(a["n_epochs"]), float(a["epoch_ms"])
        elif "--stc" in self.flags:                      # --n-swr/--epoch-ms apply only with --stc
            n_swr = int(_flag(self.flags, "--n-swr", 1))
            epoch_ms = float(_flag(self.flags, "--epoch-ms", 1000.0))
        else:                                            # one epoch of --sim-ms
            n_swr, epoch_ms = 1, float(a.get("sim_ms", self.t_max))
        windows = []
        for e in range(n_swr):
            for kind in ("fwd", "rev"):
                s, f = a.get(f"swr_{kind}_start"), a.get(f"swr_{kind}_stop")
                if s is not None:
                    windows.append({"kind": kind, "start": e * epoch_ms + s, "stop": e * epoch_ms + f})
        return {"name": self.name, "t_max": self.t_max, "bin_ms": BIN_MS, "pops": pops,
                "windows": windows, "sleep_end": n_swr * epoch_ms, "flags": self.flags,
                "replay": [self.replay(w) for w in windows] if self.seq_groups else [],
                "attrs": {k: v for k, v in a.items() if isinstance(v, (int, float, str, bool))},
                "matrix": self.wiring.matrix() if self.wiring else None,
                "metrics": _log_metrics(self.name)}

    def replay(self, w, pad=20.0, bin_ms=2.0):
        """CA3 SUP group activity around one ripple, and the replay score.

        Score = Spearman rho between group number and the group's mean spike
        time inside the ripple window, the same as replay_score() in
        replay_scaled.py (+1 = groups fire in learned order, -1 = reversed).
        """
        from scipy.stats import spearmanr
        t, i = self.t["ca3_sup"], self.i["ca3_sup"]
        a, b = np.searchsorted(t, [w["start"] - pad, w["stop"] + pad])
        t, i = t[a:b], i[a:b]
        edges = np.arange(w["start"] - pad, w["stop"] + pad + bin_ms, bin_ms)
        heat, mean_t = [], []
        for g in self.seq_groups:
            m = np.isin(i, g)
            c, _ = np.histogram(t[m], bins=edges)
            heat.append(np.round(c / (len(g) * bin_ms / 1000.0), 1).tolist())
            inside = t[m][(t[m] >= w["start"]) & (t[m] <= w["stop"])]
            mean_t.append(round(float(inside.mean()), 2) if len(inside) else None)
        ok = [k for k, v in enumerate(mean_t) if v is not None]
        rho = p = None
        if len(ok) >= 3:
            r = spearmanr(ok, [mean_t[k] for k in ok])
            rho, p = round(float(r[0]), 3), round(float(r[1]), 4)
        return {**w, "t0": float(edges[0]), "bin_ms": bin_ms, "heat": heat, "mean_t": mean_t, "rho": rho, "p": p}

    def spikes(self, t0, t1, cap=250_000):
        out = {}
        for p in self.pops:
            t = self.t[p["name"]]
            a, b = np.searchsorted(t, [t0, t1])
            step = max(1, int(np.ceil((b - a) * len(self.pops) / cap)))
            out[p["name"]] = {"t": np.round(t[a:b:step], 2).tolist(), "i": self.i[p["name"]][a:b:step].tolist()}
        return out

    def neuron(self, pop, idx, t_click):
        spk = self.cell_spikes(pop, idx)
        res = {"pop": pop, "idx": idx, "spikes": np.round(spk, 2).tolist(), "wired": self.wiring is not None}
        if self.wiring is None:
            return res
        W = self.wiring
        ins = W.incoming(pop, idx)
        outs = W.outgoing(pop, idx)
        res["in_by_pop"] = _by_pop(ins, W.names)
        res["out_by_pop"] = _by_pop(outs, W.names)
        if len(spk) == 0:
            return res
        # The spike nearest to where the user clicked.
        k = int(np.argmin(np.abs(spk - t_click))) if t_click is not None else 0
        ts = float(spk[k])
        res["focus_spike"] = round(ts, 2)
        # Causes: input spikes that ARRIVE (t_pre + delay) in the CAUSE_MS before ts.
        # One row per sending neuron: its spikes and synapses in the window are summed.
        causes, n_spk = {}, 0
        for sp, si, w, d in zip(*ins):
            pt = self.cell_spikes(W.names[sp], si)
            a, b = np.searchsorted(pt + d, [ts - CAUSE_MS, ts + 1e-6])
            for tp in pt[a:b]:
                n_spk += 1
                c = causes.setdefault((int(sp), int(si)), {"pop": W.names[sp], "idx": int(si), "t": float(tp),
                                                           "arrive": float(tp + d), "w": 0.0, "n": 0})
                c["w"] += float(w)
                c["n"] += 1
                c["t"], c["arrive"] = min(c["t"], float(tp)), min(c["arrive"], float(tp + d))
        causes = list(causes.values())
        for c in causes:
            c["w"], c["t"], c["arrive"] = round(c["w"], 3), round(c["t"], 2), round(c["arrive"], 2)
        causes.sort(key=lambda c: -abs(c["w"]))
        res["causes"] = causes[:400]
        res["n_causes"] = n_spk
        res["n_cause_cells"] = len(causes)
        res["drive_exc"] = round(sum(c["w"] for c in causes if c["w"] > 0), 3)
        res["drive_inh"] = round(sum(c["w"] for c in causes if c["w"] < 0), 3)
        # Effects: targets that fire within CAUSE_MS after this spike arrives.
        effects = []
        for tp_, ti, w, d in zip(*outs):
            pt = self.cell_spikes(W.names[tp_], ti)
            a, b = np.searchsorted(pt, [ts + d, ts + d + CAUSE_MS])
            if b > a:
                effects.append({"pop": W.names[tp_], "idx": int(ti), "t": round(float(pt[a]), 2),
                                "w": round(float(w), 3)})
        effects.sort(key=lambda c: -abs(c["w"]))
        res["effects"] = effects[:200]
        res["n_effects"] = len(effects)
        res["n_out"] = int(len(outs[0]))
        return res


class Wiring:
    def __init__(self, path, run_pop_names):
        with h5py.File(path, "r") as h5:
            self.names = [s.decode() for s in h5["pop_names"][:]]
            n = h5["pop_n"][:].astype(np.int64)
            sp, si = h5["src_pop"][:].astype(np.int32), h5["src_idx"][:].astype(np.int32)
            tp, ti = h5["tgt_pop"][:].astype(np.int32), h5["tgt_idx"][:].astype(np.int32)
            w, d = h5["weight"][:], h5["delay"][:]
        self.n = n
        off = np.concatenate([[0], np.cumsum(n)])
        self.off = off
        sg, tg = (off[sp] + si).astype(np.int32), (off[tp] + ti).astype(np.int32)
        self.n_syn = len(sg)
        o = np.argsort(tg, kind="stable")
        self.in_ = (sp[o], si[o], w[o], d[o], np.searchsorted(tg[o], np.arange(off[-1] + 1)))
        o = np.argsort(sg, kind="stable")
        self.out = (tp[o], ti[o], w[o], d[o], np.searchsorted(sg[o], np.arange(off[-1] + 1)))
        P = len(self.names)
        key = sp.astype(np.int64) * P + tp
        cnt = np.bincount(key, minlength=P * P)
        wsum = np.bincount(key, weights=w.astype(np.float64), minlength=P * P)
        dsum = np.bincount(key, weights=d.astype(np.float64), minlength=P * P)
        self._matrix = []
        for k in np.nonzero(cnt)[0]:
            self._matrix.append({"src": self.names[k // P], "tgt": self.names[k % P], "count": int(cnt[k]),
                                 "mean_w": round(wsum[k] / cnt[k], 4), "mean_delay": round(dsum[k] / cnt[k], 2),
                                 "per_target": round(cnt[k] / n[k % P], 1)})

    def matrix(self):
        return self._matrix

    def _slice(self, arr, pop, idx):
        g = self.off[self.names.index(pop)] + idx
        a, b = arr[4][g], arr[4][g + 1]
        return arr[0][a:b], arr[1][a:b], arr[2][a:b], arr[3][a:b]

    def incoming(self, pop, idx):
        return self._slice(self.in_, pop, idx)

    def outgoing(self, pop, idx):
        return self._slice(self.out, pop, idx)


def _by_pop(conns, names):
    p, _, w, _ = conns
    out = []
    for k in np.unique(p):
        m = p == k
        out.append({"pop": names[k], "count": int(m.sum()), "mean_w": round(float(w[m].mean()), 4)})
    return sorted(out, key=lambda r: -r["count"])


def _py(v):
    if isinstance(v, bytes):
        return v.decode()
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, np.ndarray):
        return v.tolist()
    return v


def _read_flags(name):
    p = os.path.join(OUT, name + ".flags.json")
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f).get("flags", [])
    return []


def _flag(flags, key, default):
    return flags[flags.index(key) + 1] if key in flags and flags.index(key) + 1 < len(flags) else default


_METRIC = re.compile(r"(rho|ρ|replay|active|L-LTP|specificity|completion|G2|recall|consolidat|tagged|PRP)", re.I)


def _log_lines(name):
    p = os.path.join(OUT, name + ".log")
    if not os.path.exists(p):
        return []
    with open(p, errors="replace") as f:
        txt = f.read()
    # NEST's progress bar uses carriage returns; keep only real lines.
    lines = [ln.split("\r")[-1].rstrip() for ln in txt.split("\n")]
    return [ln for ln in lines if ln and "Model time" not in ln and not ln.startswith("[INFO]")]


def _log_metrics(name):
    return [ln.strip() for ln in _log_lines(name) if _METRIC.search(ln) and len(ln) < 220][-80:]


_RUN_NAME = re.compile(r"[A-Za-z0-9_.-]{1,80}")


def _check_name(name):
    """Run names are plain file names inside out/ (no '/', no '..')."""
    if not _RUN_NAME.fullmatch(name) or name.startswith("."):
        raise ValueError(f"bad run name {name!r}")
    return name


def get_run(name):
    _check_name(name)
    path = os.path.join(OUT, name + ".h5")
    with _LOCK:
        r = _CACHE.get(name)
        wpath = os.path.join(OUT, name + "_wiring.h5")
        stale = r is None or r.mtime != os.path.getmtime(path) or (r.wiring is None and os.path.exists(wpath))
        if stale:
            r = _CACHE[name] = Run(name)
        return r


def list_runs():
    names = set()
    for p in glob.glob(os.path.join(OUT, "*.h5")) + glob.glob(os.path.join(OUT, "*.flags.json")):
        b = os.path.basename(p)
        if b.endswith("_wiring.h5"):
            continue
        names.add(b[:-3] if b.endswith(".h5") else b[:-len(".flags.json")])
    runs = []
    for n in sorted(names):
        job = JOBS.get(n)
        has_h5 = os.path.exists(os.path.join(OUT, n + ".h5"))
        if job is not None and job.poll() is None:
            state = "running"
        elif job is not None and job.returncode != 0:
            state = "failed"
        elif has_h5:
            state = "done"
        else:
            state = "incomplete"
        runs.append({"name": n, "state": state, "has_spikes": has_h5,
                     "has_wiring": os.path.exists(os.path.join(OUT, n + "_wiring.h5")),
                     "mtime": os.path.getmtime(os.path.join(OUT, n + (".h5" if has_h5 else ".flags.json")))})
    return sorted(runs, key=lambda r: -r["mtime"])


def launch(body):
    name = str(body.get("name", ""))
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", name):
        raise ValueError("name: use 1-40 letters, digits, - or _")
    if name in JOBS and JOBS[name].poll() is None:
        raise ValueError("a run with this name is still running")
    if any(j.poll() is None for j in JOBS.values()):
        raise ValueError("another run is still running; wait for it to finish")
    preset = PRESETS.get(body.get("preset"))
    if preset is None:
        raise ValueError("unknown preset")
    scale = int(body.get("scale", 1))
    threads = int(body.get("threads", 8))
    seed = int(body.get("seed", 202))
    n_swr = int(body.get("n_swr", 4))
    if not (1 <= scale <= 3 and 1 <= threads <= 16 and 1 <= n_swr <= 20 and 0 <= seed < 2**31):
        raise ValueError("scale 1-3, threads 1-16, sleep blocks 1-20")
    os.makedirs(OUT, exist_ok=True)
    h5 = os.path.join("out", name + ".h5")
    flags = (["--scale", str(scale), "--threads", str(threads), "--seed", str(seed), "--n-swr", str(n_swr)]
             + preset["flags"].split() + ["--no-figures", "--out-hdf5", h5])
    with open(os.path.join(OUT, name + ".flags.json"), "w") as f:
        json.dump({"name": name, "preset": body.get("preset"), "flags": flags}, f, indent=1)
    log = os.path.join("out", name + ".log")
    cmd = (f"{shlex.quote(PY)} replay_scaled.py {' '.join(shlex.quote(a) for a in flags)} > {shlex.quote(log)} 2>&1"
           f" && echo '>>> simulation done; exporting wiring' >> {shlex.quote(log)}"
           f" && {shlex.quote(PY)} viewer/export_wiring.py {shlex.quote(h5)} >> {shlex.quote(log)} 2>&1")
    JOBS[name] = subprocess.Popen(["/bin/bash", "-c", cmd], cwd=REPO)
    return {"ok": True, "name": name}


def log_tail(name, n=60):
    return _log_lines(_check_name(name))[-n:]


# --------------------------------------------------------------------------- http

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, allow_nan=False, default=_py).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if (self.headers.get("Host") or "").rsplit(":", 1)[0] not in ("127.0.0.1", "localhost"):
            return self._send(403, {"error": "forbidden host"})
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ("/", "/index.html"):
                with open(os.path.join(HERE, "index.html"), "rb") as f:
                    return self._send(200, f.read(), "text/html; charset=utf-8")
            if u.path == "/api/runs":
                return self._send(200, {"runs": list_runs(), "presets": {k: v["label"] for k, v in PRESETS.items()}})
            if u.path == "/api/log":
                return self._send(200, {"lines": log_tail(q["run"])})
            run = get_run(q["run"])
            if u.path == "/api/summary":
                return self._send(200, run.summary())
            if u.path == "/api/spikes":
                return self._send(200, run.spikes(float(q["t0"]), float(q["t1"])))
            if u.path == "/api/neuron":
                t = float(q["t"]) if q.get("t") not in (None, "") else None
                return self._send(200, run.neuron(q["pop"], int(q["idx"]), t))
            self._send(404, {"error": "not found"})
        except (KeyError, ValueError, FileNotFoundError, OSError) as e:
            self._send(400, {"error": f"{type(e).__name__}: {e}"})

    def _local_request(self):
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        origin = self.headers.get("Origin")
        ok_hosts = ("127.0.0.1", "localhost")
        return (host in ok_hosts
                and (origin is None or urlparse(origin).hostname in ok_hosts)
                and (self.headers.get("Content-Type") or "").split(";")[0].strip() == "application/json")

    def do_POST(self):
        if not self._local_request():
            return self._send(403, {"error": "forbidden: POST only from the viewer page"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
            if urlparse(self.path).path == "/api/launch":
                return self._send(200, launch(body))
            self._send(404, {"error": "not found"})
        except (ValueError, json.JSONDecodeError) as e:
            self._send(400, {"error": str(e)})


if __name__ == "__main__":
    print(f"tinyHippo viewer on http://127.0.0.1:{PORT}  (runs from {OUT})")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
