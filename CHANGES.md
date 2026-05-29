# CHANGES — ET Severity Pipeline Advisor Feedback Implementation
<!-- One entry per edit, in execution order. -->
<!-- Format: ## <date> — Step <#>: <title> -->
<!-- Each entry: File, Function/section, Reason, BEFORE, AFTER, Revert -->
<!-- Skipped steps logged as SKIPPED with reason. -->

---

## 2026-05-29 — Step 0: Baseline established
- File: N/A (no code changed)
- Reason: Record pre-change state before any edits.
- Baseline: CHANGES.md created. Pipeline state = commit e0de4c9.
  All subsequent changes will reference this baseline.
- Revert: N/A

---

## 2026-05-29 — Step 1: Encoding fix — utf-8-sig for BOM CSV files
- File: `data_loader.py`
- Function/section: `read_imu_csv` (line ~130)
- Reason: Advisor constraint — BOM CSVs must use `utf-8-sig`. Without it, a BOM on the
  first cell is coerced to NaN and silently dropped.
- BEFORE:
  ```python
  df = pd.read_csv(filepath, header=None)
  ```
- AFTER:
  ```python
  # encoding="utf-8-sig" strips the UTF-8 BOM on the first cell if present,
  # preventing silent NaN corruption on BOM-marked CSV files.
  df = pd.read_csv(filepath, header=None, encoding="utf-8-sig")
  ```
- Revert: restore `df = pd.read_csv(filepath, header=None)` and delete the two comment lines above it.

---

## 2026-05-29 — Step 2: Remove SMOTE from run_classification
- File: `ml_pipeline.py`
- Function/section: `run_classification`
- Reason: Advisor item 2b — SMOTE at segment level leaks patient identity across LOSO
  folds and double-corrects (class weights already present). Removed in three places.
- BEFORE (import):
  ```python
  from imblearn.over_sampling import SMOTE
  ```
- AFTER: import line deleted entirely.
- BEFORE (instantiation):
  ```python
  smote = SMOTE(random_state=cfg.RANDOM_STATE)
  ```
- AFTER: line deleted entirely.
- BEFORE (in-fold block):
  ```python
  try:
      X_train_res, y_train_res = smote.fit_resample(X_train_sel, y_train)
  except ValueError:
      X_train_res, y_train_res = X_train_sel, y_train

  fold_model = clone(model)
  fold_model.fit(X_train_res, y_train_res)
  ```
- AFTER:
  ```python
  # Class imbalance handled by class_weight / scale_pos_weight on the model.
  # SMOTE removed: segment-level resampling leaks patient identity in LOSO.
  fold_model = clone(model)
  fold_model.fit(X_train_sel, y_train)
  ```
- Revert: re-add the three BEFORE snippets and restore the SMOTE import.
- ADDENDUM (stacking branch): also removed residual `smote.fit_resample` in the
  `USE_STACKING` inner loop (line ~719); replaced with direct `fs.fit(X_tr_sel, y_tr)`.

---

## 2026-05-29 — Step 3: Remove SMOTE from run_calibrated_classification
- File: `ml_pipeline.py`
- Function/section: `run_calibrated_classification`
- Reason: Same as Step 2 — segment-level SMOTE leaks patient identity; class weights handle imbalance.
- BEFORE (docstring line):
  ```python
  data leakage.  SMOTE is applied after scaling+RFE on training fold.
  ```
- AFTER:
  ```python
  data leakage. Class imbalance is handled via class_weight / bal_weight on the model.
  SMOTE was removed: segment-level resampling leaks patient identity in LOSO.
  ```
- BEFORE (instantiation):
  ```python
  from imblearn.over_sampling import SMOTE
  smote = SMOTE(random_state=cfg.RANDOM_STATE)
  ```
- AFTER: both lines deleted.
- BEFORE (in-fold block):
  ```python
  # 3. SMOTE on selected+scaled train data
  try:
      X_train_res, y_train_res = smote.fit_resample(X_train_sel, y_train)
  except ValueError:
      X_train_res, y_train_res = X_train_sel, y_train

  # 4. Fit calibrated model and predict
  ...
  calibrated.fit(X_train_res, y_train_res)
  ```
- AFTER:
  ```python
  # 3. Fit calibrated model and predict.
  # Class imbalance handled by class_weight / bal_weight on the base model.
  # SMOTE removed: segment-level resampling leaks patient identity in LOSO.
  ...
  calibrated.fit(X_train_sel, y_train)
  ```
- Revert: restore the BEFORE snippets.

---

## 2026-05-29 — Step 4: Binary severity config constants
- File: `config.py`
- Function/section: Stage F section (end of file, after SEVERITY_GLOBAL_LABELS)
- Reason: Advisor item 3a — group severity {0,1} vs {2,3,4} on raw per-item TETRAS cells.
  Existing SEVERITY_* constants unchanged.
- BEFORE: nothing (new addition)
- AFTER:
  ```python
  SEVERITY_BINARY_THRESHOLD = 2
  SEVERITY_BINARY_LABELS    = ["Low", "High"]
  ```
- Revert: delete the two new constants and their comment block.

---

## 2026-05-29 — Step 5: Binary severity logic — run_binary_severity_classification
- File: `ml_pipeline.py` (new function), `main.py` (import + Stage 7e call)
- Function/section: new `run_binary_severity_classification` added after `run_severity_classification`
- Reason: Advisor item 3a — binary {0,1} vs {2,3,4} on raw per-item TETRAS cells.
  Existing `run_severity_classification` unchanged.
- BEFORE: function did not exist; `main.py` imported only `run_severity_classification`
- AFTER: `run_binary_severity_classification` added to `ml_pipeline.py`;
  imported in `main.py`; called in Stage 7e with result stored in `sev_binary`.
- Revert: delete `run_binary_severity_classification` from `ml_pipeline.py`;
  remove the import line and the Stage 7e call block from `main.py`.

---

## 2026-05-29 — Step 6: Train + CV metrics in run_regression
- File: `ml_pipeline.py`
- Function/section: `run_regression` — inner fold loop
- Reason: Advisor item 4a — plot metrics for BOTH training set and test (CV) set.
  Added `y_pred_train` array populated with in-sample predictions each fold.
  After the fold loop, compute train-fold aggregated metrics and store as
  `train_R2` / `train_MAE` alongside the existing CV metrics.
- BEFORE: `y_pred = np.zeros(len(y))` only; no train-fold capture.
- AFTER: `y_pred_train` array added; populated inside fold loop; train metrics
  computed post-loop with "train_" prefix keys added to the results dict.
- Revert: remove `y_pred_train` array, the train-fold predict line, and the
  train-metrics block (from "Train-fold metrics:" comment to end of else branch).

---

## 2026-05-29 — Step 7: Normalized confusion matrices
- File: `visualization.py`
- Function/section: `plot_confusion_matrix`
- Reason: Advisor item 4b — CM on test set must reflect normalized/balanced output.
  `plot_severity_confusion_matrix` already had 2 panels; extended `plot_confusion_matrix`
  (binary ET vs Control) to match: left=raw counts, right=row-normalised recall (%).
- BEFORE: single-panel raw count heatmap.
- AFTER: two-panel figure (counts + row-normalised recall). Function signature unchanged.
- Revert: restore the original single-panel `plot_confusion_matrix` implementation.

---

## 2026-05-29 — Step 8: R² annotation on scatter plot
- File: `visualization.py` (`plot_scatter`), `main.py` (Stage 8 call)
- Reason: Advisor item 4c — plot R² directly on graphs; target ~0.70.
- BEFORE: `plot_scatter` had no R² parameters; figure showed no annotation.
- AFTER: added optional `r2_train`, `r2_cv`, `r2_target=0.70` parameters;
  annotates CV R² (+ train R² if provided) in a text box on the figure.
  `main.py` now passes `r2_train` from `reg_local` results to the call.
- Revert: remove the three new parameters + annotation block from `plot_scatter`;
  restore original `viz.plot_scatter(...)` call in `main.py` (no r2_train kwarg).

---

## 2026-05-29 — Step 9: UMAP visualization
- Files: `requirements.txt`, `visualization.py` (new `plot_umap`), `main.py` (Stage 8 call)
- Reason: Advisor items 1b/1c — UMAP scatter for EDA. Named features kept as model inputs.
  umap-learn added to dependencies with graceful ImportError fallback in the function.
- BEFORE: `requirements.txt` had no umap-learn; `plot_umap` did not exist.
- AFTER: `umap-learn>=0.5` in requirements; `plot_umap` added to `visualization.py`;
  called in `main.py` Stage 8 (`umap_et_vs_control.png`).
- Revert: remove `umap-learn>=0.5` from `requirements.txt`; delete `plot_umap` from
  `visualization.py`; remove the Stage 8 `plot_umap` call from `main.py`.

---

## 2026-05-29 — Step 10: Correlation-filter — SKIPPED (no-op)
- File: N/A
- Reason: Grep for `drop.*corr`, `corr_threshold`, `drop_correlated` across all `.py`
  files returned zero matches. No correlation-threshold feature-dropping filter exists.
  Advisor item 1a requires no code change.
- Revert: N/A

---

## 2026-05-29 — Step 11: sev_binary wired into report + final integrity check
- File: `main.py` (Stage 9 `report_metrics` dict)
- Reason: Ensure `sev_binary` result from Step 5 reaches the report generator.
- BEFORE: `report_metrics` had `sev_local` and `sev_global` but not `sev_binary`.
- AFTER: `"sev_binary": sev_binary` added to `report_metrics`.
- Revert: remove the `"sev_binary": sev_binary` line.
- Integrity checks passed:
  - `smote.fit_resample` / `from imblearn` → 0 matches in `ml_pipeline.py` ✓
  - No correlation-threshold filter in any `.py` file ✓
  - All existing variable names preserved (additive changes only) ✓
  - New comments in English; existing Russian comments untouched ✓

---
