"""Export a few memories from the Nous eval database and give each one a model slot.

Step 3a, option A: a memory from the database becomes one model pattern (slot s =
pattern s, see ``backends/slots.py``). Only the choice and the order of the memories
come from the database; their text does not shape the spikes.

Read-only: the connection runs with ``default_transaction_read_only=on``. Needs
``psql`` and a dotenv file with DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
(the Nous kit's ``eval-db.env``). The output holds database text: keep it in ``out/``,
which is not committed.

    python -m llm.nous_export --env-file ../nous/eval-db.env \
        --agent mab-eval-prod_memory-8f18622a --n 3 --out out/nous/mem3.json
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
from pathlib import Path

from .backends.slots import SlotBank

# Active facts of one agent, oldest first; ties broken by id so the choice repeats.
# Category 'rule' is skipped: those are the agent's own instructions, not benchmark content.
_QUERY = """
select coalesce(json_agg(t), '[]') from (
    select id::text as id, content as text, category, created_at::text as created_at
    from heart.facts
    where agent_id = :'agent' and active and category <> 'rule'
    order by created_at, id
    limit :n
) t
"""


def read_env(path: Path) -> dict[str, str]:
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def fetch(env: dict[str, str], agent: str, n: int) -> list[dict]:
    proc_env = dict(os.environ,
                    PGPASSWORD=env["DB_PASSWORD"],
                    PGSSLMODE=env.get("PGSSLMODE", "require"),
                    PGOPTIONS="-c default_transaction_read_only=on -c statement_timeout=30000")
    out = subprocess.run(
        ["psql", "-h", env["DB_HOST"], "-p", env["DB_PORT"], "-U", env["DB_USER"],
         "-d", env["DB_NAME"], "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1",
         "-v", f"agent={agent}", "-v", f"n={int(n)}"],
        input=_QUERY, env=proc_env, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--env-file", type=Path, required=True)
    ap.add_argument("--agent", required=True)
    ap.add_argument("--n", type=int, required=True, help="number of memories = number of slots")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    rows = fetch(read_env(args.env_file), args.agent, args.n)
    if len(rows) < args.n:
        raise SystemExit(f"agent {args.agent} has only {len(rows)} active facts")
    bank = SlotBank(args.n)
    for r in rows:
        r["slot"] = bank.assign(r["id"])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "source": "nous_mab_wp heart.facts",
        "agent": args.agent,
        "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "n_slots": args.n,
        "memories": rows,
    }, ensure_ascii=False, indent=2))
    for r in rows:
        print(f"slot {r['slot']}: {r['text'][:90]}")


if __name__ == "__main__":
    main()
