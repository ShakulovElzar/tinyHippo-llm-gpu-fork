# MN5: copy, run and fetch the 12% jobs

Replace `<user>` with the BSC user name. Hosts `glogin1.bsc.es` (login) and `transfer1.bsc.es` (data
transfer) are the usual MN5 GPP names; check them in the BSC access e-mail. Remote folder: `~/tinyHippo-llm-gpu`.

## 1. Copy the code (on the Mac, from the repo root)

Only files tracked by git, plus the memory file that the flag files need (`--ec-memories`, not in git):

```bash
rsync -av --files-from=<(git ls-files) ./ <user>@transfer1.bsc.es:~/tinyHippo-llm-gpu/
rsync -av --relative out/nous/mem3.json <user>@transfer1.bsc.es:~/tinyHippo-llm-gpu/
```

## 2. Environment (on MN5, once)

Module names from `docs/setup/COMPATIBILITY.md` (NEST 3.9, Python 3.9). Check them with `module avail nest`.

```bash
ssh <user>@glogin1.bsc.es
cd ~/tinyHippo-llm-gpu
module load gcc/11.2.0 python/3.9.11 nest/3.9.0 hdf5/1.12.1-parallel intelmpi/2021.4.0
python3 -c "import nest, numpy, scipy, h5py; print(nest.__version__, numpy.__version__)"
```

The module lines must also be active in the job: run `sbatch` from a shell where they are loaded
(`--export=ALL` passes the environment).

## 3. Submit (on MN5, from `~/tinyHippo-llm-gpu`)

Launcher `hpc/run_flags.sh` runs the exact 1% flags of a WORKLOG config at `SCALE` (default 12),
50 cores, 20 h wall. Output: `results/<NAME>_12pct_s<SEED>.h5`.

Relay through the full loop, WORKLOG §44 (`m1`), 2 seeds:

```bash
sbatch --export=ALL,FLAGS=hpc/flags/m1.flags,NAME=m1,SEED=202 hpc/run_flags.sh
sbatch --export=ALL,FLAGS=hpc/flags/m1.flags,NAME=m1,SEED=303 hpc/run_flags.sh
```

Consolidation with the covariance rule, WORKLOG §48 (`L48`) and its no-plasticity twin, 2 seeds:

```bash
sbatch --export=ALL,FLAGS=hpc/flags/L48.flags,NAME=L48,SEED=202 hpc/run_flags.sh
sbatch --export=ALL,FLAGS=hpc/flags/L48.flags,NAME=N48,SEED=202,EXTRA="--no-stc-hook --no-mpfc-assoc" hpc/run_flags.sh
sbatch --export=ALL,FLAGS=hpc/flags/L48.flags,NAME=L48,SEED=303 hpc/run_flags.sh
sbatch --export=ALL,FLAGS=hpc/flags/L48.flags,NAME=N48,SEED=303,EXTRA="--no-stc-hook --no-mpfc-assoc" hpc/run_flags.sh
```

Check: `squeue -u <user>`; log: `Nest_flags_<jobid>.slurmout`.

## 4. Fetch the results (on the Mac, from the repo root)

```bash
rsync -av <user>@transfer1.bsc.es:~/tinyHippo-llm-gpu/results/ res/2026-11-mn5/
rsync -av <user>@transfer1.bsc.es:'~/tinyHippo-llm-gpu/Nest_flags_*.slurm*' res/2026-11-mn5/logs/
```

## 5. Score (on the Mac)

```bash
.venv/bin/python analysis/score_chain.py res/2026-11-mn5/m1_12pct_s202.h5 res/2026-11-mn5/m1_12pct_s303.h5
.venv/bin/python analysis/score_cons.py res/2026-11-mn5/L48_12pct_s202.h5 res/2026-11-mn5/N48_12pct_s202.h5
.venv/bin/python analysis/score_cons.py res/2026-11-mn5/L48_12pct_s303.h5 res/2026-11-mn5/N48_12pct_s303.h5
```

Not checked yet: run time at 12% for these configs, and that every flag behaves the same under NEST 3.9.
