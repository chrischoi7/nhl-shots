# Reproduction and repository guide

## What can be reproduced now

The supporting artifacts can be rebuilt from the **saved** notebook outputs and original `metrics.csv`, without data downloads, model files, notebook execution, or training. From the repository root:

```bash
python -m venv .venv
# Activate .venv using the command for your shell.
python -m pip install matplotlib==3.10.8
python scripts/build_case_study.py
```

The script was verified with Matplotlib 3.10.8. It uses standard-library parsing and does not evaluate notebook code. It validates Git blob hashes for its two input files and fails if they differ from the reviewed snapshot; after a future modeling change, review and update the exporter/provenance intentionally.

Generated files:

| File | Contents |
|---|---|
| [catboost_deciles.csv](../reports/catboost_deciles.csv) | Saved CatBoost deciles; exact counts, six-decimal displayed scores/rates/lift |
| [confusion_matrix.csv](../reports/confusion_matrix.csv) | Counts reconstructed from the top three deciles |
| [model_comparison.csv](../reports/model_comparison.csv) | Initial AP comparison and subsequent boosting CV log losses, kept as separate stages |
| [evidence_summary.json](../reports/evidence_summary.json) | Source commit/blob hashes, counts, saved scores and labeled derived baseline |
| [ranking_and_calibration.svg](../reports/ranking_and_calibration.svg) | Ranking and reliability views of the saved deciles |

The exporter checks that reconstructed precision, recall, and F1 match `metrics.csv` within 1e-12. It deliberately omits the questionable boosting CV standard deviations. The SVG can be viewed directly on GitHub or opened in a browser.

## What a full training rerun still needs

This is **not yet a one-command reproducible training project**. There is no dependency lock file, raw data snapshot, final prediction export, or saved estimator in the reviewed repository. The 20-row sample is not the training dataset.

| Historical stage | Reads | Produces / current issue |
|---|---|---|
| Cleaning notebook | `all_teams.csv`, `shots_2015-2023.csv`, `shots_2024.csv` under an absolute local raw-data directory | `mp_shots_clean.csv` |
| EDA notebook | `mp_shots_clean.csv` | Contains drops and sentinel handling, but no committed export of `mp_shots_cleaner.csv` |
| Legacy prep notebook | `mp_shots_cleaner.csv` | Exploratory encoding/scaling and a 25% split; not the final modeling path |
| Modeling notebook | `mp_shots_cleaner.csv` | Main 30% evaluation split, searches, scores, and local cached artifacts |
| Supporting exporter | Saved Modeling notebook and original metrics CSV | Documentation evidence only |

Before a full rerun:

1. Obtain the source data from [MoneyPuck](https://moneypuck.com/data.htm), respecting its terms and attribution. Record exact file dates, row counts, and checksums; current downloads may differ from the historical snapshot.
2. Recover the missing cleaner transformation, including its missing-value handling and feature-drop decisions. Do not substitute an inferred transformation and call the result an exact reproduction.
3. Resolve the path, scorer, cache, and model-identity problems in the [validation plan](VALIDATION_PLAN.md).
4. Record a tested environment. Imports include pandas, NumPy, scikit-learn, imbalanced-learn, XGBoost, LightGBM, CatBoost, Matplotlib, Plotly, SciPy, statsmodels, joblib, ipywidgets and a notebook runtime. These are an inventory, not a verified install specification. Search cells request GPU execution; CPU substitutions would be a different run configuration.
5. Execute from a fresh kernel without old caches. Export split identifiers, probabilities and labels, selected parameters, model files and environment metadata with the new run.

Saved notebook outputs are evidence of a historical session, not proof that all displayed cells execute together from a clean state. Original PDFs remain historical capstone documents and were not rewritten as part of this update.
