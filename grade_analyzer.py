"""
Grade Analyzer
--------------
Reads a CSV of student marks, calculates each student's total, letter grade
and grade point, prints a class summary and saves two charts.

Usage:
    python grade_analyzer.py sample_data/marks.csv
    python grade_analyzer.py sample_data/marks.csv --out my_results
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # save charts to files, no window needed
import matplotlib.pyplot as plt
import pandas as pd

# Maximum marks for each assessment (they add up to 100).
# Change these to match your own course.
ASSESSMENTS = {
    "attendance": 5,
    "assignment": 10,
    "quiz": 15,
    "mid": 30,
    "final": 40,
}

# (minimum total, letter grade, grade point), highest first.
GRADE_SCALE = [
    (90, "A", 4.00),
    (86, "A-", 3.67),
    (82, "B+", 3.33),
    (78, "B", 3.00),
    (74, "B-", 2.67),
    (70, "C+", 2.33),
    (66, "C", 2.00),
    (62, "C-", 1.67),
    (58, "D+", 1.33),
    (55, "D", 1.00),
    (0, "F", 0.00),
]
PASS_MARK = 55

# Chart colors
BAR_COLOR = "#2a78d6"
TEXT_COLOR = "#0b0b0b"
MUTED_COLOR = "#52514e"
GRID_COLOR = "#e4e3df"


def letter_grade(total):
    """Return (letter, grade point) for a total out of 100."""
    for minimum, letter, point in GRADE_SCALE:
        if total >= minimum:
            return letter, point
    return "F", 0.00


def load_marks(csv_path):
    """Read the CSV and fix common problems (blank, non-numeric or out-of-range marks)."""
    df = pd.read_csv(csv_path)

    required = ["student_id", "name", *ASSESSMENTS]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise SystemExit(f"Error: the CSV is missing column(s): {', '.join(missing)}")

    for column, max_marks in ASSESSMENTS.items():
        # Anything that isn't a number (e.g. "absent") becomes NaN
        df[column] = pd.to_numeric(df[column], errors="coerce")

        blanks = df[df[column].isna()]
        for _, row in blanks.iterrows():
            print(f"Warning: {row['student_id']} has no valid '{column}' mark, counted as 0.")
        df[column] = df[column].fillna(0)

        out_of_range = df[(df[column] < 0) | (df[column] > max_marks)]
        for _, row in out_of_range.iterrows():
            print(f"Warning: {row['student_id']} has {row[column]} in '{column}' "
                  f"(allowed 0-{max_marks}), clipped to the limit.")
        df[column] = df[column].clip(0, max_marks)

    return df


def add_results(df):
    """Add total, grade and grade_point columns."""
    df["total"] = df[list(ASSESSMENTS)].sum(axis=1)
    df["grade"] = df["total"].apply(lambda t: letter_grade(t)[0])
    df["grade_point"] = df["total"].apply(lambda t: letter_grade(t)[1])
    return df


def grade_counts(df):
    """Number of students per grade, in A..F order (grades nobody got show 0)."""
    order = [letter for _, letter, _ in GRADE_SCALE]
    return df["grade"].value_counts().reindex(order, fill_value=0)


def print_summary(df):
    totals = df["total"]
    n = len(df)
    passed = (totals >= PASS_MARK).sum()

    print("\n=== Class Summary ===")
    print(f"Students       : {n}")
    print(f"Average        : {totals.mean():.2f}")
    print(f"Median         : {totals.median():.2f}")
    print(f"Highest        : {totals.max():.2f}")
    print(f"Lowest         : {totals.min():.2f}")
    print(f"Std. deviation : {totals.std():.2f}")
    print(f"Pass rate      : {passed}/{n} ({passed / n:.0%})")

    print("\n=== Grade Distribution ===")
    for grade, count in grade_counts(df).items():
        print(f"{grade:<3} {'#' * count} {count}")

    # Which assessment did the class find hardest?
    print("\n=== Class Average per Assessment ===")
    for column, max_marks in ASSESSMENTS.items():
        print(f"{column:<11} {df[column].mean():5.2f} / {max_marks:<3} ({df[column].mean() / max_marks:.0%})")

    print("\n=== Top 5 Students ===")
    top = df.nlargest(5, "total")[["student_id", "name", "total", "grade"]]
    print(top.to_string(index=False))

    at_risk = df[df["total"] < PASS_MARK].sort_values("total")
    print(f"\n=== Students Below the Pass Mark ({PASS_MARK}) ===")
    if at_risk.empty:
        print("None")
    else:
        print(at_risk[["student_id", "name", "total"]].to_string(index=False))


def style_axes(ax, title, xlabel, ylabel):
    ax.set_title(title, loc="left", fontsize=13, color=TEXT_COLOR, pad=12)
    ax.set_xlabel(xlabel, color=MUTED_COLOR)
    ax.set_ylabel(ylabel, color=MUTED_COLOR)
    ax.tick_params(colors=MUTED_COLOR, length=0)
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(MUTED_COLOR)


def save_charts(df, out_dir):
    # 1. Bar chart: how many students got each grade
    counts = grade_counts(df)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(counts.index, counts.values, color=BAR_COLOR, width=0.6)
    for x, count in enumerate(counts.values):
        if count:
            ax.text(x, count + 0.15, str(count), ha="center", color=TEXT_COLOR)
    style_axes(ax, "Grade distribution", "Grade", "Number of students")
    fig.tight_layout()
    fig.savefig(out_dir / "grade_distribution.png", dpi=120)
    plt.close(fig)

    # 2. Histogram: spread of total marks, with the pass mark and class average
    fig, ax = plt.subplots(figsize=(8, 4.5))
    counts, _, _ = ax.hist(df["total"], bins=range(0, 105, 5), color=BAR_COLOR,
                           edgecolor="white", linewidth=2)
    top = counts.max() * 1.3  # leave room above the tallest bar for the labels
    ax.set_ylim(0, top)
    average = df["total"].mean()
    ax.axvline(PASS_MARK, color=TEXT_COLOR, linestyle="--", linewidth=1.5)
    ax.axvline(average, color=MUTED_COLOR, linestyle=":", linewidth=2)
    ax.text(PASS_MARK - 1, top * 0.95, f"Pass mark {PASS_MARK}", ha="right", va="top", color=TEXT_COLOR)
    ax.text(average + 1, top * 0.95, f"Average {average:.1f}", ha="left", va="top", color=MUTED_COLOR)
    ax.set_xlim(0, 100)
    style_axes(ax, "Total marks", "Total (out of 100)", "Number of students")
    fig.tight_layout()
    fig.savefig(out_dir / "score_histogram.png", dpi=120)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Analyze student marks from a CSV file.")
    parser.add_argument("csv_file", help="path to the marks CSV")
    parser.add_argument("--out", default="output", help="folder for results (default: output)")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = add_results(load_marks(args.csv_file))
    print_summary(df)

    df.sort_values("total", ascending=False).to_csv(out_dir / "results.csv", index=False)
    save_charts(df, out_dir)
    print(f"\nSaved results.csv, grade_distribution.png and score_histogram.png to '{out_dir}/'")


if __name__ == "__main__":
    main()
