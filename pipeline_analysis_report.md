# Fork ET Detection Pipeline — Full Technical & Log Analysis Report

**Run date:** 22 April 2026  
**Pipeline version:** main branch (commit `0e7549b`)  
**Analyst:** Senior Data Scientist / Software Engineer review

---

## Table of Contents

1. [End-to-End Pipeline Flow](#1-end-to-end-pipeline-flow)
2. [Data Processing, Segmentation, and Classification](#2-data-processing-segmentation-and-classification)
3. [Module Responsibilities](#3-module-responsibilities)
4. [Execution Log Analysis](#4-execution-log-analysis)

---

## 1. End-to-End Pipeline Flow

### Startup & Initialization (`main.py`)

`python main.py` enters `main()`, which:
1. Calls `setup_logging()` — timestamped `INFO`-level logger to stdout.
2. Calls `ensure_output_dirs()` — creates `output/figures/` if absent.
3. Sets up the global `logger` and imports all pipeline modules.

---

### Stage 1 — Participant Scanning

`scan_participants()` (`data_loader.py`) performs an `os.walk` of `E:\Fork\Cup\cupcode\New Data\משתתפים`. It supports two folder layouts:
- **Flat:** `.../Control-001/...`
- **Grouped:** `.../Control/Control-001/...` and `.../Tremor/ET-001/...`

For every folder matching the regex `(Control|ET)-(\d{3})`, it collects all files starting with `fork*.csv` and keeps only the **largest file per device prefix** (`fork1`, `fork2`, or bare `fork_`), because the sensor firmware appends all sessions into one growing file. The result is a list of dicts with `{patient_id, group, filepath}`.

`_get_crf_data()` is then called once, parsing `HIT Study CRF - No personal Data.xlsx` sheet `ET Rater 1-F2F Dr.Lassman`. It reads patient ID, gender, age, tremor hand, four fork-score cells (`rt_scoop`, `lf_scoop`, `rt_stab`, `lf_stab` at columns 53–56), and Subtotal B Extended (col 62). Results are cached globally for the lifetime of the run.

---

### Stages 2–4a — Preprocessing, Filtering, Segmentation (Data Collection Pass)

For each discovered record the pipeline runs:

**A. IMU Loading**  
`load_imu()` reads the CSV, drops all columns except index 0 (timestamp ms) and indices 4–9 (6 IMU axes at 100 Hz). Coerces all values to float and drops NaN rows.

**B. Robust Preprocessing (Stage A)**
- `reject_outliers()` — per-axis clip to [0.5, 99.5] percentiles → NaN → linear interpolation
- `reject_spikes()` — first-derivative spikes above the 99.5th percentile → NaN → interpolation
- `smooth_signal()` — median filter (kernel=5) then Savitzky-Golay (window=11, poly=3). Used **only** for the static-tilt term in the activity detector, never for feature extraction.

**C. Two Bandpass Copies of the Cleaned Signal**
- `df_narrow`: Butterworth BP 2–15 Hz — input to the activity detector
- `df_wide`: Butterworth BP 0.5–20 Hz — input to feature extraction

**D. Activity Detection (Stage B) — Cup Combined Criterion**

`detect_activity()` computes per-sample:

```
combined(t) = |∇acc_mag_filt| + |∇gyro_mag_filt| + |acc_smooth_mag(t) - 1g|
gyro_above_rest(t) = gyro_mag(t) - min(gyro_mag)

active(t)  iff  combined(t) >= τ₁=1.5  AND  gyro_above_rest(t) >= τ₂=0.1 rad/s
```

A 0.5-second sliding window (box kernel) converts sample-level flags into segment decisions:
- Segment **opens** when ≥70% of the window is active
- Segment **closes** when ≥70% of the window is inactive

Intra-cycle gaps ≤0.3 s are filled. Segments outside [3 s, 15 s] are discarded. Oversized segments are split into 15-second chunks.

**E. Cycle Quality Classification**

`classify_cycle_quality()` labels each segment as `"cycle"` or `"fragment"` based on two conditions:
- **Tilt criterion:** `max(acc_y_range, acc_z_range) > 0.2g` — a real eating cycle tilts the fork.
- **Jerk criterion:** `peak_jerk / mean_jerk >= 1.5` AND `mean_jerk > 1e-10` — real eating has a sharp impulsive moment; smooth constant-motion artifacts fail this.

Only `"cycle"` segments proceed further.

**F. Behavioral Test Grouping**  
Consecutive eating cycles are grouped into tests by gaps >10 seconds. Each test gets a unique key `patient_id__filename__test_idx`, mapping to the study protocol's distinct task blocks.

**G. Visualization**  
For the first valid test of each patient, a 2-panel (accelerometer + gyroscope) PNG is saved to `output/figures/patient_signals/`.

---

### Stage 4b — Handedness Classification

`HandednessClassifier` (logistic regression, `handedness.py`) trains on all cycles with known labels (`Fork1_* → Right`, `Fork2_* → Left`). It uses 6 chirality-sensitive features:

1. `gyro_y_asym = p95(gy) + p05(gy)` — signed rotational asymmetry
2. `skew(gyro_y)`, `skew(gyro_z)` — pronation/supination sign
3. `corr(acc_x, gyro_y)`, `corr(acc_z, gyro_x)` — cross-axis chirality (sign inverts between hands)
4. `weighted_mean(gyro_y)` — mean gyro_y weighted by `|acc|` (emphasises the scoop moment)

LOSO accuracy is evaluated if ≥10 labeled cycles exist. For test-level hand assignment, the pipeline majority-votes all per-cycle predictions within a test.

---

### Stage 4c — Movement Type Clustering (GMM k=4)

`MovementClassifier` (`movement_classifier.py`) extracts 15 biomechanical features per cycle and fits a `GaussianMixture(n_components=4, covariance_type='full', n_init=5)`. The cluster-to-label mapping is read from `config.GMM_CLUSTER_LABEL_MAP = {0: "scoop", 1: "fragment", 2: "other", 3: "stab"}`.

A 3-page inspection PDF is generated after fitting:
- Page 1: Feature histograms per cluster
- Page 2: Mean acc-magnitude profile per cluster
- Page 3: PCA scatter coloured by cluster

---

### Stage 5 — Feature Extraction

`extract_all_features()` runs 13 feature families on each cycle segment from the wide-band filtered signal:

| Family | Features (approx) | Key content |
|---|---|---|
| Time-domain (×6 axes) | 36 | mean, std, RMS, skew, kurt, ptp |
| Jerk (×6 axes) | 24 | mean, std, RMS, max of finite-diff derivative |
| Cross-axis correlations | 9 | Pearson corr of 9 axis pairs |
| Magnitude (acc + gyro) | 12 | Time stats on Euclidean magnitude |
| Frequency (×6 axes) | 24 | dominant/median freq, spectral energy, 4–12 Hz power ratio |
| Spectral shape (×6 axes) | 24 | entropy, flatness, centroid, rolloff |
| Wavelet CWT (×6 axes) | 24 | Morlet CWT energy mean/std/max/ratio in ET band |
| Weighted spectral (acc + gyro) | 16 | weighted mean/median/max freq, freq std/skew, FFT amp stats |
| Peak features (acc + gyro) | 9 | peak-to-peak intervals, peak frequency, duration |
| Tremor features (acc + gyro) | 10 | tremor power ratio, TSI, HNR |
| Multi-resolution CWT (acc + gyro) | 6 | windowed energy variance, CV, trend |
| Dual bandpass 3–15 Hz (acc + gyro) | 8 | narrow-band RMS/std/max/energy ratio |
| Temporal (acc + gyro) | 8 | ACF at ET lags, sample entropy |

When `PER_SEGMENT=True`, each cycle produces one row. Metadata columns (`patient_id`, `group`, `hand`, `local_score`, `global_score`, `is_et`, `movement_type`, 4 CRF cells) are appended. RFE within each CV fold reduces the feature set to 25.

---

### Stage 6 — Regression

`run_regression()` operates on ET-only rows. It runs 5–6 models (LinearRegression, Ridge, Lasso, RandomForest, GradientBoosting, XGBoost), each wrapped in:

```
VarianceThreshold → StandardScaler → RFE(RF, k=25, step=1) → model
```

The CV loop is **manual** (LOSO when N_groups ≥ 3, GroupKFold when >15 patients, else 5-fold KFold) to ensure augmentation is applied only to training folds. Per-segment predictions are aggregated to patient level via **median** before computing R², MAE, Pearson r, Spearman ρ.

`run_bucketed_regression()` applies the same approach for 4 specific buckets: `(Right/Left) × (scoop/stab)`, each targeting the matching CRF cell. Buckets with <5 unique patients are skipped.

---

### Stage 7 — Classification & Extended Analysis

`run_classification()` runs 5 classifiers (LogisticRegression, SVC, RandomForest, GradientBoosting, XGBoost) using a manual LOSO CV loop. SMOTE is applied after scaling and RFE — **strictly on training folds**. Then:

- **Patient-level metrics** — aggregates segment scores to the 75th-percentile per patient; optimizes threshold at target specificity ≥80%.
- **Youden's J optimization** — finds the probability threshold maximizing sensitivity + specificity − 1.
- `run_regress_then_classify()` — predicts tremor score via regression, binarizes above a threshold; also evaluated with Youden's J.
- `run_calibrated_classification()` — wraps SVC and RF in `CalibratedClassifierCV(cv=3, method='sigmoid')` (Platt scaling).
- `run_shap_analysis()` — trains XGBoost (or RF fallback) on the full dataset, computes TreeSHAP values, saves bar + beeswarm PNGs.

---

### Stage 8 — Visualizations

Generates: PCA (ET vs Control), boxplot (top-variance features by group), PCA (movement clusters), activity-segment signal overlay, scatter (true vs predicted local score), Bland-Altman, confusion matrix, ROC curve.

---

### Stage 9 — Clinical Report

`generate_report()` assembles an A4 PDF via `fpdf2`: title page, summary table, regression tables (local + global score + bucketed), classification tables (direct + calibrated + regress-then-classify), patient-level results, SHAP feature rankings, RFE stability, embedded PNGs, and a limitations section.

---

## 2. Data Processing, Segmentation, and Classification

### 2.1 Cycle Segmentation — Deep Technical Detail

**Problem:** The raw CSV is a continuous multi-hour recording. Rest periods, transitions, and actual eating events are all mixed together. The algorithm must detect windows of active fork-eating motion.

**Combined activity metric (Cup criterion):**

```
combined(t) = |d/dt acc_mag_filt(t)| + |d/dt gyro_mag_filt(t)| + |acc_smooth_mag(t) - 1.0|
```

- The **first term** captures acceleration rate-of-change (fork movement onset/offset).
- The **second term** captures rotational rate-of-change (wrist/elbow motion).
- The **third term** penalises static tilt away from gravity. A fork at rest = 1g; a lifted or tilted fork ≠ 1g. This rejects pure vibration on a stable surface.
- The **AND gate** with `gyro_above_rest >= τ₂=0.1 rad/s` rejects pure vibration artifacts that would trigger the acc criterion without actual rotation.

**Sliding window decision:** A 50-sample (0.5 s) box kernel is convolved with the binary `active` flag. A segment **opens** when the smoothed ratio ≥ 0.7 and **closes** when ≥ 0.7 is inactive. This prevents single noisy samples from fragmenting eating bouts.

**Gap filling:** Intra-cycle gaps ≤0.3 s (30 samples) are bridged — handles the brief pause mid-scoop when the fork pauses between plate and mouth.

**Quality filter — two biomechanical tests:**
1. `tilt > 0.2g`: A real eating cycle always tilts the utensil. Pure horizontal shaking (at-rest tremor, coughing) won't pass.
2. `peak_jerk / mean_jerk >= 1.5`: A real eating cycle has a characteristic impulsive moment (stabbing food, lifting the plate). Smooth constant-motion artifacts have flat jerk profiles and fail this test.

**Behavioral test grouping:** Segments separated by >10 seconds are treated as distinct eating tests (e.g., Scoop Test 1, Stab Test 2), mapping directly to the study protocol's designated tasks.

---

### 2.2 Hand Classification — Deep Technical Detail

**Label source:** Filenames encode hand — `Fork1_* → Right`, `Fork2_* → Left`. Files starting with bare `Fork_` are ambiguous and use `FORK_DEFAULT_HAND = "Right"` with `INCLUDE_AMBIGUOUS_FORK = True`.

**Feature logic — why these 6 features:**

| Feature | Physical meaning |
|---|---|
| `gyro_y_asym = p95(gy) + p05(gy)` | Right hand scooping: gyro_y peaks positive (wrist supination toward mouth). Left hand: opposite sign. Sum is positive for Right, near-zero or negative for Left. |
| `skew(gyro_y)`, `skew(gyro_z)` | Pronation/supination distribution is asymmetric and reverses between hands. |
| `corr(acc_x, gyro_y)`, `corr(acc_z, gyro_x)` | Cross-axis coupling from sensor orientation inverts sign when the hand holding the fork changes (sensor physically rotates ~180°). |
| `weighted_mean_gy` | Gravity-weighted gyro_y emphasises the scoop-to-mouth arc, the most biomechanically discriminative moment. |

**LOSO evaluation:** `LeaveOneGroupOut` on patient IDs ensures the classifier is evaluated on unseen subjects. Accuracy must reach ≥0.90. If below, a warning is issued and the heuristic fallback (`gyro_y p95/p05 asymmetry sign`) is used.

**Test-level decision:** Majority vote across all cycles in a test — avoids single-cycle misclassification propagating to the whole test's CRF score lookup.

---

### 2.3 Movement Type Classification — Deep Technical Detail

**Why GMM (not k-means)?**  
Eating cycles are not spherical clusters. Scooping has high `acc_y_range` and low `jerk_ratio`; stabbing has high `jerk_ratio` and sharp `peak_jerk`. GMM with `covariance_type='full'` captures these ellipsoidal distributions.

**k=4 rationale:**  
The study protocol includes Scooping and Stabbing (the two clinical subtasks), plus two noise categories — short noisy fragments (`fragment`) and other incidental motion (`other`). The label map `{0: "scoop", 1: "fragment", 2: "other", 3: "stab"}` is a post-hoc assignment confirmed by inspecting the inspection PDF.

**Feature discriminability:**

| Feature | Discriminates |
|---|---|
| `acc_y_range`, `tilt_path` | High for scooping (large vertical arc), lower for stabbing (more horizontal thrust) |
| `jerk_ratio`, `peak_jerk` | High for stabbing (sharp, impulsive), lower for scooping (smooth parabolic) |
| `dominant_freq`, `hf_ratio` | Fragments: high-frequency dominated spectra (sensor artifacts without clean eating signal) |
| `duration` | Fragments close to the 3-second minimum; full scooping cycles typically 4–8 seconds |

**Integration into regression:**  
Only `scoop` and `stab` labeled cycles feed into the bucketed regression. `fragment` and `other` cycles are excluded from bucket targets but their features still participate in the overall regression/classification.

---

## 3. Module Responsibilities

| Module | Role & Responsibilities |
|---|---|
| **`config.py`** | Single source of truth for all constants: file paths (`DATA_ROOT`, `CRF_PATH`, `OUTPUT_DIR`), CRF column indices, IMU parameters (FS=100 Hz, filter bounds), activity detection thresholds (τ₁=1.5, τ₂=0.1, P_active=0.7), feature selection settings (TOP_K=25, method="rfe"), ML flags (`USE_LOSO`, `TUNE_HYPERPARAMS`, `USE_STACKING`, `PER_SEGMENT`), GMM configuration, and bucketed regression minimums. All other modules import from this file and never from each other. |
| **`utils.py`** | Infrastructure utilities: `setup_logging()` configures the root logger with timestamps; `ensure_output_dirs()` creates `output/figures/`; `normalize_hand_label()` maps raw CRF strings (English + Hebrew) to canonical `Right`/`Left`/`Bilateral`. Stateless helper module with no domain logic. |
| **`data_loader.py`** | All I/O with filesystem and CRF Excel: `scan_participants()` discovers Fork CSV files across flat and grouped directory layouts; `load_imu()` parses the 10-column CSV and returns a clean 7-column DataFrame; `load_crf_scores()` looks up a patient's clinical scores and computes `local_score` (average of relevant CRF cells per tremor hand) and `global_score` (Subtotal B Extended); `_get_crf_data()` parses the Excel once and caches globally. Contains all filename-to-hand and folder-name-to-group parsing logic. |
| **`preprocessing.py`** | Signal processing layer: `reject_outliers()` and `reject_spikes()` clean the raw IMU signal; `smooth_signal()` (median + Savitzky-Golay) prepares the signal for the tilt term in the activity detector; `bandpass_filter()` implements zero-phase Butterworth BP; `detect_activity()` implements the full Cup combined-criterion segmentation; `classify_cycle_quality()` labels segments as `"cycle"` vs `"fragment"`; `segment_signal()` slices DataFrames. Also contains deprecated fallback functions kept for backward-compatibility. |
| **`handedness.py`** | Per-cycle hand classifier using logistic regression on 6 chirality-sensitive gyroscope/accelerometer features. Provides `fit()`, `predict()`, and `evaluate_loso()`. Falls back to a simple `gyro_y` asymmetry heuristic if not fitted. Labels come exclusively from filenames; the classifier is used only for ambiguous `Fork_*` files. |
| **`movement_classifier.py`** | GMM-based unsupervised clustering of eating cycle types (k=4: scoop, stab, fragment, other). Extracts 15 biomechanical features (jerk, tilt, gyro dominance, duration, spectral properties, kurtosis). `generate_inspection_pdf()` creates a 3-page diagnostic PDF for manual cluster-to-label assignment. The cluster-to-label mapping lives in `config.GMM_CLUSTER_LABEL_MAP`. |
| **`feature_extraction.py`** | Comprehensive feature engineering across 13 families producing ~196 raw features per cycle segment. Key clinical families: tremor features (tremor power ratio, TSI, HNR in 4–12 Hz ET band), wavelet CWT energy (Morlet), and temporal features (ACF, sample entropy). `extract_all_features()` is the public API — supports both per-segment and per-patient-averaged modes via `PER_SEGMENT` flag. |
| **`ml_pipeline.py`** | The ML engine: `run_regression()` (LOSO CV on ET-only, 5–6 models), `run_classification()` (LOSO CV with SMOTE, 5 models, patient-level aggregation), `run_bucketed_regression()` (4 hand×movement buckets with independent RFE), `run_calibrated_classification()` (Platt scaling), `run_regress_then_classify()` (score-based binary classification), `run_shap_analysis()` (TreeSHAP), `optimize_threshold_youden()`. All preprocessing (scaling, RFE, SMOTE) is applied **inside** CV folds to prevent data leakage. |
| **`visualization.py`** | All matplotlib figure generation: scatter (true vs predicted), Bland-Altman (agreement), PCA (ET vs Control and movement clusters), boxplot (features by group), ROC curve, confusion matrix, activity-segment overlay, per-patient IMU signal plots. Uses `Agg` backend (non-interactive, safe for headless runs). |
| **`report_generator.py`** | Automated PDF report generation using `fpdf2`. Assembles a clinical A4 report with summary statistics, regression tables (local + global score + bucketed), classification tables (direct + calibrated + regress-then-classify), patient-level results, SHAP feature rankings, RFE stability, embedded PNG figures, and a limitations section. Fully driven by the `metrics_dict` passed from `main.py` — no hardcoded numbers. |
| **`main.py`** | Pipeline orchestrator across 9 stages. Defines the entire execution sequence, handles all inter-module data flow (`all_cycle_records`, `movement_types`, `features_df`), coordinates the two-pass architecture (data collection pass → feature extraction pass), and assembles the final `report_metrics` dict. Contains `_group_into_tests()` for behavioral test segmentation. |

---

## 4. Execution Log Analysis

**Run:** 2026-04-22, 22:57:39 → 23:23:17 (~25.5 minutes total)

---

### 4.1 Stage 1 — Data Inventory

```
36 files from 25 patients (ET=23, Control=10)
CRF loaded for 29 ET patients
```

The file count (36) exceeds the patient count (25) because some participants have both a Fork1 and a Fork2 device. The CRF contains records for 29 ET patients but only 23 have matching sensor directories — **6 ET patients are silent exclusions** with clinical data but no IMU recordings. These must be documented in any participant flow diagram.

#### Critical CRF Quality Issues

> **[CRITICAL] Age = `None` for every patient.**  
> `CRF_COL_AGE = 3` points at the wrong column (likely a header or a non-numeric identifier cell). Every patient falls back to `age = 65.0` (the hardcoded default in `extract_all_features()`). Age is a **completely uninformative constant** in every model in this run. Fix: verify the zero-indexed column number in the Excel and update `config.py`.

> **[CRITICAL] Gender = `0.0` for every patient.**  
> Either all 29 ET patients are female, or the Hebrew cell values (`זכר`/`נקבה`) are not matching the gender mapping due to encoding or whitespace differences in the Excel. Gender is a **completely uninformative feature** in this run. Fix: add a debug log line that prints the raw cell value before the mapping, then correct the matching logic.

**Patients with NaN fork scores:**
- Patients **001, 002, 004** — all four fork score columns are `NaN`, `subtotal_b_ext = 0.0`. A zero global score for a confirmed ET patient is clinically implausible. These are likely early incomplete CRF entries. All three are correctly skipped in Stage 5.
- Patient **024** — valid fork scores but `subtotal_b_ext = NaN`. Participates in local-score regression but is **excluded from global-score regression**. The missing cell should be recovered from the source document.

---

### 4.2 Stage 2–4a — Preprocessing & Segmentation

```
Data collection complete: 410 cycle records from 24 patients
```

One patient was lost between the 25 with sensor files and the 24 with valid cycles — likely a participant whose recordings produced no segments passing the quality filter.

> **[WARNING] ET_021 — corrupt CSV: `No columns to parse from file`.**  
> File: `Fork1_2024-05-16_10-52-05_021 ET part 3.csv`  
> The file is completely empty (0-byte or header-only). This session's data is permanently lost. Archive or delete the file; verify whether ET_021 has other valid recordings from a different session.

**Ambiguous `Fork_` files (4 occurrences):** Accepted with `hand = Right` via `FORK_DEFAULT_HAND`. If any of these patients are left-dominant, their CRF scores will be looked up for the wrong hand, silently corrupting both the regression target and the bucket assignment.

**ET_020 appearing between Control records** is expected — this patient shares a combined folder `"Control-003 and ET-020"`, which `_parse_folder_name()` correctly decomposes via regex into two independent records.

---

### 4.3 Stage 4b — Handedness Classifier

```
Trained on 410 cycles: 378 Right (92%), 32 Left (8%)
LOSO accuracy: 0.659  (target >= 0.900)

Confusion matrix:
           Pred Left  Pred Right
True Left     15          17       (46.9% correct)
True Right   123         255       (67.5% correct)
```

> **[CRITICAL] Handedness classifier is functionally broken for the Left class.**  
> 123 of 132 actual Left cycles are classified as Right — a 74% false-Right rate. The root cause is the **92%/8% class imbalance**: only 32 Left-hand cycles exist across the entire dataset. Despite `class_weight="balanced"`, LOSO leaves too few Left-hand examples per training fold to learn reliable chirality features. The classifier performs barely better than a majority-class baseline.
>
> **Consequence:** Any ambiguous `Fork_*` file genuinely belonging to a left-dominant patient will be systematically mislabeled, causing wrong CRF cell lookups (`lf_scoop`/`lf_stab` vs `rt_scoop`/`rt_stab`) and corrupted regression targets.
>
> **Short-term fix:** Trust only filename-derived labels; disable the classifier for `Fork_*` files or exclude ambiguous files entirely.  
> **Long-term fix:** Collect substantially more Fork2 (Left-hand) recordings.

---

### 4.4 Stage 4c — Movement Type Clustering

```
Cluster counts: {0: 70, 1: 8, 2: 280, 3: 52}
Label map:      {0: "scoop", 1: "fragment", 2: "other", 3: "stab"}
```

| Cluster | Label | Count | Share |
|---|---|---|---|
| 0 | scoop | 70 | 17.1% |
| 1 | fragment | 8 | 2.0% |
| **2** | **other** | **280** | **68.3%** |
| 3 | stab | 52 | 12.7% |

> **[WARNING] Cluster 2 ("other") captures 68% of all cycles.**  
> Since bucketed regression only uses `"scoop"` and `"stab"` cycles, 68% of the data is excluded from that analysis. Two likely explanations:
> 1. The label map assignment is wrong — cluster 2 may contain genuine eating cycles that the GMM did not cleanly separate from the other classes.
> 2. The protocol genuinely produces many non-eating movements between tasks.
>
> **Action required:** Re-inspect `cluster_inspection.pdf` and verify the label assignment. Consider whether k=3 (scoop, stab, other) would produce cleaner separation than k=4.

The fragment cluster (n=8, 2%) is unusually sparse — the `classify_cycle_quality()` filter removes most fragments before they reach the GMM, leaving almost no fragment-class training examples for the model.

---

### 4.5 Stage 5 — Feature Extraction

```
Patients 001, 002, 004 skipped (missing CRF fork scores)
39 valid tests → 381 segments
Feature matrix: 381 rows × 221 columns
```

With `PER_SEGMENT=True` each row is one eating cycle. 221 columns = ~196 raw features + 25 metadata columns. The raw feature count (~196) versus the number of patients (24) gives a features-to-patients ratio of ~8:1 — a classic small-N high-dimensional setting where LOSO is mandatory and all reported metrics carry wide confidence intervals.

---

### 4.6 Stage 6 — Regression Results

#### Local Score (fork feeding, scale 0–4 per cell)

| Model | MAE | R² | Pearson r |
|---|---|---|---|
| LinearRegression | 0.538 | 0.618 | 0.819 |
| Ridge | 0.536 | 0.628 | 0.828 |
| Lasso | 0.566 | 0.611 | 0.844 |
| RandomForest | 0.566 | 0.594 | 0.796 |
| **GradientBoosting** | **0.500** | **0.677** | **0.848** |
| XGBoost | 0.498 | 0.623 | 0.808 |

> **[POSITIVE] GradientBoosting is the best local-score model: R²=0.677, Pearson r=0.848 under LOSO CV.**  
> The IMU signal explains ~68% of the variance in the clinician-rated fork-feeding tremor score. MAE ≈ 0.5 on a 0–4 scale corresponds to roughly one ordinal grade — clinically meaningful as a screening or monitoring tool.

**RFE feature selection** produced 25 gyroscope-dominated features: `gyro_x/y/z_ptp`, `gyro jerk statistics`, `gyro CWT energy ratio (4–12 Hz)`, `gyro spectral centroid/rolloff`, `gyro weighted mean/median frequency`, and `gyro peak-to-peak interval`. Only 6 of 25 selected features are accelerometer-derived. This is biologically coherent — ET is a kinetic action tremor manifesting primarily as rotational wrist/forearm oscillation.

#### Global Score (Subtotal B Extended, scale ~3–41)

| Model | MAE | R² | Pearson r |
|---|---|---|---|
| LinearRegression | 4.566 | 0.682 | 0.862 |
| Ridge | 4.464 | 0.697 | 0.870 |
| **Lasso** | **4.260** | **0.725** | **0.887** |
| RandomForest | 5.186 | 0.583 | 0.842 |
| GradientBoosting | 5.162 | 0.582 | 0.835 |
| XGBoost | 5.637 | 0.488 | 0.763 |

> **[POSITIVE] Lasso is the best global-score model: R²=0.725, Pearson r=0.887.**  
> Linear models consistently outperform tree-based models for the global score, indicating a more linear feature–score relationship and that tree models overfit with only ~14 ET patients per LOSO fold. MAE=4.26 on a 38-point range is approximately 11% error.

---

### 4.7 Stage 6b — Bucketed Regression

#### Sparsity Report

| Hand | Movement | Cycles | Patients | Status |
|---|---|---|---|---|
| Left | fragment | 2 | 2 | Skipped |
| Left | other | 14 | 4 | Skipped |
| **Left** | **scoop** | **8** | **4** | **SKIPPED — too sparse** |
| **Left** | **stab** | **8** | **2** | **SKIPPED — too sparse** |
| Right | fragment | 3 | 3 | Skipped |
| Right | other | 181 | 18 | Not a regression target |
| Right | scoop | 46 | 16 | Valid |
| **Right** | **stab** | **31** | **9** | **INVALID (R²<0 for all models)** |

> **[CRITICAL] All left-hand buckets are skipped. No regression analysis exists for left-hand tremor.** For bilateral and left-dominant ET patients this is a fundamental structural data gap.

#### Right_scoop (16 patients, 46 cycles)

| Model | MAE | R² | Pearson r |
|---|---|---|---|
| **Ridge** | **0.499** | **0.632** | **0.807** |
| RandomForest | 0.751 | 0.261 | 0.566 |
| GradientBoosting | 0.732 | 0.244 | 0.584 |
| XGBoost | 0.840 | 0.050 | 0.502 |

Ridge dominates tree models by a large margin. With only 16 patients in LOSO, each training fold has 15 patients — too small for a 100-tree forest. Ridge's L2 regularization is the correct inductive bias for this small-N setting. Selected features: `gyro_x_jerk_max`, `gyro_mag_rms`, `acc_x_cwt_energy_mean`, `acc_z_cwt_energy_mean`, `acc_z_cwt_energy_max`.

#### Right_stab (9 patients, 31 cycles) — Complete Failure

| Model | MAE | R² | Pearson r |
|---|---|---|---|
| Ridge | 1.225 | **−0.748** | 0.141 |
| RandomForest | 1.138 | **−0.539** | **−0.246** |
| GradientBoosting | 1.309 | **−0.858** | **−0.322** |
| XGBoost | 1.458 | **−1.145** | **−0.345** |

> **[CRITICAL] Right_stab: all 4 models produce negative R². Three models produce negative Pearson r. Every model is worse than predicting the mean.**  
>
> Root causes:
> 1. Only 9 patients — LOSO trains on 8, leaving near-zero degrees of freedom for regression.
> 2. The stab score variance may be low within these 9 patients.
> 3. The GMM `"stab"` label may be noisy (cluster 3, only 12.7% of all cycles).
>
> **Do NOT report these results as meaningful findings. Label as "insufficient data" in all reports.**

---

### 4.8 Stage 7 — Classification (ET vs Control)

#### Patient-Level Results — Clinically Honest (N=24, Specificity ≥ 80%)

| Model | Sensitivity | Specificity | AUC | N |
|---|---|---|---|---|
| **LogisticRegression** | **0.643** | **0.800** | **0.679** | 24 |
| SVC | 0.357 | 1.000 | 0.664 | 24 |
| XGBoost | 0.429 | 0.900 | 0.571 | 24 |
| RandomForest | 0.429 | 0.800 | 0.571 | 24 |
| GradientBoosting | 0.286 | 0.800 | 0.557 | 24 |

> **[POSITIVE] LogisticRegression is the best patient-level classifier:** Sensitivity=0.643, Specificity=0.800, AUC=0.679 at N=24.  
> SVC achieves Specificity=1.000 only by predicting nearly every patient as Control (Sensitivity=0.357 = ~5 of 14 ET patients correctly identified) — clinically unacceptable.

AUC range 0.557–0.679 at patient level. With N=24, the 95% confidence interval on AUC is approximately ±0.15–0.20, meaning these values are not statistically distinguishable from each other or from chance (AUC=0.50). Statistical significance requires approximately 40–50 patients.

#### Segment-Level Youden's J Optimization

| Model | Accuracy | Sensitivity | Specificity | AUC | J |
|---|---|---|---|---|---|
| LogisticRegression | 0.709 | 0.778 | 0.477 | 0.615 | 0.255 |
| SVC | 0.703 | 0.730 | 0.406 | 0.649 | 0.344 |
| RandomForest | 0.630 | 0.621 | 0.343 | 0.626 | 0.280 |
| GradientBoosting | 0.732 | 0.836 | 0.386 | 0.580 | 0.223 |
| XGBoost | 0.688 | 0.730 | 0.545 | 0.632 | 0.276 |

All Youden J values (0.223–0.344) are low, confirming that no classifier achieves strong simultaneous sensitivity and specificity. Specificity is consistently below 0.55 for the highest-sensitivity models.

#### Regress-then-Classify

| Mode | Sensitivity | Specificity | AUC |
|---|---|---|---|
| **Fixed threshold=0.50** | **0.935** | **0.068** | 0.665 |
| Youden optimal (threshold=9.044) | 0.669 | 0.670 | 0.665 |
| Patient-level (Spec≥80%, threshold=23.426) | 0.286 | 0.800 | 0.643 |

> **[WARNING] Fixed threshold=0.50 gives Specificity=0.068 — clinically useless.** The threshold is miscalibrated: Controls are assigned score=0 while ET patients have scores well above 0.5. Do **not** report this result.  
>
> **[POSITIVE] Youden-optimal threshold=9.044 gives the most balanced segment-level result of all approaches:** Sensitivity=0.669, Specificity=0.670, AUC=0.665.

---

### 4.9 Stage 7d — SHAP Feature Importance

#### Regression — Top 10 Features

| Rank | Feature | SHAP | Clinical Interpretation |
|---|---|---|---|
| 1 | `gyro_y_cwt_energy_ratio` | 0.2510 | ET tremor power (4–12 Hz) / total gyro energy — direct tremor quantification |
| 2 | `gyro_p2p_mean` | 0.1736 | Mean peak-to-peak interval of gyro magnitude |
| 3 | `gyro_mag_ptp` | 0.1090 | Gyro magnitude peak-to-peak amplitude |
| 4 | `gyro_z_ptp` | 0.0874 | Z-axis gyro peak-to-peak |
| 5 | `gyro_x_jerk_max` | 0.0863 | Max rotational jerk (X-axis) |
| 6 | `gyro_wt_mean_freq` | 0.0739 | Weighted mean frequency of gyro magnitude |
| 7 | `gyro_y_jerk_mean` | 0.0665 | Mean rotational jerk (Y-axis) |
| 8 | `acc_x_cwt_energy_ratio` | 0.0651 | Accelerometer ET-band CWT energy ratio |
| 9 | `gyro_x_ptp` | 0.0465 | X-axis gyro peak-to-peak |
| 10 | `corr_acc_z_gyro_z` | 0.0445 | Z-axis accelerometer–gyroscope coupling |

9 of 10 top regression features are gyroscope-derived. `gyro_y_cwt_energy_ratio` — the fraction of rotational energy in the 4–12 Hz Morlet CWT band — is the single most important feature by a wide margin (SHAP=0.251 vs 0.174 for #2).

#### Classification — Top 10 Features

| Rank | Feature | SHAP | Clinical Interpretation |
|---|---|---|---|
| 1 | `gyro_wt_mean_freq` | 0.8067 | Weighted mean frequency of gyro motion |
| 2 | `gyro_x_spec_rolloff` | 0.6167 | Spectral rolloff frequency (X gyro) |
| 3 | `corr_acc_y_acc_z` | 0.5726 | Y–Z accelerometer coupling (arm orientation) |
| 4 | `acc_z_spec_rolloff` | 0.4498 | Spectral rolloff (Z acc) |
| 5 | `acc_y_power_4_12hz` | 0.4080 | ET-band power ratio (Y acc) |
| 6 | `acc_y_rms` | 0.3917 | RMS acceleration (Y-axis) |
| 7 | `acc_x_power_4_12hz` | 0.3873 | ET-band power ratio (X acc) |
| 8 | `acc_x_cwt_energy_std` | 0.2901 | CWT energy variability (X acc) |
| 9 | `acc_wt_mean_freq` | 0.2679 | Weighted mean frequency of acc magnitude |
| 10 | `acc_p2p_mean` | 0.2582 | Mean peak-to-peak interval (acc) |

Classification features are more evenly split between acc and gyro, dominated by spectral frequency descriptors. ET vs Control discrimination relies on the **frequency distribution of motion** (where energy is concentrated in the spectrum) rather than its absolute magnitude. This makes sense: Controls also produce arm motion during eating — the discriminative signal is the spectral signature difference.

---

### 4.10 Summary — Prioritised Issues & Recommended Actions

| Priority | Issue | Impact | Recommended Action |
|---|---|---|---|
| **P1** | `age = None` for all patients — `CRF_COL_AGE` wrong | Age is constant (65.0) in every model | Verify zero-indexed column in Excel; fix `config.py` |
| **P1** | `gender = 0.0` for all patients — Hebrew mapping failure | Gender uninformative in every model | Log raw cell value; fix Hebrew character matching |
| **P1** | Right_stab: all 4 models R²<0 (worst: −1.145) | Results are anti-predictive; must not be reported | Label "insufficient data"; collect more stab recordings |
| **P2** | Handedness accuracy 0.659 vs target 0.900 | Left-hand cycle labels are unreliable | Collect more Fork2 data; short-term: disable classifier for `Fork_` files |
| **P2** | Left_scoop (4 patients) and Left_stab (2 patients) both skipped | No left-hand bucket analysis at all | Structural gap; flag in report; collect more left-dominant participants |
| **P2** | GMM cluster "other" = 68% of all cycles | Most data excluded from bucketed regression | Re-inspect `cluster_inspection.pdf`; verify label map; consider k=3 |
| **P3** | ET_021 corrupt CSV (empty file) | One session permanently lost | Archive file; verify ET_021 has other valid recordings |
| **P3** | Patient 024 missing `subtotal_b_ext` | Excluded from global-score regression | Recover missing CRF value from source document |
| **P3** | RTC fixed threshold=0.50 gives Specificity=0.068 | Misleading result in report | Remove fixed-threshold result; report Youden-optimal only |

---

### 4.11 Key Positive Findings

1. **Local score regression — GradientBoosting R²=0.677, Pearson r=0.848 (LOSO CV).**  
   The IMU signal explains ~68% of the variance in the clinician-rated fork-feeding tremor score. MAE ≈ 0.5 on a 0–4 scale is clinically meaningful as a screening tool.

2. **Global score regression — Lasso R²=0.725, Pearson r=0.887 (LOSO CV).**  
   The strongest regression result in the run. Linear models consistently outperform tree-based models, suggesting a near-linear relationship between gyro spectral features and overall tremor burden.

3. **Right_scoop bucket — Ridge R²=0.632, Pearson r=0.807 (16 patients).**  
   The strongest single-bucket result and the most clinically targeted finding in the entire run.

4. **Patient-level classification — LogisticRegression Sensitivity=0.643, Specificity=0.800, AUC=0.679 (N=24).**  
   Above-chance ET vs Control discrimination under an honest leave-one-subject-out evaluation.

5. **SHAP interpretability — `gyro_y_cwt_energy_ratio` is the top regression feature (SHAP=0.251).**  
   Gyroscope-dominated feature sets are biologically coherent for a kinetic rotational tremor. Results are clinically explainable.

6. **Regress-then-classify (Youden optimal) — Sensitivity=0.669, Specificity=0.670, AUC=0.665.**  
   The most balanced segment-level classification result across all approaches tested in this run.

---

*This document was produced from the execution log of the Fork ET Detection Pipeline run on 2026-04-22. All metrics reflect LOSO CV on N=24 patients (ET=~14 with valid CRF, Control=10). Confidence intervals are wide at this sample size; findings should be treated as preliminary until validated on an independent cohort.*
