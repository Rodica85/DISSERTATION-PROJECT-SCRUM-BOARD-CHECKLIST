"""Statistical analysis script for TravelAssistantAI questionnaire data.

Generates descriptive statistics, box plots, and runs statistical tests
(Kruskal-Wallis) comparing the three communication tones.

Usage:
    python analysis.py
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "questionnaire_responses.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "analysis_output")

QUESTION_LABELS = {
    "q1_understanding": "Q1: Understood concerns",
    "q2_care": "Q2: Cared about helping",
    "q3_trust_info": "Q3: Trust with information",
    "q4_human_like": "Q4: Human-like responses",
    "q5_privacy_confidence": "Q5: Privacy confidence",
    "q6_satisfaction": "Q6: Overall satisfaction",
}

QUESTION_COLS = list(QUESTION_LABELS.keys())


def load_data():
    """Load and validate questionnaire data."""
    df = pd.read_csv(CSV_PATH)
    for col in QUESTION_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=QUESTION_COLS)
    return df


def descriptive_stats(df):
    """Print descriptive statistics per tone."""
    print("=" * 70)
    print("DESCRIPTIVE STATISTICS BY TONE")
    print("=" * 70)

    for tone in sorted(df["bot_tone"].unique()):
        subset = df[df["bot_tone"] == tone]
        print(f"\n--- {tone} (n={len(subset)}) ---")
        for col, label in QUESTION_LABELS.items():
            values = subset[col]
            print(f"  {label}: mean={values.mean():.2f}, median={values.median():.1f}, std={values.std():.2f}")

    print(f"\n--- Overall (N={len(df)}) ---")
    for col, label in QUESTION_LABELS.items():
        values = df[col]
        print(f"  {label}: mean={values.mean():.2f}, median={values.median():.1f}, std={values.std():.2f}")


def kruskal_wallis_tests(df):
    """Run Kruskal-Wallis H-test for each question across tones."""
    print("\n" + "=" * 70)
    print("KRUSKAL-WALLIS H-TEST (comparing tones)")
    print("=" * 70)

    tones = sorted(df["bot_tone"].unique())
    for col, label in QUESTION_LABELS.items():
        groups = [df[df["bot_tone"] == t][col].values for t in tones]
        # Need at least 2 groups with data
        groups = [g for g in groups if len(g) > 0]
        if len(groups) < 2:
            print(f"\n{label}: Not enough groups for comparison")
            continue
        stat, p_value = stats.kruskal(*groups)
        sig = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "ns"
        print(f"\n{label}")
        print(f"  H={stat:.3f}, p={p_value:.4f} ({sig})")


def create_box_plots(df):
    """Generate box plots comparing tones for each question."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle("Questionnaire Responses by Bot Tone", fontsize=16, fontweight="bold")

    tone_order = ["Empathetic", "Neutral", "Non-Empathetic"]
    colors = {"Empathetic": "#4CAF50", "Neutral": "#2196F3", "Non-Empathetic": "#F44336"}

    for idx, (col, label) in enumerate(QUESTION_LABELS.items()):
        ax = axes[idx // 3][idx % 3]
        data_by_tone = [df[df["bot_tone"] == t][col].values for t in tone_order if t in df["bot_tone"].values]
        labels = [t for t in tone_order if t in df["bot_tone"].values]

        bp = ax.boxplot(data_by_tone, labels=labels, patch_artist=True, widths=0.6)
        for patch, tone in zip(bp["boxes"], labels):
            patch.set_facecolor(colors.get(tone, "#999999"))
            patch.set_alpha(0.7)

        ax.set_title(label, fontsize=11)
        ax.set_ylabel("Score (1-5)")
        ax.set_ylim(0.5, 5.5)
        ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    filepath = os.path.join(OUTPUT_DIR, "box_plots.png")
    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\nBox plots saved to: {filepath}")


def create_mean_bar_chart(df):
    """Generate grouped bar chart of mean scores per tone."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    tone_order = ["Empathetic", "Neutral", "Non-Empathetic"]
    colors = ["#4CAF50", "#2196F3", "#F44336"]

    means = df.groupby("bot_tone")[QUESTION_COLS].mean()

    fig, ax = plt.subplots(figsize=(12, 6))
    x = range(len(QUESTION_COLS))
    width = 0.25

    for i, tone in enumerate(tone_order):
        if tone in means.index:
            values = means.loc[tone, QUESTION_COLS].values
            offset = (i - 1) * width
            bars = ax.bar([xi + offset for xi in x], values, width, label=tone, color=colors[i], alpha=0.8)
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                        f"{val:.1f}", ha="center", va="bottom", fontsize=8)

    ax.set_xlabel("Question")
    ax.set_ylabel("Mean Score (1-5)")
    ax.set_title("Mean Questionnaire Scores by Bot Tone", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([QUESTION_LABELS[c] for c in QUESTION_COLS], rotation=30, ha="right", fontsize=9)
    ax.set_ylim(0, 5.5)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    filepath = os.path.join(OUTPUT_DIR, "mean_scores.png")
    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Mean score chart saved to: {filepath}")


def sample_size_report(df):
    """Print sample size summary."""
    print("\n" + "=" * 70)
    print("SAMPLE SIZE REPORT")
    print("=" * 70)
    counts = df["bot_tone"].value_counts()
    for tone, count in counts.items():
        status = "OK" if count >= 30 else "LOW (target: 30+)"
        print(f"  {tone}: {count} responses [{status}]")
    print(f"  Total: {len(df)} responses")
    if len(df) < 90:
        print(f"\n  WARNING: Total sample size ({len(df)}) is below recommended minimum (90).")
        print(f"  Need {90 - len(df)} more responses for adequate statistical power.")


def main():
    print("TravelAssistantAI - Questionnaire Analysis")
    print("=" * 70)

    df = load_data()
    if df.empty:
        print("No data found. Run experiments first.")
        return

    sample_size_report(df)
    descriptive_stats(df)
    kruskal_wallis_tests(df)
    create_box_plots(df)
    create_mean_bar_chart(df)

    print("\nAnalysis complete.")


if __name__ == "__main__":
    main()
