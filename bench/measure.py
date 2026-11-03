"""usage: measure.py NAME VENV PROJECT_DIR RUNS -- CMD...  -> one JSON line (CMD runs inside PROJECT_DIR with VENV first on PATH)."""
import json, os, subprocess, sys, time
from pathlib import Path

name, venv, proj, runs = sys.argv[1], Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve(), int(sys.argv[4])
cmd = sys.argv[sys.argv.index("--") + 1:]
env = {**os.environ, "PATH": f"{venv}/bin:{os.environ['PATH']}", "NO_COLOR": "1"}
env.pop("VIRTUAL_ENV", None)

freeze = subprocess.run(["uv", "pip", "freeze", "--python", str(venv / "bin/python")], capture_output=True, text=True, check=True)
site = next(venv.glob("lib/python*/site-packages"))
size_kb = int(subprocess.run(["du", "-sk", str(site)], capture_output=True, text=True).stdout.split()[0])
secs = []
for _ in range(runs):
    (proj / "bench.duckdb").unlink(missing_ok=True)  # (c) starts from an empty database each run
    t = time.perf_counter()
    r = subprocess.run(cmd, cwd=proj, env=env, capture_output=True, text=True)
    secs.append(round(time.perf_counter() - t, 3))
    assert r.returncode == 0, r.stdout + r.stderr
print(json.dumps({"name": name, "packages": len(freeze.stdout.split()), "site_packages_mb": round(size_kb / 1024, 1),
                  "secs": secs, "mean_secs": round(sum(secs) / len(secs), 3)}))
