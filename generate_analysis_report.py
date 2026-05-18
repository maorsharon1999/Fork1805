"""
Generates a PDF report of the log analysis for the Fork ET Detection Pipeline run (2026-04-22).
Run with: python generate_analysis_report.py
"""

import os
from datetime import datetime
from fpdf import FPDF

OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "output", "figures",
    "log_analysis_2026-04-22.pdf",
)

MARGIN = 15
PAGE_W = 210 - 2 * MARGIN  # A4 usable width mm

# -- Colour palette ----------------------------------------------------------
C_DARK_BLUE   = (30,  30,  80)
C_MID_BLUE    = (50,  50, 160)
C_RED         = (180,  30,  30)
C_ORANGE      = (200, 100,   0)
C_GREEN       = ( 20, 120,  40)
C_GREY_TEXT   = (100, 100, 100)
C_BLACK       = (  0,   0,   0)
C_WHITE       = (255, 255, 255)
C_HDR_BG      = ( 50,  50,  80)
C_ROW_ALT     = (235, 235, 245)
C_ROW_WHITE   = (255, 255, 255)
C_WARN_BG     = (255, 240, 220)
C_CRIT_BG     = (255, 225, 225)
C_OK_BG       = (220, 245, 225)


class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*C_GREY_TEXT)
        self.cell(0, 6, "Fork ET Detection Pipeline - Log Analysis Report (2026-04-22)", align="R")
        self.ln(4)
        self.set_draw_color(*C_MID_BLUE)
        self.set_line_width(0.3)
        self.line(MARGIN, self.get_y(), 210 - MARGIN, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*C_GREY_TEXT)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    # -- Section title --------------------------------------------------------
    def section_title(self, text, level=1):
        self.ln(4)
        if level == 1:
            self.set_font("Helvetica", "B", 14)
            self.set_text_color(*C_DARK_BLUE)
            self.cell(0, 9, text, ln=True)
            self.set_draw_color(*C_MID_BLUE)
            self.set_line_width(0.6)
            self.line(MARGIN, self.get_y(), 210 - MARGIN, self.get_y())
        else:
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(*C_DARK_BLUE)
            self.cell(0, 7, text, ln=True)
            self.set_draw_color(180, 180, 200)
            self.set_line_width(0.3)
            self.line(MARGIN, self.get_y(), 210 - MARGIN, self.get_y())
        self.ln(3)
        self.set_text_color(*C_BLACK)

    # -- Body text ------------------------------------------------------------
    def body(self, text, indent=0):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*C_BLACK)
        self.set_x(MARGIN + indent)
        self.multi_cell(PAGE_W - indent, 5.2, text)
        self.ln(1)

    def bold_inline(self, label, value, indent=0):
        self.set_x(MARGIN + indent)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*C_BLACK)
        self.cell(0, 6, f"{label}  ", ln=False)
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, value, ln=True)

    # -- Coloured callout box -------------------------------------------------
    def callout(self, text, kind="warning"):
        colours = {
            "critical": (C_CRIT_BG,  C_RED),
            "warning":  (C_WARN_BG,  C_ORANGE),
            "ok":       (C_OK_BG,    C_GREEN),
        }
        bg, fg = colours.get(kind, (C_WARN_BG, C_ORANGE))
        self.set_fill_color(*bg)
        self.set_draw_color(*fg)
        self.set_line_width(0.4)
        x0 = MARGIN
        y0 = self.get_y()
        self.set_x(x0)
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(*fg)
        self.multi_cell(PAGE_W, 5.5, text, border=1, fill=True)
        self.set_text_color(*C_BLACK)
        self.ln(2)

    # -- Generic table --------------------------------------------------------
    def draw_table(self, headers, rows, col_widths=None, row_colours=None):
        if col_widths is None:
            col_widths = [PAGE_W / len(headers)] * len(headers)

        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(*C_HDR_BG)
        self.set_text_color(*C_WHITE)
        for w, h in zip(col_widths, headers):
            self.cell(w, 7, h, border=1, align="C", fill=True)
        self.ln()

        self.set_font("Helvetica", "", 9)
        self.set_text_color(*C_BLACK)
        for i, row in enumerate(rows):
            if row_colours and row_colours[i]:
                self.set_fill_color(*row_colours[i])
                fill = True
            elif i % 2 == 0:
                self.set_fill_color(*C_ROW_WHITE)
                fill = True
            else:
                self.set_fill_color(*C_ROW_ALT)
                fill = True
            for w, val in zip(col_widths, row):
                self.cell(w, 6, str(val), border=1, align="C", fill=fill)
            self.ln()
        self.ln(2)


# ============================================================================
# BUILD PDF
# ============================================================================

def build():
    pdf = PDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_left_margin(MARGIN)
    pdf.set_right_margin(MARGIN)

    # -- TITLE PAGE ------------------------------------------------------------
    pdf.add_page()
    pdf.ln(16)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(*C_DARK_BLUE)
    pdf.cell(0, 14, "Fork ET Detection Pipeline", ln=True, align="C")
    pdf.set_font("Helvetica", "B", 17)
    pdf.cell(0, 10, "Execution Log Analysis Report", ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*C_GREY_TEXT)
    pdf.cell(0, 7, f"Run date: 22 April 2026   |   Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}", ln=True, align="C")
    pdf.ln(14)

    # Summary box
    pdf.set_fill_color(240, 242, 255)
    pdf.set_draw_color(*C_MID_BLUE)
    pdf.set_line_width(0.5)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(*C_BLACK)
    summary_lines = [
        "Participants scanned: 36 files / 25 patients  (ET=23, Control=10)",
        "Cycle records collected: 410 from 24 patients",
        "Feature matrix after CRF join: 381 segments x 221 columns",
        "Cross-validation: Leave-One-Subject-Out (LOSO)",
        "Best local-score regression: GradientBoosting  R2=0.677  Pearson r=0.848",
        "Best global-score regression: Lasso  R2=0.725  Pearson r=0.887",
        "Best patient-level classifier: LogisticRegression  Sens=0.643  Spec=0.800  AUC=0.679",
        "Critical issues identified: 8   |   Issues to fix before publication: 3 P1 + 3 P2 + 3 P3",
    ]
    for line in summary_lines:
        pdf.set_x(MARGIN + 4)
        pdf.cell(PAGE_W - 8, 7, line, ln=True)
    pdf.ln(10)

    # -- SECTION 1: STAGE 1 DATA INVENTORY ------------------------------------
    pdf.section_title("1.  Stage 1 - Data Inventory & CRF Quality")

    pdf.body(
        "The scanner found 36 Fork CSV files across 25 patients (ET=23, Control=10). "
        "Because some participants have both a Fork1 and a Fork2 device, the file count "
        "exceeds the patient count. The CRF Excel was parsed successfully for 29 ET patients, "
        "but only 23 have matching sensor directories - 6 ET patients are silent exclusions "
        "with CRF records but no IMU data. These must be documented explicitly in any "
        "participant flow diagram."
    )

    pdf.section_title("1a.  Critical CRF Quality Problems", level=2)

    pdf.callout(
        "[CRITICAL] Age = None for every patient.\n"
        "CRF_COL_AGE = 3 points at the wrong column (likely a header or non-numeric identifier). "
        "Every patient falls back to the hardcoded default age = 65.0, making 'age' a constant "
        "and therefore a completely uninformative feature in every model.",
        kind="critical",
    )

    pdf.callout(
        "[CRITICAL] Gender = 0.0 for every patient.\n"
        "Either all 29 ET patients are female, or the Hebrew cell values (zain/nun letters) "
        "are not matching the gender mapping due to encoding or whitespace differences. "
        "Both age and gender features carry zero information in this run.",
        kind="critical",
    )

    pdf.body(
        "Patients 001, 002, 004 have all four fork-score columns (rt_scoop, lf_scoop, "
        "rt_stab, lf_stab) as NaN despite having subtotal_b_ext = 0.0. A zero Subtotal B "
        "Extended for a confirmed ET patient is clinically implausible and suggests incomplete "
        "CRF entry for these early participants. All three are correctly skipped in Stage 5 "
        "and are excluded from every ML stage."
    )

    pdf.body(
        "Patient 024 has valid fork scores but subtotal_b_ext = NaN. This patient participates "
        "in the local-score regression but is excluded from the global-score regression. "
        "The missing cell should be recovered from the source CRF document."
    )

    # -- SECTION 2: STAGE 2-4a ------------------------------------------------
    pdf.section_title("2.  Stages 2-4a - Preprocessing & Segmentation")

    pdf.body(
        "410 valid eating cycles were collected from 24 patients. One patient was lost "
        "between the initial 25 (with sensor files) and the final 24 (with valid cycles) - "
        "likely a participant whose recordings produced no segments passing the quality filter "
        "(tilt > 0.2 g AND peak/mean jerk >= 1.5)."
    )

    pdf.callout(
        "[WARNING] ET_021: corrupt CSV - 'No columns to parse from file'.\n"
        "File: Fork1_2024-05-16_10-52-05_021 ET part 3.csv\n"
        "The file is empty or contains only whitespace. ET_021 may have other valid recordings "
        "but this session is permanently lost. Archive or delete the file and verify ET_021's "
        "remaining data.",
        kind="warning",
    )

    pdf.body(
        "Four 'Fork_' (ambiguous hand) files were accepted with the default hand = Right "
        "(INCLUDE_AMBIGUOUS_FORK = True, FORK_DEFAULT_HAND = 'Right'). If any of these "
        "patients are left-dominant, their CRF tremor scores will be looked up for the wrong "
        "hand, silently corrupting both the target variable and the bucket assignment."
    )

    pdf.body(
        "ET_020 appearing between Control records in the signal log is expected - this patient "
        "shares a combined folder named 'Control-003 and ET-020', which _parse_folder_name() "
        "correctly decomposes into two separate records."
    )

    # -- SECTION 3: HANDEDNESS ------------------------------------------------
    pdf.section_title("3.  Stage 4b - Handedness Classifier")

    pdf.callout(
        "[CRITICAL] Handedness LOSO accuracy = 0.659 (target >= 0.900).\n"
        "Trained on 410 cycles: 378 Right (92%), 32 Left (8%).\n"
        "Confusion matrix:  Left predicted correctly: 15/32 = 46.9%  |  Right correctly: 255/378 = 67.5%\n"
        "The classifier is broken for the Left class. 123 of 132 Left cycles are classified as Right. "
        "Any ambiguous Fork_ file belonging to a left-dominant patient will be systematically mislabeled, "
        "causing wrong CRF cell lookups and corrupted regression targets.",
        kind="critical",
    )

    pdf.body(
        "Root cause: extreme class imbalance (92%/8%). Despite class_weight='balanced', "
        "LOSO leaves too few Left-hand examples per training fold to learn reliable chirality features. "
        "The heuristic fallback (gyro_y p95/p05 sign) is used for ambiguous files - "
        "this is no worse than the trained classifier given the current data."
    )

    pdf.body(
        "Short-term fix: trust only filename-derived labels (Fork1 = Right, Fork2 = Left); "
        "disable the classifier entirely for Fork_ files or exclude them. "
        "Long-term fix: collect substantially more Fork2 (Left-hand) recordings."
    )

    # -- SECTION 4: GMM -------------------------------------------------------
    pdf.section_title("4.  Stage 4c - Movement-Type Clustering (GMM k=4)")

    pdf.body("Cluster distribution across 410 cycles:")

    pdf.draw_table(
        headers=["Cluster", "Label", "Cycles", "Share"],
        rows=[
            ["0", "scoop",    "70",  "17.1%"],
            ["1", "fragment",  "8",   "2.0%"],
            ["2", "other",   "280",  "68.3%"],
            ["3", "stab",     "52",  "12.7%"],
        ],
        col_widths=[25, 45, 30, 30],
        row_colours=[None, None, (255, 230, 230), None],
    )

    pdf.callout(
        "[WARNING] Cluster 2 ('other') captures 68% of all cycles.\n"
        "Only 'scoop' and 'stab' labeled cycles feed into bucketed regression. "
        "With 68% of cycles excluded, the bucket models operate on a small minority of the data. "
        "Two explanations: (a) the label map is wrong and cluster 2 contains genuine eating cycles "
        "that should be split; or (b) the protocol produces many non-eating movements. "
        "Action required: re-inspect cluster_inspection.pdf and verify the label assignment "
        "before treating any bucketed results as final.",
        kind="warning",
    )

    pdf.body(
        "The fragment cluster (n=8, 2%) is unusually sparse. The cycle-quality filter in "
        "classify_cycle_quality() removes most fragments before they reach the GMM, leaving "
        "almost no fragment-class examples. Consider whether the GMM still needs a dedicated "
        "fragment component or whether k=3 (scoop, stab, other) would be more stable."
    )

    # -- SECTION 5: FEATURE EXTRACTION ----------------------------------------
    pdf.section_title("5.  Stage 5 - Feature Extraction")

    pdf.body(
        "Feature matrix: 381 rows x 221 columns (PER_SEGMENT=True). "
        "Each row is one eating cycle; 3 patients excluded due to missing CRF scores (001, 002, 004). "
        "The raw feature count of ~196 (221 minus metadata columns) versus 24 patients is extreme - "
        "the features-to-patients ratio is ~8:1, which is why LOSO is mandatory and results carry "
        "wide confidence intervals. RFE within each fold reduces to 25 features, which is the "
        "correct approach to prevent leakage."
    )

    # -- SECTION 6: REGRESSION ------------------------------------------------
    pdf.add_page()
    pdf.section_title("6.  Stage 6 - Regression Results (ET only, LOSO CV)")

    pdf.section_title("6a.  Local Score (Fork Feeding, scale 0-4)", level=2)

    pdf.draw_table(
        headers=["Model", "MAE", "R²", "Pearson r"],
        rows=[
            ["LinearRegression",  "0.538", "0.618", "0.819"],
            ["Ridge",             "0.536", "0.628", "0.828"],
            ["Lasso",             "0.566", "0.611", "0.844"],
            ["RandomForest",      "0.566", "0.594", "0.796"],
            ["GradientBoosting",  "0.500", "0.677", "0.848"],
            ["XGBoost",           "0.498", "0.623", "0.808"],
        ],
        col_widths=[55, 30, 30, 35],
        row_colours=[None, None, None, None, (220, 245, 225), None],
    )

    pdf.callout(
        "[POSITIVE] GradientBoosting is the best local-score model: R2=0.677, Pearson r=0.848.\n"
        "This means the IMU signal explains ~68% of variance in the clinician-rated fork-feeding "
        "tremor score under LOSO CV. MAE ~ 0.5 on a 0-4 scale is roughly one ordinal grade - "
        "clinically meaningful as a screening tool.",
        kind="ok",
    )

    pdf.body(
        "RFE selected 25 gyroscope-dominated features: gyro_x/y/z_ptp, gyro jerk statistics, "
        "gyro CWT energy ratio (4-12 Hz), gyro spectral centroid/rolloff, gyro weighted mean/median "
        "frequency, and gyro peak-to-peak interval. This is biologically coherent - ET is a kinetic "
        "action tremor manifesting as rotational wrist/forearm oscillation. Only 6 of 25 selected "
        "features are accelerometer-derived."
    )

    pdf.section_title("6b.  Global Score (Subtotal B Extended, scale ~3-41)", level=2)

    pdf.draw_table(
        headers=["Model", "MAE", "R²", "Pearson r"],
        rows=[
            ["LinearRegression",  "4.566", "0.682", "0.862"],
            ["Ridge",             "4.464", "0.697", "0.870"],
            ["Lasso",             "4.260", "0.725", "0.887"],
            ["RandomForest",      "5.186", "0.583", "0.842"],
            ["GradientBoosting",  "5.162", "0.582", "0.835"],
            ["XGBoost",           "5.637", "0.488", "0.763"],
        ],
        col_widths=[55, 30, 30, 35],
        row_colours=[None, None, (220, 245, 225), None, None, None],
    )

    pdf.callout(
        "[POSITIVE] Lasso is the best global-score model: R2=0.725, Pearson r=0.887.\n"
        "Linear models consistently outperform tree-based models for the global score - "
        "suggesting a more linear feature-score relationship, and that tree models overfit "
        "with only ~14 ET patients per fold. MAE=4.26 on a 38-point range is ~11% error.",
        kind="ok",
    )

    # -- SECTION 7: BUCKETED REGRESSION ---------------------------------------
    pdf.section_title("7.  Stage 6b - Bucketed Regression (Hand x Movement Type)")

    pdf.section_title("7a.  Sparsity Report", level=2)

    pdf.draw_table(
        headers=["Hand", "Movement", "Cycles", "Patients", "Status"],
        rows=[
            ["Left",  "fragment",  "2",   "2",  "Skipped (<5 patients)"],
            ["Left",  "other",    "14",   "4",  "Skipped (<5 patients)"],
            ["Left",  "scoop",     "8",   "4",  "SKIPPED - too sparse"],
            ["Left",  "stab",      "8",   "2",  "SKIPPED - too sparse"],
            ["Right", "fragment",  "3",   "3",  "Skipped (<5 patients)"],
            ["Right", "other",   "181",  "18",  "Not a regression target"],
            ["Right", "scoop",    "46",  "16",  "Run - results valid"],
            ["Right", "stab",     "31",   "9",  "Run - results INVALID (R2<0)"],
        ],
        col_widths=[20, 28, 22, 25, 55],
        row_colours=[
            (255, 230, 230), (255, 230, 230), (255, 200, 200), (255, 200, 200),
            (255, 230, 230), (240, 240, 240), (220, 245, 225), (255, 200, 200),
        ],
    )

    pdf.callout(
        "[CRITICAL] All left-hand buckets skipped. No regression analysis exists for left-hand "
        "tremor. For bilateral and left-dominant ET patients this is a fundamental data gap.",
        kind="critical",
    )

    pdf.section_title("7b.  Right_scoop (16 patients, 46 cycles)", level=2)

    pdf.draw_table(
        headers=["Model", "MAE", "R²", "Pearson r"],
        rows=[
            ["Ridge",            "0.499", "0.632", "0.807"],
            ["RandomForest",     "0.751", "0.261", "0.566"],
            ["GradientBoosting", "0.732", "0.244", "0.584"],
            ["XGBoost",          "0.840", "0.050", "0.502"],
        ],
        col_widths=[55, 30, 30, 35],
        row_colours=[(220, 245, 225), None, None, None],
    )

    pdf.body(
        "Ridge dominates tree models by a large margin (R2=0.632 vs 0.050-0.261). "
        "With only 16 patients in LOSO, each training fold has 15 patients - too small "
        "for a 100-tree forest with RFE. Ridge's L2 regularization provides the right "
        "inductive bias for this small-N setting. Selected features: gyro_x_jerk_max, "
        "gyro_mag_rms, acc_x_cwt_energy_mean, acc_z_cwt_energy_mean, acc_z_cwt_energy_max."
    )

    pdf.section_title("7c.  Right_stab (9 patients, 31 cycles) - ALL MODELS FAILED", level=2)

    pdf.draw_table(
        headers=["Model", "MAE", "R²", "Pearson r"],
        rows=[
            ["Ridge",            "1.225", "-0.748",  "0.141"],
            ["RandomForest",     "1.138", "-0.539", "-0.246"],
            ["GradientBoosting", "1.309", "-0.858", "-0.322"],
            ["XGBoost",          "1.458", "-1.145", "-0.345"],
        ],
        col_widths=[55, 30, 30, 35],
        row_colours=[(255, 200, 200)] * 4,
    )

    pdf.callout(
        "[CRITICAL] Right_stab: all 4 models produce negative R2 (worst: -1.145). "
        "Every model is worse than predicting the mean. Three models produce negative Pearson r, "
        "meaning predictions are anti-correlated with the true stab scores.\n\n"
        "Root causes: (1) Only 9 patients - LOSO trains on 8, leaving near-zero degrees of freedom. "
        "(2) Stab score variance may be low within these 9 patients. "
        "(3) GMM 'stab' label may be noisy (cluster 3, n=52, only 12.7% of cycles).\n\n"
        "Action: Do NOT report these results as meaningful findings. Label as 'insufficient data' "
        "in all reports. Collect more stab recordings or merge stab into the overall regression.",
        kind="critical",
    )

    # -- SECTION 8: CLASSIFICATION ---------------------------------------------
    pdf.add_page()
    pdf.section_title("8.  Stage 7 - Classification (ET vs Control)")

    pdf.section_title("8a.  Patient-Level Results (clinically honest, N=24)", level=2)

    pdf.draw_table(
        headers=["Model", "Sensitivity", "Specificity", "AUC", "N"],
        rows=[
            ["LogisticRegression", "0.643", "0.800", "0.679", "24"],
            ["SVC",                "0.357", "1.000", "0.664", "24"],
            ["XGBoost",            "0.429", "0.900", "0.571", "24"],
            ["RandomForest",       "0.429", "0.800", "0.571", "24"],
            ["GradientBoosting",   "0.286", "0.800", "0.557", "24"],
        ],
        col_widths=[55, 30, 30, 25, 15],
        row_colours=[(220, 245, 225), None, None, None, None],
    )

    pdf.callout(
        "[POSITIVE] LogisticRegression is the best patient-level classifier: "
        "Sensitivity=0.643, Specificity=0.800, AUC=0.679 at N=24.\n"
        "SVC achieves Specificity=1.000 by predicting nearly everyone as Control "
        "(Sensitivity=0.357 = only ~5 of 14 ET patients correctly identified).",
        kind="ok",
    )

    pdf.body(
        "AUC range 0.557-0.679 across patient-level models. With N=24, the 95% confidence "
        "interval on AUC is approximately +-0.15 to +-0.20, meaning these values are not "
        "statistically distinguishable from each other or from chance (AUC=0.50). "
        "Statistical significance requires approximately 40-50 patients."
    )

    pdf.section_title("8b.  Segment-Level Youden's J Optimization", level=2)

    pdf.draw_table(
        headers=["Model", "Accuracy", "Sensitivity", "Specificity", "AUC", "J"],
        rows=[
            ["LogisticRegression", "0.709", "0.778", "0.477", "0.615", "0.255"],
            ["SVC",                "0.703", "0.730", "0.406", "0.649", "0.344"],
            ["RandomForest",       "0.630", "0.621", "0.343", "0.626", "0.280"],
            ["GradientBoosting",   "0.732", "0.836", "0.386", "0.580", "0.223"],
            ["XGBoost",            "0.688", "0.730", "0.545", "0.632", "0.276"],
        ],
        col_widths=[47, 28, 28, 28, 22, 18],
    )

    pdf.body(
        "All Youden J values (0.223-0.344) are low, reflecting that no classifier achieves "
        "strong simultaneous sensitivity and specificity at segment level. Specificity is "
        "consistently below 0.55 for the highest-sensitivity models, which is clinically "
        "insufficient for a screening tool."
    )

    pdf.section_title("8c.  Regress-then-Classify", level=2)

    pdf.draw_table(
        headers=["Mode", "Sensitivity", "Specificity", "AUC"],
        rows=[
            ["Fixed threshold=0.50 (segment)", "0.935", "0.068", "0.665"],
            ["Youden optimal (segment)",        "0.669", "0.670", "0.665"],
            ["Patient-level (Spec>=80%)",       "0.286", "0.800", "0.643"],
        ],
        col_widths=[70, 32, 32, 22],
        row_colours=[(255, 200, 200), (220, 245, 225), None],
    )

    pdf.callout(
        "[WARNING] Fixed threshold=0.50 produces Specificity=0.068 - clinically useless. "
        "The threshold is far too low: Controls are assigned score=0 and ET patients have "
        "scores well above 0.5. Do NOT report this result.\n\n"
        "[POSITIVE] Youden-optimal threshold=9.044 gives the most balanced segment-level "
        "result of all approaches tested: Sensitivity=0.669, Specificity=0.670, AUC=0.665.",
        kind="warning",
    )

    # -- SECTION 9: SHAP ------------------------------------------------------
    pdf.section_title("9.  Stage 7d - SHAP Feature Importance")

    pdf.section_title("9a.  Regression Top 10 Features", level=2)

    pdf.draw_table(
        headers=["Rank", "Feature", "Mean |SHAP|", "Interpretation"],
        rows=[
            ["1",  "gyro_y_cwt_energy_ratio",  "0.2510", "ET tremor power (4-12 Hz) / total gyro energy"],
            ["2",  "gyro_p2p_mean",             "0.1736", "Mean peak-to-peak interval of gyro magnitude"],
            ["3",  "gyro_mag_ptp",              "0.1090", "Gyro magnitude peak-to-peak amplitude"],
            ["4",  "gyro_z_ptp",                "0.0874", "Z-axis gyro peak-to-peak"],
            ["5",  "gyro_x_jerk_max",           "0.0863", "Max rotational jerk (X-axis)"],
            ["6",  "gyro_wt_mean_freq",         "0.0739", "Weighted mean frequency of gyro magnitude"],
            ["7",  "gyro_y_jerk_mean",          "0.0665", "Mean rotational jerk (Y-axis)"],
            ["8",  "acc_x_cwt_energy_ratio",    "0.0651", "Acc ET-band CWT energy ratio"],
            ["9",  "gyro_x_ptp",                "0.0465", "X-axis gyro peak-to-peak"],
            ["10", "corr_acc_z_gyro_z",         "0.0445", "Z-axis acc-gyro coupling"],
        ],
        col_widths=[13, 60, 28, 55],
    )

    pdf.body(
        "9 of 10 top regression features are gyroscope-derived. This is biologically coherent: "
        "ET is a kinetic action tremor manifesting as rotational wrist/forearm oscillation. "
        "The dominant feature (gyro_y_cwt_energy_ratio) directly quantifies the fraction of "
        "rotational energy in the clinical ET tremor band (4-12 Hz) using Morlet CWT - "
        "the most principled tremor-specific measure in the feature set."
    )

    pdf.section_title("9b.  Classification Top 10 Features", level=2)

    pdf.draw_table(
        headers=["Rank", "Feature", "Mean |SHAP|", "Interpretation"],
        rows=[
            ["1",  "gyro_wt_mean_freq",    "0.8067", "Weighted mean frequency of gyro motion"],
            ["2",  "gyro_x_spec_rolloff",  "0.6167", "Spectral rolloff frequency (X gyro)"],
            ["3",  "corr_acc_y_acc_z",     "0.5726", "Y-Z accelerometer coupling (arm orientation)"],
            ["4",  "acc_z_spec_rolloff",   "0.4498", "Spectral rolloff (Z acc)"],
            ["5",  "acc_y_power_4_12hz",   "0.4080", "ET-band power ratio (Y acc)"],
            ["6",  "acc_y_rms",            "0.3917", "RMS acceleration (Y-axis)"],
            ["7",  "acc_x_power_4_12hz",   "0.3873", "ET-band power ratio (X acc)"],
            ["8",  "acc_x_cwt_energy_std", "0.2901", "CWT energy variability (X acc)"],
            ["9",  "acc_wt_mean_freq",     "0.2679", "Weighted mean frequency of acc magnitude"],
            ["10", "acc_p2p_mean",         "0.2582", "Mean peak-to-peak interval (acc)"],
        ],
        col_widths=[13, 55, 28, 60],
    )

    pdf.body(
        "Classification features are more evenly split between accelerometer and gyroscope, "
        "dominated by spectral frequency descriptors. ET vs Control discrimination relies on "
        "the frequency distribution of motion (where energy is concentrated in the spectrum), "
        "not just the absolute ET-band power. This makes sense: Controls also produce arm "
        "motion during eating - the discriminative signal is the spectral signature difference."
    )

    # -- SECTION 10: PRIORITY TABLE --------------------------------------------
    pdf.add_page()
    pdf.section_title("10.  Prioritised Issues & Recommended Actions")

    pdf.draw_table(
        headers=["Priority", "Issue", "Impact", "Action"],
        rows=[
            ["P1", "CRF_COL_AGE wrong - age=None all patients",
             "Age uninformative in all models",
             "Fix column index in config.py; re-run"],
            ["P1", "Gender=0.0 all patients - mapping failure",
             "Gender uninformative in all models",
             "Log raw gender cell; fix Hebrew mapping"],
            ["P1", "Right_stab: all R2<0 (worst -1.145)",
             "Anti-predictive; must not be reported",
             "Label 'insufficient data'; collect more stab data"],
            ["P2", "Handedness accuracy 0.659 vs target 0.900",
             "Left-hand cycle labels unreliable",
             "Collect more Fork2 data; disable classifier for Fork_ files"],
            ["P2", "Left_scoop (4 pts) and Left_stab (2 pts) skipped",
             "No left-hand bucket analysis",
             "Structural gap; flag in report; collect more left-hand data"],
            ["P2", "GMM cluster 'other' = 68% of all cycles",
             "Most data excluded from bucket regression",
             "Re-inspect cluster_inspection.pdf; verify label map"],
            ["P3", "ET_021 corrupt CSV (empty file)",
             "Session data permanently lost",
             "Archive file; verify ET_021 has other valid recordings"],
            ["P3", "Patient 024 missing subtotal_b_ext",
             "Excluded from global score regression",
             "Recover missing CRF value from source document"],
            ["P3", "RTC fixed threshold=0.50 gives Spec=0.068",
             "Misleading result in clinical report",
             "Remove fixed-threshold result; report Youden-optimal only"],
        ],
        col_widths=[16, 58, 52, 54],
        row_colours=[
            (255, 200, 200), (255, 200, 200), (255, 200, 200),
            (255, 230, 200), (255, 230, 200), (255, 230, 200),
            (255, 245, 220), (255, 245, 220), (255, 245, 220),
        ],
    )

    # -- SECTION 11: POSITIVE SUMMARY -----------------------------------------
    pdf.section_title("11.  Key Positive Findings")

    positives = [
        ("Local score regression",
         "GradientBoosting R2=0.677, Pearson r=0.848 under LOSO CV. "
         "The IMU signal explains ~68% of variance in clinician-rated fork-feeding tremor severity."),
        ("Global score regression",
         "Lasso R2=0.725, Pearson r=0.887. Linear models outperform tree models - "
         "the global score has a near-linear relationship with gyro spectral features."),
        ("Right_scoop bucket",
         "Ridge R2=0.632, Pearson r=0.807 with 16 patients. "
         "The strongest single-bucket result and the most clinically targeted finding."),
        ("Patient-level classification",
         "LogisticRegression achieves Sensitivity=0.643 at Specificity=0.800 (N=24). "
         "Above-chance discrimination with an honest leave-one-subject-out evaluation."),
        ("SHAP interpretability",
         "gyro_y_cwt_energy_ratio is the single most important regression feature (SHAP=0.251). "
         "Gyroscope-dominated feature sets are clinically coherent for a kinetic rotational tremor."),
        ("Regress-then-classify (Youden)",
         "Youden-optimal threshold gives the most balanced segment-level result: "
         "Sensitivity=0.669, Specificity=0.670, AUC=0.665."),
    ]

    for title, text in positives:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*C_GREEN)
        pdf.cell(0, 6, f"  {title}", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*C_BLACK)
        pdf.set_x(MARGIN + 4)
        pdf.multi_cell(PAGE_W - 4, 5.2, text)
        pdf.ln(1)

    # -- FOOTER NOTE -----------------------------------------------------------
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*C_GREY_TEXT)
    pdf.multi_cell(
        PAGE_W, 5,
        "This document was generated automatically from the execution log of the "
        "Fork ET Detection Pipeline run on 2026-04-22. All metrics reflect LOSO CV "
        "on N=24 patients (ET=~14 with valid CRF, Control=10). Confidence intervals "
        "are wide at this sample size; findings should be treated as preliminary "
        "until validated on an independent cohort.",
    )

    pdf.output(OUTPUT_PATH)
    print(f"PDF saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    build()
