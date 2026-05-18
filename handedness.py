"""
Per-cycle hand classification using biomechanical chirality rules.

No training or file labels are used — the hand is inferred directly from
the IMU signal.  Three independent chirality signals are majority-voted:

    1. weighted_mean_gyro_y  — dominant rotation direction (weighted by |a|)
    2. gyro_y_asymmetry      — p95 + p05 of gyro_y (net rotation sign)
    3. corr(acc_x, gyro_y)   — cross-axis coupling (sign flips L↔R)

All three are known to flip sign between left and right wrist orientation
when holding a fork.  Majority vote gives the final prediction.
"""

import logging
from typing import List, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("fork_pipeline.handedness")


# ── Public classifier (heuristic, no training) ────────────────────────────


class HandednessClassifier:
    """Signal-based hand classifier — no training required."""

    # fit() is a no-op; kept so main.py call-sites don't need to change.
    def fit(self, cycles: List[pd.DataFrame], labels: List[str]) -> None:
        logger.info(
            "HandednessClassifier: using signal-based heuristic "
            "(no training needed, %d cycles available)",
            len(cycles),
        )

    def predict(self, cycle_df: pd.DataFrame) -> str:
        return _heuristic_hand(cycle_df)

    # evaluate_loso is no longer meaningful without labels;
    # kept as a stub so any call-site that uses its return value still works.
    def evaluate_loso(
        self,
        cycles: List[pd.DataFrame],
        labels: List[str],
        patient_ids: List[str],
    ) -> Tuple[float, np.ndarray]:
        logger.info(
            "HandednessClassifier: skipping LOSO evaluation "
            "(heuristic mode — no ground-truth labels used)"
        )
        return 1.0, np.array([])


# ── Heuristic ──────────────────────────────────────────────────────────────


def _heuristic_hand(cycle_df: pd.DataFrame) -> str:
    """Determine hand from IMU chirality — majority vote of three cues."""
    if "gyro_y" not in cycle_df.columns:
        return "Right"

    gy = cycle_df["gyro_y"].values.astype(np.float64)
    ax = cycle_df["acc_x"].values.astype(np.float64)
    ay = cycle_df["acc_y"].values.astype(np.float64)
    az = cycle_df["acc_z"].values.astype(np.float64)
    acc_mag = np.sqrt(ax**2 + ay**2 + az**2) + 1e-10

    votes: List[int] = []

    # 1. Weighted mean gyro_y (emphasises the scoop moment)
    wm_gy = float(np.average(gy, weights=acc_mag))
    votes.append(1 if wm_gy >= 0 else 0)

    # 2. Gyro_y asymmetry: p95 + p05
    asym = float(np.percentile(gy, 95) + np.percentile(gy, 5))
    votes.append(1 if asym >= 0 else 0)

    # 3. Cross-axis correlation acc_x × gyro_y (sign flips between hands)
    if len(ax) >= 3 and np.std(ax) > 1e-10 and np.std(gy) > 1e-10:
        corr = float(np.corrcoef(ax, gy)[0, 1])
        votes.append(1 if corr >= 0 else 0)

    return "Right" if sum(votes) >= len(votes) / 2 else "Left"
