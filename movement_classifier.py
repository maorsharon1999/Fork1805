"""
Per-cycle movement-type classifier using biomechanical rules.

Rules applied in priority order:
    1. fragment : duration < RULE_FRAGMENT_MAX_DUR  AND
                  jerk_ratio < RULE_FRAGMENT_MAX_JERK_RATIO
    2. scoop    : lateral tilt dominates (acc_y > acc_z),
                  roll rotation dominates (gyro_y > gyro_x),
                  peak jerk falls in mid-cycle
    3. stab     : vertical range dominates (acc_z > acc_y),
                  peak jerk falls in first half of cycle
    4. other    : everything else

Thresholds live in config.py (RULE_* constants) and can be tuned by
inspecting the validation PDF produced by generate_inspection_pdf().
"""

import logging
import os
from typing import List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

import config as cfg

logger = logging.getLogger("fork_pipeline.movement_classifier")

_LABEL_ORDER = ["scoop", "stab", "fragment", "other"]
_LABEL_TO_INT = {lbl: i for i, lbl in enumerate(_LABEL_ORDER)}


class MovementClassifier:
    """Rule-based movement-type classifier (no training required).

    Rules:
        fragment: short AND weak (duration + jerk thresholds)
        scoop   : acc_y tilt dominates, gyro_y roll dominates, mid-cycle peak jerk
        stab    : acc_z vertical range dominates, early peak jerk
        other   : everything else
    """

    # fit() is a no-op — kept so main.py call-sites don't need to change.
    def fit(self, cycles: List[pd.DataFrame], fs: float = cfg.FS) -> None:
        counts = {lbl: 0 for lbl in _LABEL_ORDER}
        for c in cycles:
            counts[self.predict_label(c, fs)] += 1
        logger.info(
            "MovementClassifier (rule-based): %d cycles classified. Counts: %s",
            len(cycles), counts,
        )

    # ── Feature extraction ─────────────────────────────────────────────────

    def _extract_features(self, cycle_df: pd.DataFrame, fs: float = cfg.FS) -> dict:
        ax = cycle_df["acc_x"].values.astype(np.float64)
        ay = cycle_df["acc_y"].values.astype(np.float64)
        az = cycle_df["acc_z"].values.astype(np.float64)
        gx = cycle_df["gyro_x"].values.astype(np.float64)
        gy = cycle_df["gyro_y"].values.astype(np.float64)

        acc_mag = np.sqrt(ax**2 + ay**2 + az**2)
        jerk = np.abs(np.gradient(acc_mag, 1.0 / fs))
        mean_jerk = float(jerk.mean()) if jerk.mean() > 1e-10 else 1e-10
        n = len(cycle_df)

        return {
            "duration":        float(n / fs),
            "jerk_ratio":      float(jerk.max() / mean_jerk),
            "acc_y_range":     float(np.ptp(ay)),
            "acc_z_range":     float(np.ptp(az)),
            "gy_std":          float(np.std(gy)),
            "gx_std":          max(float(np.std(gx)), 1e-10),
            "peak_jerk_time":  float(np.argmax(jerk) / max(n - 1, 1)),
        }

    # ── Rule engine ────────────────────────────────────────────────────────

    def _classify_features(self, f: dict) -> str:
        # 1. Fragment: short AND weak
        if (
            f["duration"] < cfg.RULE_FRAGMENT_MAX_DUR
            and f["jerk_ratio"] < cfg.RULE_FRAGMENT_MAX_JERK_RATIO
        ):
            return "fragment"

        # 2. Scoop: lateral tilt + roll dominance + mid-cycle peak
        if (
            f["acc_y_range"] > cfg.RULE_SCOOP_MIN_ACC_Y_RANGE
            and f["acc_y_range"] > f["acc_z_range"] * cfg.RULE_SCOOP_TILT_RATIO
            and f["gy_std"] > f["gx_std"] * cfg.RULE_SCOOP_GYRO_RATIO
            and cfg.RULE_SCOOP_PEAK_JERK_MIN < f["peak_jerk_time"] < cfg.RULE_SCOOP_PEAK_JERK_MAX
        ):
            return "scoop"

        # 3. Stab: vertical range + early peak
        if (
            f["acc_z_range"] > cfg.RULE_STAB_MIN_ACC_Z_RANGE
            and f["acc_z_range"] > f["acc_y_range"] * cfg.RULE_STAB_VERT_RATIO
            and f["peak_jerk_time"] < cfg.RULE_STAB_PEAK_JERK_MAX
        ):
            return "stab"

        return "other"

    # ── Inference ──────────────────────────────────────────────────────────

    def predict_label(self, cycle_df: pd.DataFrame, fs: float = cfg.FS) -> str:
        return self._classify_features(self._extract_features(cycle_df, fs))

    def predict_all_labels(
        self, cycles: List[pd.DataFrame], fs: float = cfg.FS
    ) -> List[str]:
        return [self.predict_label(c, fs) for c in cycles]

    def predict_all_clusters(
        self, cycles: List[pd.DataFrame], fs: float = cfg.FS
    ) -> List[int]:
        """Integer indices (for backward compatibility with generate_inspection_pdf)."""
        return [_LABEL_TO_INT.get(self.predict_label(c, fs), 3) for c in cycles]

    # ── Validation PDF ────────────────────────────────────────────────────

    def generate_inspection_pdf(
        self,
        cycles: List[pd.DataFrame],
        cluster_assignments: Optional[List[int]] = None,  # ignored, kept for compat
        fs: float = cfg.FS,
        output_path: str = "cluster_inspection.pdf",
    ) -> None:
        """Generate a validation PDF: histograms + mean profiles + PCA.

        Use this to verify the rule thresholds are producing sensible
        splits — if not, adjust RULE_* constants in config.py and re-run.
        """
        labels = self.predict_all_labels(cycles, fs)
        feats_list = [self._extract_features(c, fs) for c in cycles]
        X = pd.DataFrame(feats_list)
        label_arr = np.array(labels)
        colors = plt.cm.tab10.colors
        counts = {lbl: int(np.sum(label_arr == lbl)) for lbl in _LABEL_ORDER}

        from matplotlib.backends.backend_pdf import PdfPages

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        with PdfPages(output_path) as pdf:
            # ── Page 1: feature histograms per movement type ───────────────
            feat_names = list(X.columns)
            ncols = 4
            nrows = int(np.ceil(len(feat_names) / ncols))
            fig, axes = plt.subplots(nrows, ncols, figsize=(16, 3 * nrows))
            axes = axes.ravel()
            for idx, col in enumerate(feat_names):
                ax = axes[idx]
                for ci, lbl in enumerate(_LABEL_ORDER):
                    vals = X.loc[label_arr == lbl, col].values
                    if len(vals) > 0:
                        ax.hist(
                            vals, bins=15, alpha=0.5, label=lbl, density=True,
                            color=colors[ci % len(colors)],
                        )
                ax.set_title(col, fontsize=8)
                ax.legend(fontsize=5)
                ax.tick_params(labelsize=6)
            for ax in axes[len(feat_names):]:
                ax.set_visible(False)
            fig.suptitle(
                f"Feature distributions by movement type  {counts}",
                fontsize=12,
            )
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)

            # ── Page 2: mean acc-magnitude profile per type ────────────────
            fig, axes = plt.subplots(2, 2, figsize=(16, 10))
            axes = axes.ravel()
            for ci, lbl in enumerate(_LABEL_ORDER):
                ax = axes[ci]
                mask = label_arr == lbl
                subset = [cycles[i] for i in range(len(cycles)) if mask[i]]
                if not subset:
                    ax.set_title(f"{lbl} — empty")
                    continue
                target_len = max(int(np.median([len(c) for c in subset])), 10)
                profiles = []
                for cyc in subset[:30]:
                    mag = np.sqrt(
                        cyc["acc_x"] ** 2 + cyc["acc_y"] ** 2 + cyc["acc_z"] ** 2
                    ).values.astype(np.float64)
                    if len(mag) < 5:
                        continue
                    profiles.append(
                        np.interp(
                            np.linspace(0, 1, target_len),
                            np.linspace(0, 1, len(mag)),
                            mag,
                        )
                    )
                if profiles:
                    mean_p = np.mean(profiles, axis=0)
                    std_p = np.std(profiles, axis=0)
                    t = np.linspace(0, target_len / fs, target_len)
                    ax.plot(t, mean_p, color=colors[ci % len(colors)], linewidth=2)
                    ax.fill_between(
                        t, mean_p - std_p, mean_p + std_p,
                        alpha=0.2, color=colors[ci % len(colors)],
                    )
                ax.set_title(f"{lbl} — n={int(sum(mask))}", fontsize=10)
                ax.set_xlabel("Time (s)")
                ax.set_ylabel("|acc| (g)")
            fig.suptitle("Mean acc-magnitude profile per movement type", fontsize=13)
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)

            # ── Page 3: PCA scatter coloured by movement type ──────────────
            X_s = StandardScaler().fit_transform(X.values)
            pca = PCA(n_components=2)
            comp = pca.fit_transform(X_s)
            fig, ax = plt.subplots(figsize=(9, 7))
            for ci, lbl in enumerate(_LABEL_ORDER):
                mask = label_arr == lbl
                ax.scatter(
                    comp[mask, 0], comp[mask, 1],
                    label=f"{lbl} (n={int(sum(mask))})", alpha=0.7, s=30,
                    color=colors[ci % len(colors)],
                )
            ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.1%})")
            ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.1%})")
            ax.set_title("PCA — movement types (rule-based)")
            ax.legend()
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)

        logger.info("Movement type inspection PDF saved to %s", output_path)
