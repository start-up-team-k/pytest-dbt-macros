"""Run inside the baseline venv (see make_baselines.sh).

1. Copies dbt's cross-database `utils` macros (Apache-2.0) into src/pytest_dbt_macros/vendored/.
2. For every target type, runs `dbt compile` on the fixture project, one model per case in
   tests/baselines/cases.json, and stores the compiled SQL in tests/baselines/<target>/<case>.sql.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests/fixtures/project"
BASE = ROOT / "tests/baselines"
VENDORED = ROOT / "src/pytest_dbt_macros/vendored"

# target type -> profile fields (fake values; nothing connects)
PROFILES = {
    "postgres": dict(host="localhost", port=5432, user="u", password="p", dbname="d", schema="s"),
    "snowflake": dict(account="a", user="u", password="p", database="d", warehouse="w", schema="s"),
    # BigQuery opens a client eagerly, so give it a throwaway service-account key (never used online).
    "bigquery": dict(method="service-account-json", project="p", dataset="s", keyfile_json=None),
    "duckdb": dict(path=":memory:", schema="s"),
}
# vendored directory (inside site-packages/dbt/include) -> pip distribution it comes from
SOURCES = {
    "global_project": "dbt-adapters", "postgres": "dbt-postgres", "snowflake": "dbt-snowflake",
    "bigquery": "dbt-bigquery", "duckdb": "dbt-duckdb",
}


def vendor():
    include = Path(__import__("dbt.include", fromlist=["x"]).__path__[0])
    shutil.rmtree(VENDORED, ignore_errors=True)
    for d in SOURCES:
        shutil.copytree(include / d / "macros" / "utils", VENDORED / d)
    # current_timestamp & friends
    shutil.copy(include / "global_project/macros/adapters/timestamps.sql", VENDORED / "global_project/_timestamps.sql")
    shutil.copy(include / "postgres/macros/timestamps.sql", VENDORED / "postgres/_timestamps.sql")
    for d, dist in SOURCES.items():  # keep each upstream's own license text next to its files
        d_ = metadata.distribution(dist)
        shutil.copy(d_.locate_file(next(f for f in d_.files if f.name == "LICENSE")), VENDORED / d / "LICENSE")
    versions = {d: f"{dist}=={metadata.version(dist)}" for d, dist in SOURCES.items()}
    (VENDORED / "SOURCES.json").write_text(json.dumps(versions, indent=2) + "\n")


def fake_service_account():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    pem = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    return {
        "type": "service_account", "project_id": "p", "private_key_id": "x", "private_key": pem.decode(),
        "client_email": "x@p.iam.gserviceaccount.com", "client_id": "1",
        "token_uri": "https://oauth2.googleapis.com/token",
    }


def compile_target(target, cases, work):
    proj = work / target
    shutil.copytree(FIXTURE, proj)
    (proj / "models").mkdir()
    for name, expr in cases.items():
        (proj / "models" / f"{name}.sql").write_text(expr)
    fields = {**PROFILES[target]}
    if target == "bigquery":
        fields["keyfile_json"] = fake_service_account()
    profiles = {"cedar_fixture": {"target": target, "outputs": {target: {"type": target, "threads": 1, **fields}}}}
    pdir = work / f"profiles_{target}"
    pdir.mkdir()
    (pdir / "profiles.yml").write_text(json.dumps(profiles))  # JSON is valid YAML
    subprocess.run(
        [sys.executable, "-m", "dbt.cli.main", "compile", "--no-populate-cache",
         "--project-dir", str(proj), "--profiles-dir", str(pdir)],
        check=True,
    )
    out = BASE / target
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    for name in cases:
        shutil.copy(proj / "target/compiled/cedar_fixture/models" / f"{name}.sql", out / f"{name}.sql")


STAR_CASES = {  # need a real table: only DuckDB (a local file) can be created without a server
    "star_all": "{{ dbt_utils.star(ref('users')) }}",
    "star_except_prefix": "{{ dbt_utils.star(ref('users'), except=['email'], prefix='u_') }}",
}


def star_baselines(work):
    """`dbt run` creates table `users` (id, name, email) in a temp DuckDB file, then `dbt compile` renders star()."""
    proj = work / "star"
    shutil.copytree(FIXTURE, proj)
    (proj / "models").mkdir()
    (proj / "models/users.sql").write_text("select 1 as id, 'x' as name, 'y' as email")
    for name, expr in STAR_CASES.items():
        (proj / "models" / f"{name}.sql").write_text(expr)
    out = {"type": "duckdb", "threads": 1, "path": str(work / "star.duckdb")}
    (work / "profiles.yml").write_text(json.dumps({"cedar_fixture": {"target": "d", "outputs": {"d": out}}}))
    for cmd, extra in (("run", ["--select", "users"]), ("compile", [])):
        subprocess.run([sys.executable, "-m", "dbt.cli.main", cmd, "--project-dir", str(proj),
                        "--profiles-dir", str(work), *extra], check=True)
    dest = ROOT / "tests/baselines_star"
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir()
    for name in STAR_CASES:
        shutil.copy(proj / "target/compiled/cedar_fixture/models" / f"{name}.sql", dest / f"{name}.sql")


if __name__ == "__main__":
    vendor()
    cases = json.loads((BASE / "cases.json").read_text())
    with tempfile.TemporaryDirectory() as tmp:
        for t in PROFILES:
            compile_target(t, cases, Path(tmp))
        (Path(tmp) / "s").mkdir()
        star_baselines(Path(tmp) / "s")
    dists = ["dbt-core", "dbt-adapters", "dbt-postgres", "dbt-snowflake", "dbt-bigquery", "dbt-duckdb"]
    lines = [f"{d}=={metadata.version(d)}" for d in dists]
    lines.append("dbt-utils==1.4.1 (git tag 1.4.1, copied to tests/fixtures/project/dbt_packages/dbt_utils)")
    (BASE / "VERSIONS.txt").write_text("\n".join(lines) + "\n")
