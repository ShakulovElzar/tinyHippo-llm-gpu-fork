# MN5: run the 12% jobs (for the person with MN5 access)

All commands run on MN5. Nothing is needed from the author's Mac except one small file (step 2).
Replace `<user>` with your BSC user name.

## 1. Get the code (once)

The fork is public on GitHub, branch `llm-work`:

```bash
ssh <user>@glogin1.bsc.es
git clone -b llm-work https://github.com/ShakulovElzar/tinyHippo-llm-gpu-fork.git ~/tinyHippo-llm-gpu
cd ~/tinyHippo-llm-gpu
git log --oneline -1
```

If the login node has no internet access, clone on your own machine and copy the folder:

```bash
git clone -b llm-work https://github.com/ShakulovElzar/tinyHippo-llm-gpu-fork.git tinyHippo-llm-gpu
rsync -av tinyHippo-llm-gpu/ <user>@transfer1.bsc.es:~/tinyHippo-llm-gpu/
```

## 2. Put the memory file in place

The flag files use `--ec-memories out/nous/mem3.json` (3 facts, 855 bytes). It is not in git;
the author sends it separately. Put it here:

```bash
mkdir -p ~/tinyHippo-llm-gpu/out/nous
# copy the received mem3.json into ~/tinyHippo-llm-gpu/out/nous/mem3.json
ls -la ~/tinyHippo-llm-gpu/out/nous/mem3.json
```

## 3. Environment

Module names from `docs/setup/COMPATIBILITY.md` (NEST 3.9, Python 3.9). Check them with `module avail nest`.

```bash
cd ~/tinyHippo-llm-gpu
module load gcc/11.2.0 python/3.9.11 nest/3.9.0 hdf5/1.12.1-parallel intelmpi/2021.4.0
python3 -c "import nest, numpy, scipy, h5py; print(nest.__version__, numpy.__version__)"
```

Run `sbatch` from this shell: `--export=ALL` passes the loaded modules to the job.

## 4. Short test first (about 15–30 min)

The code was tested with NEST 3.10 only. This 1% job with 2 sleep epochs checks that the
flags work under NEST 3.9 before the 20 h jobs:

```bash
sbatch --time=01:00:00 --export=ALL,FLAGS=hpc/flags/L48.flags,NAME=test,SEED=202,SCALE=1,EXTRA="--n-swr 2 --g2-trials 2 --mpfc-cov-eta 0.1 --mpfc-cov-center" hpc/run_flags.sh
squeue -u <user>
```

OK when `results/test_1pct_s202.h5` exists and the log `Nest_flags_<jobid>.slurmout` ends with `>>> Done.`
If it fails, send `Nest_flags_<jobid>.slurmout` and `Nest_flags_<jobid>.slurmerr` to the author.

## 5. The 12% jobs (6 jobs, 50 cores and 20 h each)

Estimate from 1% and 2% (WORKLOG §49 B): about 13 CPU-h and 26 GB peak memory per job.

Relay of a memory through the full loop, WORKLOG §44 (`m1`):

```bash
sbatch --export=ALL,FLAGS=hpc/flags/m1.flags,NAME=m1,SEED=202 hpc/run_flags.sh
sbatch --export=ALL,FLAGS=hpc/flags/m1.flags,NAME=m1,SEED=303 hpc/run_flags.sh
```

Consolidation, WORKLOG §51 (`M51`: learning on CA1 → EC LV and EC LV → mPFC) and its
no-plasticity twin (`N48`), same seed:

```bash
sbatch --export=ALL,FLAGS=hpc/flags/L48.flags,NAME=M51,SEED=202,EXTRA="--mpfc-cov-eta 0.1 --mpfc-cov-center" hpc/run_flags.sh
sbatch --export=ALL,FLAGS=hpc/flags/L48.flags,NAME=N48,SEED=202,EXTRA="--no-stc-hook --no-mpfc-assoc" hpc/run_flags.sh
sbatch --export=ALL,FLAGS=hpc/flags/L48.flags,NAME=M51,SEED=303,EXTRA="--mpfc-cov-eta 0.1 --mpfc-cov-center" hpc/run_flags.sh
sbatch --export=ALL,FLAGS=hpc/flags/L48.flags,NAME=N48,SEED=303,EXTRA="--no-stc-hook --no-mpfc-assoc" hpc/run_flags.sh
```

Check: `squeue -u <user>`. Output: `results/<NAME>_12pct_s<SEED>.h5`.

## 6. Send the results back

```bash
cd ~/tinyHippo-llm-gpu
tar czf mn5_results.tgz results/ Nest_flags_*.slurmout Nest_flags_*.slurmerr
ls -la mn5_results.tgz
```

Expected size: about 100 MB per job, so under 1 GB in total. Copy it off MN5 through
`transfer1.bsc.es` (for example `rsync <user>@transfer1.bsc.es:~/tinyHippo-llm-gpu/mn5_results.tgz .`).

## 7. Score (author, on the Mac, after unpacking into `res/2026-11-mn5/`)

```bash
.venv/bin/python analysis/score_chain.py res/2026-11-mn5/results/m1_12pct_s202.h5 res/2026-11-mn5/results/m1_12pct_s303.h5
.venv/bin/python analysis/score_cons.py res/2026-11-mn5/results/M51_12pct_s202.h5 res/2026-11-mn5/results/N48_12pct_s202.h5
.venv/bin/python analysis/score_mpfc.py res/2026-11-mn5/results/M51_12pct_s202.h5 res/2026-11-mn5/results/N48_12pct_s202.h5
```

Same for seed 303. Not checked yet: the real 12% time on MN5, the module names, and that every
flag behaves the same under NEST 3.9 (step 4 checks the last one).
