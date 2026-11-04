# Prioritized validation plan

This plan is based on code and saved outputs at commit `1c0e229`. The documentation update preserves every notebook and `metrics.csv`; none of the experiments below has been run.

## Highest-value gaps

| Priority | Gap and evidence | Why it matters | Completion criterion |
|---|---|---|---|
| 1 | **Independent evaluation:** Modeling cells 22, 109–129 use a random shot split and revisit evaluation labels for sampling/threshold decisions. | The current headline cannot establish future performance. | Preserve game and season identifiers outside model inputs; reserve later games/seasons before development; show zero game overlap. Select thresholds and calibration on training/validation data, then evaluate once on the held-out period. |
| 2 | **Probability calibration:** cell 115 gives top-decile score 0.790 versus observed rate 0.289; original loss 0.515 exceeds the derived constant-rate reference 0.250. | Raw scores cannot yet support expected-goals totals. | On natural-prevalence validation data, compare no calibration with sigmoid/isotonic approaches as appropriate; report untouched-test log loss, Brier score, reliability, AP and ROC-AUC alongside a training-prevalence constant and simple location baseline. Do not select the method on test results. |
| 3 | **Fold isolation:** rare-category pooling precedes splitting (cell 17); scaling precedes inner CV; feature selection uses all undersampled training labels (cells 72–75); oversampling precedes CV (cells 62, 65, 118–120). | Validation folds can influence preparation; duplicated shots can inflate oversampled CV. | Fit learned transforms and samplers only within each training fold. Verify no duplicated original shot IDs cross folds. Perform feature selection inside CV or remove it from the comparison. |
| 4 | **Reproducibility and model identity:** missing `mp_shots_cleaner.csv` transformation; cache-dependent branches; invalid `neg-log-loss` scorer in cell 89; separate CatBoost search/final-fit settings. | A fresh checkout cannot reproduce or reliably identify the selected estimator. | Run from raw source files in a fresh environment without caches; save configuration, dependency versions, input hashes, feature schema, model artifact, split IDs, and prediction file together. Check that final fitting uses the intended iteration/configuration. |
| 5 | **Feature semantics and leakage audit:** penalty mappings in cell 11 appear inverted; removal of future-event fields is not fully traceable through the missing cleaner step. | Importance may be misinterpreted, and prediction-time availability is not fully established. | Document the timestamp/availability of each predictor; test penalty cases against the data dictionary; retain identifiers only for splitting/auditing. Any semantic fixes get a new experiment version. |
| 6 | **Comparable model experiments and uncertainty:** CatBoost uses 73 native features; other boosting models use 30 selected encoded features. Model losses differ by about 0.002. | Algorithm superiority is not isolated by the current setup. | Use common splits and comparable feature information; record each search budget. Estimate paired uncertainty by resampling games, and report ranking/calibration by season, empty-net status, manpower situation, and shot type. |

## Concrete notebook repairs for the next version

These are code-review findings, not silent changes to the historical results.

- **Data handoff:** cleaning exports `mp_shots_clean.csv`, while prep/modeling read `mp_shots_cleaner.csv`. The checked-in EDA notebook does not export that latter file. Restore the exact transformation before attempting reproduction.
- **Portable paths:** cleaning/EDA contain absolute macOS paths; modeling uses Windows backslashes. Define one project data directory and use path joins.
- **Search configuration:** use the valid `neg_log_loss` scoring identifier in cell 89. Set each model's own `best_index_` when reading its CV standard deviation (cells 85 and 91 currently reuse an earlier variable). Do not publish those standard deviations as verified uncertainty.
- **CatBoost identity:** retain distinct undersampled and oversampled model variables. Record parameters and selected iteration explicitly. Feature importance must come from the same model that generated the reported predictions.
- **Penalty labels:** for a home-team shooter, a penalty on the away team normally represents a power-play opportunity. Current `powerplay*` fields take the home team's penalty values. Verify complex penalty situations and rename/correct consistently in a new version.
- **Legacy prep notebook:** it performs a separate 25% split; its scaler is fitted before that split but the resulting `scaled_df` is not used for its final `X`. Do not infer that this is the final modeling path. The main modeling notebook fits its scaler after splitting.
- **Cleaning name map:** the player-name normalization code maps player IDs to themselves rather than to the selected names. This is a housekeeping defect, not evidence that the reported final metrics are wrong.

## Suggested work order

First restore data provenance and deterministic execution. Then introduce game-aware temporal splits and fold-local transformations. After that, compare simple baselines and calibration, freeze the operating rule, and produce a new evaluation report.

Keep the current results as an explicitly historical experiment. Do not overwrite them with a rerun while retaining their old captions or provenance.

## Changes completed in this documentation update

- Replaced the broad introduction with a decision-oriented case study and explicit evidence limits.
- Corrected CV-versus-evaluation labels and percentile-versus-probability threshold wording.
- Added exact exported counts, a ranking/calibration figure, and a derived constant-rate loss reference.
- Added a model card and a practical reproduction guide without claiming the project is fully reproducible.
