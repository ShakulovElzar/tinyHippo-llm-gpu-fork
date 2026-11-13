# tinyHippo: Installation & Setup Guide
## Bidirectional SWR Replay + STC Consolidation Model

---

## Quick Start (Local Development)

### 1. Clone repository
```bash
git clone https://github.com/max-talanov/tinyHippo.git
cd tinyHippo
```

### 2. Install base requirements
```bash
pip install -r requirements.txt
```

### 3. Verify NEST installation
```bash
python -c "import nest; print(f'NEST {nest.__version__} ✓')"
```

### 4. Run test simulation (1% scale, ~5 min)
```bash
python bidirectional_replay_watson2025_scaled.py --scale 1pct
# Output: replay_output_1pct/replay_1pct.h5
```

### 5. Generate figures from HDF5
```bash
python replay_plot_from_hdf5.py --in replay_output_1pct/replay_1pct.h5 \
  --save-prefix figures/run1
```

---

## HPC Installation (MareNostrum5 or equivalent)

### 1. Load modules
```bash
# Standard stack
module load gcc/11.2.0 python/3.9.11
module load nest/3.9.0
module load hdf5/1.12.1-parallel   # For MPI-parallel I/O

# Optional: Intel MPI
module load intelmpi/2021.4.0
```

### 2. Create Python virtual environment
```bash
python -m venv tinyHippo_env
source tinyHippo_env/bin/activate
```

### 3. Install requirements (MPI-enabled)
```bash
pip install --upgrade pip setuptools
pip install -r requirements.txt
pip install mpi4py>=3.0.0   # Must be installed AFTER module load mpi
```

### 4. Verify MPI+NEST integration
```bash
python -c "
import nest
from mpi4py import MPI
print(f'NEST {nest.__version__} with MPI ✓')
print(f'MPI rank: {MPI.COMM_WORLD.Get_rank()}')
"
```

### 5. Submit job to SLURM
```bash
sbatch run_bidir_replay.sh
```

Example `run_bidir_replay.sh`:
```bash
#!/bin/bash
#SBATCH --job-name=tinyHippo
#SBATCH --nodes=16
#SBATCH --ntasks-per-node=4
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --output=logs/replay_%j.log
#SBATCH --error=logs/replay_%j.err

module load gcc python nest hdf5/intelmpi

source tinyHippo_env/bin/activate

mpirun -n 64 python bidirectional_replay_watson2025_scaled.py \
  --scale 12pct \
  --out-hdf5 replay_output_12pct/replay_12pct.h5
```

---

## Scale-Specific Usage

### 1% Scale (Debug/Development)
```bash
# ~7.7k neurons, 1 CPU, ~5 min
python bidirectional_replay_watson2025_scaled.py --scale 1pct
```

### 12% Scale (HPC Development)
```bash
# ~93k neurons, 16 nodes, ~25 min
mpirun -n 64 python bidirectional_replay_watson2025_scaled.py --scale 12pct
```

### 100% Scale (Full Rat Hippocampus)
```bash
# ~781k neurons, 256 nodes, ~3–5 h
mpirun -n 256 python bidirectional_replay_watson2025_scaled.py --scale 100pct
```

---

## Project Structure

```
tinyHippo/
├── bidirectional_replay_watson2025_scaled.py   # Main simulation (NEST)
├── replay_plot_from_hdf5.py                    # Post-hoc plotting (no NEST)
├── tiny.py                                     # Utility library
├── requirements.txt                            # Core dependencies
├── requirements-dev.txt                        # Dev tools (optional)
├── mem_cons_plan.md                            # 5-phase consolidation plan
├── README.md                                   # Full documentation
└── replay_output_*/                            # Simulation outputs (HDF5)
```

---

## File I/O & Analysis Workflow

### On HPC Cluster
```bash
# 1. Run simulation (writes HDF5 to shared filesystem)
mpirun -n 64 python bidirectional_replay_watson2025_scaled.py \
  --scale 12pct --out-hdf5 replay_output/replay_12pct.h5

# 2. Download HDF5 to local machine (or access via NFS)
rsync -av user@mn5:/path/to/replay_output/ ./local_output/
```

### On Local Machine
```bash
# No NEST required; only matplotlib, h5py, numpy, scipy
python replay_plot_from_hdf5.py \
  --in local_output/replay_12pct.h5 \
  --save-prefix figures/12pct
```

---

## Dependency Troubleshooting

### "ModuleNotFoundError: No module named 'nest'"
- Install NEST: `pip install nest-simulator>=3.9.0`
- Or load module: `module load nest`
- Verify: `python -c "import nest; print(nest.__version__)"`

### "ModuleNotFoundError: No module named 'mpi4py'"
- Ensure MPI module is loaded BEFORE installing mpi4py
- On MareNostrum5: `module load intelmpi && pip install mpi4py`

### "h5py not found"
- `pip install h5py>=3.0.0`
- On HPC: `module load hdf5` and ensure it matches pip install

### scipy version warnings
- Install latest: `pip install --upgrade scipy>=1.7.0`
- Required for Spearman correlation in replay quality metrics

---

## Biological Targets & Validation

This model implements the Watson et al. 2025 circuit with the following constraints:

- **CA3 populations** (SUP/DEEP): Asymmetric forward/backward weights
- **Synaptic Tagging & Capture (STC)**: L-LTP appears at SWR event ~4 (Frey & Morris 1997)
- **Replay quality (Spearman ρ)**:
  - Forward replay: ρ > +0.5 (groups 0→N activate sequentially)
  - Reverse replay: ρ < −0.5 (groups N→0 activate sequentially)
- **Falsification (Phase 5)**: PRP_threshold=999 blocks L-LTP but preserves replay quality

---

## Key References

- Watson et al. (2025) — Hippocampal circuit architecture
- Frey & Morris (1997) — L-LTP temporal dynamics
- NEST 3.9.0 documentation — https://nest-simulator.readthedocs.io/

---

## Support & Issues

For bugs or questions:
1. Check GitHub issues: https://github.com/max-talanov/tinyHippo/issues
2. Verify all dependencies: `pip list | grep -E "nest|numpy|h5py|scipy"`
3. Run diagnostic: `python -c "import nest, numpy, h5py, scipy; print('All OK')"`
