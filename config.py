"""
Central configuration for the Fork ET Detection Pipeline.

All paths, thresholds, column mappings, and frequency parameters live here
so that every other module imports from a single source of truth.
"""

import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_BASE = r"C:\Users\maor1\Desktop\fork\New Data"
DATA_ROOT = os.path.join(_DATA_BASE, "משתתפים")
CRF_PATH = os.path.join(_DATA_BASE, "HIT Study CRF - No personal Data.xlsx")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output", "figures")

# ---------------------------------------------------------------------------
# CRF Excel — sheet names
# ---------------------------------------------------------------------------
CRF_SHEET_ET = "ET Rater 1-F2F Dr.Lassman"
CRF_SHEET_CONTROL = "Control Rater 1-F2F Dr.Lassman"

# ---------------------------------------------------------------------------
# CRF Excel — column indices (0-based)
# ---------------------------------------------------------------------------
CRF_COL_SUBJECT = 1
CRF_COL_GENDER = 2
CRF_COL_AGE = 3
CRF_COL_TREMOR_HAND = 7
CRF_COL_RT_FORK_SCOOP = 53
CRF_COL_LF_FORK_SCOOP = 54
CRF_COL_RT_FORK_STAB = 55
CRF_COL_LF_FORK_STAB = 56
CRF_COL_SUBTOTAL_B_EXT = 62

# ---------------------------------------------------------------------------
# Fork hand mapping
# ---------------------------------------------------------------------------
FORK_HAND_MAP = {"Fork1": "Right", "Fork2": "Left"}
FORK_DEFAULT_HAND = "Right"
INCLUDE_AMBIGUOUS_FORK = True

# ---------------------------------------------------------------------------
# IMU / signal parameters
# ---------------------------------------------------------------------------
FS = 100
LOWPASS_HZ = 20.0
HIGHPASS_HZ = 0.5
BUTTER_ORDER = 4

# ---------------------------------------------------------------------------
# Activity detection
# ---------------------------------------------------------------------------
ACTIVITY_THRESHOLD = 0.25
GAP_FILL_SEC = 2.0
MIN_SEGMENT_SEC = 3.0

# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------
ET_FREQ_LOW = 4.0
ET_FREQ_HIGH = 12.0
WAVELET_NAME = "morl"
WAVELET_SCALES_HZ = (4, 5, 6, 7, 8, 9, 10, 11, 12)

# ---------------------------------------------------------------------------
# Feature selection
# ---------------------------------------------------------------------------
FEATURE_SELECTION_METHOD = "rfe"   # "rfe", "rf_importance", or "select_k_best"
TOP_K_FEATURES = 25
RF_IMPORTANCE_THRESHOLD = 0.01

# ---------------------------------------------------------------------------
# Data augmentation
# ---------------------------------------------------------------------------
USE_AUGMENTATION = False #Took too long and can be a reason for overfitting
NOISE_SCALE = 0.05
MIXUP_ALPHA = 0.01

# ---------------------------------------------------------------------------
# ML
# ---------------------------------------------------------------------------
CV_FOLDS = 5
TEST_SIZE = 0.2
RANDOM_STATE = 42
USE_LOSO = True
TUNE_HYPERPARAMS = False #Took too long and can be a reason for overfitting
USE_STACKING = False #Took too long and can be a reason for overfitting
PER_SEGMENT = True
TARGET_SPECIFICITY = 0.80

# ---------------------------------------------------------------------------
# Stage A: Robust preprocessing
# ---------------------------------------------------------------------------
OUTLIER_PERCENTILE_LOW = 0.5
OUTLIER_PERCENTILE_HIGH = 99.5
SPIKE_DERIV_PERCENTILE = 99.5
SMOOTH_MEDIAN_N = 5
SMOOTH_SG_WINDOW = 11
SMOOTH_SG_POLY = 3
NARROW_BPF_LOW = 2.0
NARROW_BPF_HIGH = 15.0

# ---------------------------------------------------------------------------
# Stage B: Enhanced cycle segmentation (Cup combined criterion)
# ---------------------------------------------------------------------------
TAU_1 = 1.5                   # combined activity metric threshold (init from Cup)
TAU_2 = 0.1                   # gyro-above-rest threshold in rad/s
P_ACTIVE = 0.7                # min active ratio in window to open a segment
P_INACTIVE = 0.7              # min inactive ratio in window to close a segment
ACTIVITY_WINDOW_SEC = 0.5     # sliding window size for start/end detection
INTRA_CYCLE_GAP_FILL_SEC = 0.3  # shorter gap fill vs old 2.0 s
MAX_SEGMENT_SEC = 15.0        # fused-cycle guard
FRAGMENT_JERK_RATIO = 1.5     # peak/mean jerk ratio below which → fragment
FRAGMENT_TILT_MIN = 0.2       # minimum acc_y/z range (g) required for a real cycle

# ---------------------------------------------------------------------------
# Stage C: Handedness classifier
# ---------------------------------------------------------------------------
HANDEDNESS_MIN_ACCURACY = 0.90

# ---------------------------------------------------------------------------
# Stage D: Rule-based movement classifier
# Rules are applied in order: fragment → scoop → stab → other.
# Tune these thresholds by inspecting the cluster_inspection.pdf.
# ---------------------------------------------------------------------------
RULE_FRAGMENT_MAX_DUR       = 2.0   # s  — cycle shorter than this AND weak → fragment
RULE_FRAGMENT_MAX_JERK_RATIO = 2.5  # —   peak/mean jerk below this (weak motion)
RULE_SCOOP_MIN_ACC_Y_RANGE  = 0.3   # g  — minimum lateral tilt to qualify as scoop
RULE_SCOOP_TILT_RATIO       = 0.8   # —   acc_y_range must exceed acc_z_range × this
RULE_SCOOP_GYRO_RATIO       = 1.0   # —   gy_std must exceed gx_std × this (roll > pitch)
RULE_SCOOP_PEAK_JERK_MIN    = 0.25  # —   peak jerk must fall after this fraction of cycle
RULE_SCOOP_PEAK_JERK_MAX    = 0.75  # —   peak jerk must fall before this fraction of cycle
RULE_STAB_MIN_ACC_Z_RANGE   = 0.3   # g  — minimum vertical range to qualify as stab
RULE_STAB_VERT_RATIO        = 0.8   # —   acc_z_range must exceed acc_y_range × this
RULE_STAB_PEAK_JERK_MAX     = 0.55  # —   stab peak must occur in the first 55 % of cycle

# ---------------------------------------------------------------------------
# Stage E: Bucketed regression
# ---------------------------------------------------------------------------
MIN_BUCKET_PATIENTS = 5
RFE_MIN_FEATURES = 5

# ---------------------------------------------------------------------------
# Stage F: Severity classification
# local_score  = mean TETRAS fork item (0–4 scale per cell, averaged)
# global_score = Subtotal B Extended (sum of multiple upper-limb TETRAS items)
# ---------------------------------------------------------------------------
SEVERITY_LOCAL_BINS   = [0.0, 1.5, 3.0, 4.5]
SEVERITY_LOCAL_LABELS = ["Mild", "Moderate", "Severe"]
SEVERITY_GLOBAL_BINS   = [0.0, 8.0, 20.0, 100.0]
SEVERITY_GLOBAL_LABELS = ["Mild", "Moderate", "Severe"]

# Binary severity grouping per advisor feedback:
# Raw per-item TETRAS cell values 0–1 → "Low", 2–4 → "High"
# Applied to raw per-cycle CRF cells (rt_scoop, lf_scoop, rt_stab, lf_stab),
# not to the averaged local_score.
SEVERITY_BINARY_THRESHOLD = 2      # raw TETRAS cell value: < this → "Low", >= this → "High"
SEVERITY_BINARY_LABELS    = ["Low", "High"]   # Low = {0,1}, High = {2,3,4}
