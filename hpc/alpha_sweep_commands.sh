# Phase 4 alpha-sweep — robustness check for the homeostasis result
# =================================================================
#
# Baseline (already run, reference):
#   alpha = 0.75   ->   rho_fwd = +0.04   L-LTP intact at 98%
#
# Two new runs to bracket the parameter:
#   alpha = 0.50   ->   stronger downscaling (expect even lower rho_fwd)
#   alpha = 0.90   ->   milder downscaling (expect intermediate rho_fwd)
#
# All other parameters fixed at Run A values:
#   SCALE=25, N_SWR=14, PRP_THRESHOLD=3.5
#
# Wall time:  Phase 4 hook adds ~30-60 min on top of ~4.3h sim, so
#             8 hours is safe.  Drop --time= back to 8:00:00 in run.sh
#             before submitting (or just leave 20:00:00 — won't hurt).

# ---- alpha = 0.50  (aggressive)  ---------------------------------
sbatch -A uab100 -q acc_resb \
  --export=ALL,SCALE=25,N_SWR=14,PRP_THRESHOLD=3.5,HOMEOSTASIS=1,HOMEO_ALPHA=0.50 \
  hpc/run.sh

# ---- alpha = 0.90  (mild)  ---------------------------------------
sbatch -A uab100 -q acc_resb \
  --export=ALL,SCALE=25,N_SWR=14,PRP_THRESHOLD=3.5,HOMEOSTASIS=1,HOMEO_ALPHA=0.90 \
  hpc/run.sh

# ---- both at once  -----------------------------------------------
for A in 0.50 0.90; do
  sbatch -A uab100 -q acc_resb \
    --export=ALL,SCALE=25,N_SWR=14,PRP_THRESHOLD=3.5,HOMEOSTASIS=1,HOMEO_ALPHA=${A} \
    hpc/run.sh
done

# Output filenames will collide!  Each run will produce
#   results/replay_25pct_stc_lv_mpfc_ph4.h5
# Either:
#   (a) rename the existing alpha=0.75 file before submitting,
#       e.g.  mv results/replay_25pct_stc_lv_mpfc_ph4.h5 \
#                results/replay_25pct_stc_lv_mpfc_ph4_a075.h5
#   (b) OR add alpha tag to PHASE_TAG in run.sh:
#       in the PHASE_TAG block, add:
#         [ "$HOMEOSTASIS" = "1" ] && PHASE_TAG="${PHASE_TAG}_ph4_a${HOMEO_ALPHA//./}"
#       which gives _ph4_a050, _ph4_a075, _ph4_a090 — no collisions.
