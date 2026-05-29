"""
Visualization helpers — all plots save to ``config.OUTPUT_DIR``.

**Must be imported AFTER ``matplotlib.use('Agg')``** (enforced below).
"""

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — MUST come before pyplot

import logging
import os
from typing import List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.metrics import roc_curve, auc
from sklearn.preprocessing import StandardScaler

import config as cfg
from ml_pipeline import META_COLS

logger = logging.getLogger("fork_pipeline.visualization")


def _savefig(fig: plt.Figure, filename: str) -> None:
    """Save figure to ``config.OUTPUT_DIR`` and close it."""
    path = os.path.join(cfg.OUTPUT_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved figure: %s", path)


# ── Public API ─────────────────────────────────────────────────────────────


def plot_scatter(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    title: str,
    filename: str,
    r2_train: Optional[float] = None,
    r2_cv: Optional[float] = None,
    r2_target: float = 0.70,
) -> None:
    """Scatter plot of true vs predicted scores with R² annotations.

    Annotates CV R² (and train R² when provided) directly on the figure.
    Draws a dashed horizontal reference at r2_target (default 0.70 per
    advisor guidance) on a secondary R² axis if train/CV R² are supplied.

    Args:
        y_true: Ground-truth values.
        y_pred: Predicted values.
        title: Plot title.
        filename: Output filename (e.g. ``"scatter_local.png"``).
        r2_train: Optional train-fold R² to annotate (advisor item 4a/4c).
        r2_cv: Optional CV (test) R² to annotate; computed from y_true/y_pred
               if not provided.
        r2_target: Target R² reference line (default 0.70).
    """
    from sklearn.metrics import r2_score as _r2

    if r2_cv is None:
        r2_cv = _r2(y_true, y_pred)

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(y_true, y_pred, alpha=0.7, edgecolors="k", linewidths=0.5)
    lims = [
        min(np.min(y_true), np.min(y_pred)) - 0.5,
        max(np.max(y_true), np.max(y_pred)) + 0.5,
    ]
    ax.plot(lims, lims, "--", color="grey", linewidth=1)
    ax.set_xlim(lims)
    ax.set_ylim(lims)
    ax.set_xlabel("True Score")
    ax.set_ylabel("Predicted Score")

    # Annotate R² values on the figure
    annotation_lines = [f"CV R² = {r2_cv:.3f}"]
    if r2_train is not None:
        annotation_lines.insert(0, f"Train R² = {r2_train:.3f}")
    annotation_lines.append(f"Target R² ≥ {r2_target:.2f}")
    ax.text(
        0.05, 0.95, "\n".join(annotation_lines),
        transform=ax.transAxes,
        verticalalignment="top",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "wheat", "alpha": 0.7},
    )

    ax.set_title(title)
    _savefig(fig, filename)


def plot_boxplot(
    features_df: pd.DataFrame,
    group_col: str,
    filename: str,
    max_features: int = 8,
) -> None:
    """Side-by-side box plots for top features coloured by group.

    Args:
        features_df: DataFrame with features + a group column.
        group_col: Column name used for grouping (e.g. ``"group"``).
        filename: Output filename.
        max_features: Maximum number of feature subplots.
    """
    feat_cols = [c for c in features_df.columns if c not in META_COLS]
    # Pick features with highest variance among numeric columns
    feat_df = features_df[feat_cols].select_dtypes(include=[np.number])
    variances = feat_df.var().sort_values(ascending=False)
    top = variances.head(max_features).index.tolist()

    n = len(top)
    fig, axes = plt.subplots(1, n, figsize=(3 * n, 5), sharey=False)
    if n == 1:
        axes = [axes]
    groups = features_df[group_col].unique()
    for ax, col in zip(axes, top):
        data = [features_df.loc[features_df[group_col] == g, col].dropna()
                for g in groups]
        bp = ax.boxplot(data, labels=groups, patch_artist=True)
        # FIXED: plot_boxplot() — динамическая палитра для групп (IndexError при >2)
        colours = plt.cm.tab10.colors
        for patch, colour in zip(bp["boxes"], colours[:len(groups)]):
            patch.set_facecolor(colour)
        ax.set_title(col, fontsize=8)
        ax.tick_params(labelsize=7)
    fig.suptitle("Feature distributions by group", fontsize=12)
    fig.tight_layout()
    _savefig(fig, filename)


def plot_pca(
    features_df: pd.DataFrame,
    label_col: str,
    filename: str,
) -> None:
    """2-D PCA projection coloured by label.

    Args:
        features_df: DataFrame with features + label column.
        label_col: Column to colour by (e.g. ``"is_et"``).
        filename: Output filename.
    """
    feat_cols = [c for c in features_df.columns if c not in META_COLS]

    from sklearn.impute import SimpleImputer
    
    # Keep only numeric feature columns; movement_type and similar labels may be strings.
    X_df = features_df[feat_cols].select_dtypes(include=[np.number])
    if X_df.shape[1] == 0:
        logger.warning("PCA plot skipped: no numeric feature columns available.")
        return

    X = X_df.values
    imputer = SimpleImputer(strategy='mean')
    X_imputed = imputer.fit_transform(X)
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_imputed)
    pca = PCA(n_components=2)
    comp = pca.fit_transform(X_scaled)

    labels = features_df[label_col].values
    fig, ax = plt.subplots(figsize=(7, 5))
    scatter = ax.scatter(
        comp[:, 0], comp[:, 1], c=labels, cmap="coolwarm",
        alpha=0.8, edgecolors="k", linewidths=0.5,
    )
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.1%})")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.1%})")
    ax.set_title("PCA — ET vs Control")
    fig.colorbar(scatter, ax=ax, label=label_col)
    _savefig(fig, filename)


def plot_umap(
    features_df: pd.DataFrame,
    label_col: str,
    filename: str,
    n_neighbors: int = 15,
    min_dist: float = 0.1,
    random_state: int = 42,
) -> None:
    """2-D UMAP projection coloured by label (advisor item 1b/1c — EDA only).

    UMAP is used **purely for visualization** — the reduced components are
    never passed into estimators.  Named model features are preserved as-is.

    Requires ``umap-learn`` (``pip install umap-learn``).  If the library is
    not installed, a warning is logged and the function returns without error.

    Args:
        features_df: DataFrame with features + label column.
        label_col: Column to colour by (e.g. ``"is_et"`` or ``"severity"``).
        filename: Output filename.
        n_neighbors: UMAP neighbourhood size parameter.
        min_dist: UMAP minimum distance parameter.
        random_state: Random seed for reproducibility.
    """
    try:
        import umap as umap_lib
    except ImportError:
        logger.warning(
            "umap-learn not installed — UMAP plot skipped. "
            "Install with: pip install umap-learn"
        )
        return

    from sklearn.impute import SimpleImputer

    feat_cols = [c for c in features_df.columns if c not in META_COLS]
    X_df = features_df[feat_cols].select_dtypes(include=[np.number])
    if X_df.shape[1] == 0:
        logger.warning("UMAP plot skipped: no numeric feature columns available.")
        return

    X = X_df.values
    imputer = SimpleImputer(strategy="mean")
    X_imputed = imputer.fit_transform(X)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_imputed)

    reducer = umap_lib.UMAP(
        n_components=2,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        random_state=random_state,
    )
    comp = reducer.fit_transform(X_scaled)

    label_values = features_df[label_col].values

    # For string/categorical labels encode to integers for scatter coloring,
    # then annotate the colorbar with the original category names.
    if label_values.dtype.kind in ("U", "O", "S"):
        unique_labels = sorted(set(label_values))
        label_map = {v: i for i, v in enumerate(unique_labels)}
        color_values = np.array([label_map[v] for v in label_values], dtype=float)
        cmap = "tab10"
    else:
        color_values = label_values.astype(float)
        unique_labels = None
        cmap = "coolwarm"

    fig, ax = plt.subplots(figsize=(7, 5))
    scatter = ax.scatter(
        comp[:, 0], comp[:, 1], c=color_values, cmap=cmap,
        alpha=0.8, edgecolors="k", linewidths=0.5,
    )
    ax.set_xlabel("UMAP-1")
    ax.set_ylabel("UMAP-2")
    ax.set_title(f"UMAP — colored by {label_col}")
    cbar = fig.colorbar(scatter, ax=ax, label=label_col)
    # Replace numeric ticks with original category names for string labels
    if unique_labels is not None:
        cbar.set_ticks(list(range(len(unique_labels))))
        cbar.set_ticklabels(unique_labels)
    _savefig(fig, filename)


def plot_roc(
    y_true: np.ndarray,
    y_score: np.ndarray,
    filename: str,
) -> None:
    """ROC curve with AUC annotation.

    Args:
        y_true: Binary ground-truth labels.
        y_score: Predicted probabilities for the positive class.
        filename: Output filename.
    """
    fpr, tpr, _ = roc_curve(y_true, y_score)
    roc_auc = auc(fpr, tpr)

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, linewidth=2, label=f"AUC = {roc_auc:.3f}")
    ax.plot([0, 1], [0, 1], "--", color="grey", linewidth=1)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curve — ET vs Control")
    ax.legend(loc="lower right")
    _savefig(fig, filename)


def plot_signal_with_segments(
    magnitude: np.ndarray,
    segments: List[Tuple[int, int]],
    patient_id: str,
    filename: str,
    fs: float = cfg.FS,
) -> None:
    """Plot accelerometer magnitude highlighting detected activity segments.

    Args:
        magnitude: 1-D array of magnitude values.
        segments: List of ``(start_idx, end_idx)`` tuples.
        patient_id: Used in the title.
        filename: Output filename.
        fs: Sampling frequency.
    """
    t = np.arange(len(magnitude)) / fs
    fig, ax = plt.subplots(figsize=(12, 3))
    ax.plot(t, magnitude, linewidth=0.5, color="steelblue")
    for s, e in segments:
        ax.axvspan(s / fs, e / fs, alpha=0.25, color="orange")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Magnitude (g)")
    ax.set_title(f"Activity detection — {patient_id}")
    _savefig(fig, filename)


def plot_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    filename: str,
    labels: Optional[List[str]] = None,
) -> None:
    """Two-panel confusion matrix heatmap: raw counts + row-normalised recall.

    Normalisation adjusts for class imbalance (advisor requirement) so the
    right panel shows per-class recall regardless of group size differences.

    Args:
        y_true: True labels.
        y_pred: Predicted labels.
        filename: Output filename.
        labels: Class names for display.
    """
    from sklearn.metrics import confusion_matrix as cm_func

    if labels is None:
        labels = ["Control", "ET"]

    # Use the actual unique values present in y_true/y_pred for CM ordering,
    # then map display_labels by position so Control→row0, ET→row1.
    unique_vals = sorted(np.unique(np.concatenate([y_true, y_pred])))
    cm = cm_func(y_true, y_pred, labels=unique_vals)
    row_sums = cm.sum(axis=1, keepdims=True)
    # Row-normalised: each row sums to 1 (per-class recall / sensitivity)
    cm_norm = np.divide(cm.astype(float), row_sums, where=row_sums > 0)

    n = len(labels)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    panels = [
        (axes[0], cm,      lambda v: f"{int(v)}",  "Counts",             "Count"),
        (axes[1], cm_norm, lambda v: f"{v:.0%}",   "Row-Normalised (%)", "Recall"),
    ]
    for ax, data, fmt_fn, subtitle, cbar_lbl in panels:
        vmax = None if subtitle == "Counts" else 1.0
        im   = ax.imshow(data, interpolation="nearest", cmap="Blues", vmin=0, vmax=vmax)
        fig.colorbar(im, ax=ax, label=cbar_lbl)
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(labels)
        ax.set_yticklabels(labels)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("True")
        ax.set_title(f"Confusion Matrix — {subtitle}")
        threshold = data.max() / 2.0
        for i in range(n):
            for j in range(n):
                ax.text(
                    j, i, fmt_fn(data[i, j]),
                    ha="center", va="center",
                    color="white" if data[i, j] > threshold else "black",
                )

    fig.tight_layout()
    _savefig(fig, filename)


def plot_severity_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    labels: List[str],
    score_col: str = "local_score",
    filename: str = "severity_cm_local.png",
) -> None:
    """Two-panel confusion matrix for multi-class ET severity classification.

    Left panel: raw counts.  Right panel: row-normalised recall (%).

    Args:
        y_true: True severity label strings.
        y_pred: Predicted severity label strings.
        labels: Ordered class labels present in the data.
        score_col: Score name used only for the figure title.
        filename: Output filename.
    """
    from sklearn.metrics import confusion_matrix as cm_func

    cm = cm_func(y_true, y_pred, labels=labels)
    row_sums = cm.sum(axis=1, keepdims=True)
    cm_norm  = np.divide(cm.astype(float), row_sums, where=row_sums > 0)

    n   = len(labels)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))

    panels = [
        (axes[0], cm,      lambda v: f"{int(v)}",  "Counts",              "Count"),
        (axes[1], cm_norm, lambda v: f"{v:.0%}",   "Row-Normalised (%)",  "Recall"),
    ]
    for ax, data, fmt_fn, subtitle, cbar_lbl in panels:
        vmax = None if subtitle == "Counts" else 1.0
        im   = ax.imshow(data, interpolation="nearest", cmap="Blues", vmin=0, vmax=vmax)
        fig.colorbar(im, ax=ax, label=cbar_lbl)
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(labels, fontsize=9)
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlabel("Predicted Severity")
        ax.set_ylabel("True Severity")
        ax.set_title(subtitle)
        threshold = data.max() / 2.0
        for i in range(n):
            for j in range(n):
                ax.text(
                    j, i, fmt_fn(data[i, j]),
                    ha="center", va="center", fontsize=10,
                    color="white" if data[i, j] > threshold else "black",
                )

    score_label = "Local Score (Fork Task)" if score_col == "local_score" else "Global Score"
    fig.suptitle(
        f"ET Severity Classification — {score_label}",
        fontsize=12, fontweight="bold",
    )
    fig.tight_layout()
    _savefig(fig, filename)


def plot_bland_altman(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    title: str,
    filename: str,
) -> None:
    """Bland-Altman plot (agreement between prediction and ground truth).

    Args:
        y_true: True values.
        y_pred: Predicted values.
        title: Plot title.
        filename: Output filename.
    """
    mean_vals = (y_true + y_pred) / 2.0
    diff_vals = y_true - y_pred
    mean_diff = np.mean(diff_vals)
    std_diff = np.std(diff_vals, ddof=1)

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(mean_vals, diff_vals, alpha=0.7, edgecolors="k", linewidths=0.5)
    ax.axhline(mean_diff, color="blue", linestyle="-", linewidth=1,
               label=f"Mean diff = {mean_diff:.3f}")
    ax.axhline(mean_diff + 1.96 * std_diff, color="red", linestyle="--",
               linewidth=1, label=f"+1.96 SD = {mean_diff + 1.96 * std_diff:.3f}")
    ax.axhline(mean_diff - 1.96 * std_diff, color="red", linestyle="--",
               linewidth=1, label=f"−1.96 SD = {mean_diff - 1.96 * std_diff:.3f}")
    ax.set_xlabel("Mean of True & Predicted")
    ax.set_ylabel("True − Predicted")
    ax.set_title(title)
    ax.legend(fontsize=8)
    fig.tight_layout()
    _savefig(fig, filename)


def plot_cluster_pca(
    features_df: pd.DataFrame,
    cluster_col: str = "movement_type",
    filename: str = "pca_movement_clusters.png",
) -> None:
    """2-D PCA scatter coloured by movement-type cluster label.

    Args:
        features_df: DataFrame with feature columns + a cluster label column.
        cluster_col: Column containing cluster labels (e.g. "movement_type").
        filename: Output filename.
    """
    feat_cols = [c for c in features_df.columns if c not in META_COLS]
    if cluster_col not in features_df.columns or not feat_cols:
        return

    from sklearn.impute import SimpleImputer

    X = features_df[feat_cols].values
    imputer = SimpleImputer(strategy="mean")
    X_s = StandardScaler().fit_transform(imputer.fit_transform(X))
    pca = PCA(n_components=2)
    comp = pca.fit_transform(X_s)

    labels = features_df[cluster_col].values
    unique_labels = sorted(set(labels))
    colors = plt.cm.tab10.colors

    fig, ax = plt.subplots(figsize=(8, 6))
    for i, lbl in enumerate(unique_labels):
        mask = labels == lbl
        ax.scatter(
            comp[mask, 0], comp[mask, 1],
            label=str(lbl), alpha=0.7, s=30,
            color=colors[i % len(colors)],
        )
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.1%})")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.1%})")
    ax.set_title("PCA — movement-type clusters")
    ax.legend(title=cluster_col, fontsize=9)
    fig.tight_layout()
    _savefig(fig, filename)


def plot_and_save_patient_signal(
    df: pd.DataFrame, 
    patient_run_id: str, 
    group: str, 
    local_score: float, 
    out_dir: str
) -> None:
    """Plot accelerometer and gyroscope signals for a single patient segment.
    
    Args:
        df: DataFrame with acc_x, acc_y, acc_z and gyro_x, gyro_y, gyro_z.
        patient_run_id: Patient ID including run number.
        group: Group ('ET' or 'Control').
        local_score: Clinical score for the task.
        out_dir: Directory to save the figure in.
    """
    os.makedirs(out_dir, exist_ok=True)
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    
    # Time axis in seconds (based on sampling frequency)
    t = np.arange(len(df)) / cfg.FS
    
    # 1. Accelerometer
    ax_acc = axes[0]
    ax_acc.plot(t, df["acc_x"], color="tab:blue", label="X", linewidth=1.5)
    ax_acc.plot(t, df["acc_y"], color="tab:orange", label="Y", linewidth=1.5)
    ax_acc.plot(t, df["acc_z"], color="tab:green", label="Z", linewidth=1.5)
    ax_acc.set_title("Accelerometer", fontsize=14)
    ax_acc.set_ylabel("Acceleration [m/s²]", fontsize=12)
    ax_acc.legend(loc="upper right", fontsize=10)
    ax_acc.grid(True, linestyle="--", alpha=0.6)
    
    # 2. Gyroscope
    ax_gyr = axes[1]
    ax_gyr.plot(t, df["gyro_x"], color="tab:blue", label="X", linewidth=1.5)
    ax_gyr.plot(t, df["gyro_y"], color="tab:orange", label="Y", linewidth=1.5)
    ax_gyr.plot(t, df["gyro_z"], color="tab:green", label="Z", linewidth=1.5)
    ax_gyr.set_title("Gyroscope", fontsize=14)
    ax_gyr.set_ylabel("Angular Velocity [rad/s]", fontsize=12)
    ax_gyr.set_xlabel("Time [sec]", fontsize=12)
    ax_gyr.legend(loc="upper right", fontsize=10)
    ax_gyr.grid(True, linestyle="--", alpha=0.6)
    
    if not isinstance(local_score, (int, float)) or pd.isna(local_score):
        score_str = "NaN"
    else:
        score_str = f"{local_score:.1f}"
        
    fig.suptitle(
        f"Patient: {patient_run_id} | Group: {group} | Local Fork Score: {score_str}", 
        fontsize=16, fontweight='bold'
    )
    fig.tight_layout()
    fig.subplots_adjust(top=0.92)
    
    filename = f"{group}_{patient_run_id}_score_{score_str}.png"
    filepath = os.path.join(out_dir, filename)
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved patient signal plot to %s", filepath)

