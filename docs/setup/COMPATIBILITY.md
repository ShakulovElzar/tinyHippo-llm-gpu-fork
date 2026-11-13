# tinyHippo Dependency Compatibility Matrix

## Minimum Supported Versions

| Package | Version | Notes |
|---------|---------|-------|
| **Python** | 3.8+ | 3.9–3.11 tested on MareNostrum5 |
| **NEST** | 3.9.0+ | Required for STDP, multimeter fixes |
| **numpy** | 1.21+ | ≥2.0 has deprecation warnings; stay <2.0 |
| **scipy** | 1.7+ | For Spearman correlation (replay quality) |
| **matplotlib** | 3.4+ | For figure generation |
| **h5py** | 3.0+ | For HDF5 spike/weight serialization |
| **mpi4py** | 3.0+ | Optional; only for MPI HPC runs |

## Tested Configurations

### Local Development (macOS/Ubuntu/WSL2)

```
Python 3.9.11
  nest-simulator 3.9.0 (via pip, OpenMP-only)
  numpy 1.23.5
  scipy 1.9.3
  matplotlib 3.6.0
  h5py 3.7.0
```

**Install:** `pip install -r requirements.txt`

**Test:** `python bidirectional_replay_watson2025_scaled.py --scale 1pct`

---

### MareNostrum5 (BSC, Barcelona)

```
module load gcc/11.2.0
module load python/3.9.11
module load nest/3.9.0
module load hdf5/1.12.1-parallel
module load intelmpi/2021.4.0

pip install -r requirements.txt
pip install mpi4py==3.0.3
```

**Test (serial):** `python bidirectional_replay_watson2025_scaled.py --scale 1pct`

**Test (MPI):** `mpirun -n 4 python bidirectional_replay_watson2025_scaled.py --scale 12pct`

---

### Other HPC Clusters (Tier-0 European)

**Assumptions:**
- NEST ≥3.9.0 available as module or pre-installed
- HDF5 with parallel support (libhdf5-mpi)
- Intel MPI or OpenMPI available
- Python 3.8–3.11

**Adapt the load sequence:**
```bash
module load nest  # or nest/3.9.0
module load hdf5  # or hdf5/mpi
module load mpi   # Intel or OpenMPI
python -m pip install --user -r requirements.txt
```

---

## Known Issues & Workarounds

### Issue: numpy 2.0+ DeprecationWarning with NodeCollection

**Symptom:** Warning on np.array(NodeCollection)

**Cause:** NEST 3.9 uses list.tolist() before numpy conversion

**Fix:** Already handled in `replay_scaled.py` via explicit list conversion. If upgrading NEST >3.9, verify `_to_nc()` compatibility.

**Workaround:**
```bash
pip install 'numpy<2.0'
```

---

### Issue: mpi4py install fails on HPC

**Symptom:** `error: Command 'mpicc' not found`

**Cause:** MPI module not loaded before install

**Fix:**
```bash
module load intelmpi  # or your HPC's MPI
pip install mpi4py
```

---

### Issue: NEST not found / wrong version

**Symptom:** `ModuleNotFoundError: No module named 'nest'`

**Cause:** NEST not installed or installed to wrong Python environment

**Fix:**
```bash
# Check current Python
which python
python -c "import sys; print(sys.executable)"

# Load NEST module (HPC) OR install locally
module load nest  # or:
pip install nest-simulator==3.9.0
```

---

### Issue: h5py MPI build mismatch

**Symptom:** HDF5 write fails with MPI parallel run

**Cause:** h5py not built against parallel HDF5 library

**Fix:**
```bash
# Uninstall pip version
pip uninstall h5py -y

# Reinstall with local HDF5
module load hdf5  # parallel build
pip install --no-binary h5py h5py
```

---

## Version Pin Rationale

### nest-simulator ≥3.9.0
- GetConnections with dual filters hangs in older versions
- stdp_synapse weight updates fixed in 3.9
- Python 3.9+ native dict ordering required

### numpy <2.0
- numpy 2.0 changed float type hierarchy
- NEST bindings not yet updated
- Stay on 1.x until nest-simulator 3.10+

### scipy ≥1.7.0
- spearmanr() API stable; older versions have different return format
- Required for Spearman rho replay quality metric

### matplotlib ≥3.4.0
- Uses CSS-style color names (e.g., "steelblue") reliably
- Agg backend headless rendering required for HPC

---

## Development (Optional)

If you want to contribute to tinyHippo:

```bash
pip install -r requirements.txt -r requirements-dev.txt

# Run tests
pytest tests/

# Check code style
black --check .
flake8 .

# Build docs
sphinx-build -b html docs/ docs/_build/
```

---

## Quick Diagnostic Script

Save as `check_env.py`:

```python
#!/usr/bin/env python3
import sys
print(f"Python {sys.version}")

for pkg, expected_min in [
    ("nest", "3.9.0"),
    ("numpy", "1.21.0"),
    ("scipy", "1.7.0"),
    ("matplotlib", "3.4.0"),
    ("h5py", "3.0.0"),
]:
    try:
        mod = __import__(pkg)
        v = getattr(mod, "__version__", "unknown")
        print(f"✓ {pkg:15s} {v}")
    except ImportError:
        print(f"✗ {pkg:15s} NOT INSTALLED")

try:
    from mpi4py import MPI
    rank = MPI.COMM_WORLD.Get_rank()
    size = MPI.COMM_WORLD.Get_size()
    print(f"✓ mpi4py          OK (rank {rank}/{size})")
except ImportError:
    print(f"  mpi4py          not installed (optional)")
```

Run it:
```bash
python check_env.py
```

Expected output:
```
Python 3.9.11 (default, Apr  5 2023, 14:15:10)
✓ nest             3.9.0
✓ numpy            1.23.5
✓ scipy            1.9.3
✓ matplotlib       3.6.0
✓ h5py             3.7.0
  mpi4py           not installed (optional)
```

---

## Further Reading

- NEST 3.9 docs: https://nest-simulator.readthedocs.io/
- Memory consolidation plan: https://github.com/max-talanov/tinyHippo/blob/main/mem_cons_plan.md
- Watson et al. 2025 circuit: Check project README
