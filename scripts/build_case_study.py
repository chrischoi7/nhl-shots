"""Export saved notebook evidence; never fit a model or execute notebook cells.

Run from any directory: python scripts/build_case_study.py
Requires matplotlib for the figure; all extraction uses the standard library.
"""
from pathlib import Path
import ast
import csv
import hashlib
import io
import json
import math
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports"
SOURCE_COMMIT = "1c0e229380b4d29630d29d79a0f20951d3f7fb22"
EXPECTED_BLOBS = {
    "Notebooks/Modeling.ipynb": "28c625c0aa0a528b18b7c036d4ffef5ea7895097",
    "metrics.csv": "9602f4cdff92b1efc2db2d11ed779958f969fe0c",
}


def text(value):
    return "".join(value) if isinstance(value, list) else value


def saved_output(notebook, cell_id):
    cell = next(c for c in notebook["cells"] if c.get("id") == cell_id)
    return "\n".join(text(o.get("text", o.get("data", {}).get("text/plain", "")))
                     for o in cell.get("outputs", []))


def write_csv(name, rows):
    with (OUT / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    # Refuse stale provenance if the underlying source files change.
    for name, expected in EXPECTED_BLOBS.items():
        data = (ROOT / name).read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if actual != expected:
            raise ValueError(f"{name} differs from the reviewed snapshot; review evidence before rebuilding")
    notebook = json.loads((ROOT / "Notebooks/Modeling.ipynb").read_text())
    metrics = next(csv.DictReader(io.StringIO((ROOT / "metrics.csv").read_text())))
    deciles = []
    for line in saved_output(notebook, "a1414d2a8dad55f1").splitlines():
        parts = line.split()
        if len(parts) == 6 and parts[0].isdigit():
            deciles.append(dict(decile=int(parts[0]), shots=int(parts[1]), goals=int(parts[2]),
                                avg_predicted=float(parts[3]), goal_rate=float(parts[4]),
                                lift=float(parts[5])))
    if len(deciles) != 10 or [d["decile"] for d in deciles] != list(range(10)):
        raise ValueError("Expected ten saved CatBoost deciles")
    n = sum(d["shots"] for d in deciles)
    goals = sum(d["goals"] for d in deciles)
    selected = sum(d["shots"] for d in deciles[:3])
    tp = sum(d["goals"] for d in deciles[:3])
    fp, fn = selected - tp, goals - tp
    tn = n - tp - fp - fn
    precision, recall = tp / selected, tp / goals
    f1 = 2 * precision * recall / (precision + recall)
    for name, value in [("precision", precision), ("recall", recall), ("f1", f1)]:
        if not math.isclose(value, float(metrics[name]), abs_tol=1e-12):
            raise ValueError(f"Saved deciles disagree with metrics.csv: {name}")
    # Training prevalence recovered from saved training and balanced RUS counts.
    shape_cell = next(c for c in notebook["cells"]
                      if text(c["source"]).strip() == "X_train.shape, X_test.shape, y_train.shape, y_test.shape")
    shapes = ast.literal_eval(saved_output(notebook, shape_cell["id"]).strip())
    train_n = shapes[0][0]
    # Locate the saved RandomUnderSampler shape by source text, avoiding execution counts.
    rus_cell = next(c for c in notebook["cells"] if "print(X_rus.shape)" in text(c["source"]))
    rus_rows = int(re.search(r"\((\d+), \d+\)", saved_output(notebook, rus_cell["id"])).group(1))
    train_prevalence = (rus_rows / 2) / train_n
    test_prevalence = goals / n
    baseline_ll = -(test_prevalence * math.log(train_prevalence)
                    + (1 - test_prevalence) * math.log(1 - train_prevalence))
    OUT.mkdir(exist_ok=True)
    write_csv("catboost_deciles.csv", deciles)
    write_csv("confusion_matrix.csv", [dict(actual="no_goal", predicted_no_goal=tn, predicted_goal=fp),
                                       dict(actual="goal", predicted_no_goal=fn, predicted_goal=tp)])
    model_rows = []
    for snippet, stage in [("results", "initial_average_precision"), ("boost_results", "boosting_log_loss")]:
        matches = [c for c in notebook["cells"] if text(c["source"]).strip() == snippet and c.get("outputs")]
        content = saved_output(notebook, matches[-1]["id"])
        # literal_eval does not execute notebook code or arbitrary functions.
        rows = ast.literal_eval(re.sub(r"np\.float64\(([^()]+)\)", r"\1", content))
        for row in rows:
            model_rows.append(dict(stage=stage, model=row["model"], cv_mean=row["cv_mean"],
                                   holdout_average_precision=row.get("holdout_ap", ""),
                                   best_params=json.dumps(row["best_params"], sort_keys=True),
                                   source_cell_id=matches[-1]["id"]))
    write_csv("model_comparison.csv", model_rows)
    summary = dict(source_commit=SOURCE_COMMIT, source_blobs=EXPECTED_BLOBS,
                   status="Historical exploratory outputs; no retraining or independent validation",
                   evaluation_shots=n, evaluation_goals=goals, evaluation_goal_rate=test_prevalence,
                   selected_shots=selected, selected_goals=tp,
                   precision=precision, recall=recall, f1=f1,
                   probability_threshold=float(metrics["threshold"]),
                   reported_log_loss=float(metrics["logloss"]),
                   training_goal_rate=train_prevalence,
                   derived_constant_training_prevalence_log_loss=baseline_ll,
                   baseline_note="Calculated from saved aggregate counts; not a new fitted model",
                   decile_note="Counts exact as saved; mean scores/rates/lift rounded in notebook output")
    (OUT / "evidence_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "svg.hashsalt": "nhl-case-study"})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    x = [d["decile"] + 1 for d in deciles]
    rates = [d["goals"] / d["shots"] for d in deciles]
    axes[0].bar(x, rates, color=["#137C83"] * 3 + ["#ADC6CF"] * 7)
    axes[0].axhline(test_prevalence, color="#A14E32", linestyle="--", label=f"Overall goal rate: {test_prevalence:.2%}")
    axes[0].set(title="Ranking: goals concentrate in higher scores", xlabel="Decile (1 = highest scores)", ylabel="Observed goal rate")
    axes[0].set_xticks(x)
    axes[0].yaxis.set_major_formatter(PercentFormatter(1))
    axes[0].legend(frameon=False, fontsize=9)
    axes[1].plot([0, 1], [0, 1], linestyle="--", color="#86939D", label="Perfect calibration")
    axes[1].plot([d["avg_predicted"] for d in deciles], rates, "o-", color="#137C83", label="Saved decile averages")
    axes[1].set(xlim=(0, 1), ylim=(0, 1), xlabel="Mean model score", ylabel="Observed goal rate", title="Calibration: scores overestimate goal rates")
    axes[1].xaxis.set_major_formatter(PercentFormatter(1))
    axes[1].yaxis.set_major_formatter(PercentFormatter(1))
    axes[1].legend(frameon=False, fontsize=9)
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.15)
        ax.set_axisbelow(True)
    fig.suptitle("CatBoost | historical evaluation on 308,346 shots", fontsize=16, fontweight="bold", x=0.05, ha="left")
    fig.text(0.05, 0.015, "Source: saved Modeling.ipynb deciles. Evaluation set was reused for model/threshold decisions; no new model run.", fontsize=9, color="#53616D")
    fig.tight_layout(rect=(0.02, 0.05, 0.99, 0.93))
    fig.savefig(OUT / "ranking_and_calibration.svg", metadata={"Date": None})
    plt.close(fig)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
