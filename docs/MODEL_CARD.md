# Model card and result provenance

## Scope

**Task:** binary goal classification and retrospective shot ranking. Target: `goal`, 1 for a goal and 0 otherwise. Intended review point: recorded shot context before its outcome is known.

**Population:** MoneyPuck regular-season shot records from 2015–2024 according to the original README. Cleaning excludes playoff records and removes rows with selected missing fields. The input includes missed shots, shots on goal, and goals; it is not a dataset of on-target shots alone. Raw files are absent, so season coverage and every intermediate row count have not been independently reverified.

**Proposed user:** an analyst prioritizing shot clips. **Unsupported uses:** calibrated expected goals, causal coaching advice, player/goalie value estimates, betting decisions, or live deployment. No operational benefit has been measured.

## Data and model path

The modeling notebook reports 1,028,007 input rows and 88 columns. Filtering `lasteventteam` to HOME/AWAY leaves 1,027,818 rows; the saved split contains 719,472 training and 308,346 evaluation rows, with 73 predictors. These counts supersede a generic claim of “100+ engineered features” for the final model. Many supplied features were engineered by MoneyPuck.

The EDA drop list removes identifiers, vendor predictions such as `xgoal`, and post-shot outcomes. Modeling separately drops `shotwasongoal`. The saved input schema does not contain `timeuntilnextevent`, but the committed notebooks do not show the complete transformation that produced this cleaned input. Therefore this review cannot certify an end-to-end leakage-free dataset.

Modeling fits the scaler on the training split only. CatBoost returns to the unscaled, unencoded training frame, using `playerpositionthatdidevent`, `shottype`, and `lasteventcategory` as categorical variables. Random undersampling balances training to 98,642 records (49,321 per class); the 308,346-row evaluation set is not resampled.

The selected CatBoost search reports depth 8, learning rate 0.03, and L2 regularization 5. Its minimum saved CV log loss occurs at iteration 1,248 (zero-based). The separate final-fit cell does not explicitly carry that iteration count forward. Model artifacts are absent, and cached models can bypass the displayed training configuration.

## Evidence ledger

Sources refer to [Modeling.ipynb](../Notebooks/Modeling.ipynb) at [the reviewed commit](https://github.com/chrischoi7/nhl-shots/tree/1c0e229380b4d29630d29d79a0f20951d3f7fb22). Cell positions below are 1-based notebook positions, not execution counts. IDs survive reordering more reliably.

| Claim | Evidence | Scope |
|---|---|---|
| 719,472 train / 308,346 evaluation rows; 73 predictors | Cell 23, shape output | Saved modeling split; the separate prep notebook uses a different split |
| Initial evaluation AP: LR 0.215737; RF 0.248313; XGBoost 0.361075 | Cell 53; final saved `results` expression | Initial model family experiment, not final CatBoost AP |
| Boosting CV losses: CatBoost 0.516124, LightGBM 0.517898, XGBoost 0.518216 | Cell 105, ID `3f53c158c81bb4b1` | Balanced-data CV; feature sets and search procedures differ |
| CatBoost decile counts, mean scores, rates, lift | Cell 115, ID `a1414d2a8dad55f1` | Exact saved counts; continuous values displayed to six decimals |
| Top-30% threshold and final scores | Cells 129–130; [metrics.csv](../metrics.csv) | Cutoff 0.5260194322163532; evaluation reused for selection |
| Oversampled CatBoost evaluation loss 0.587058 | Cell 123, ID `a4112585955c753b` | Historical alternative, not a new run |

The initial model comparison uses `average_precision_score`; AP is not identical to trapezoidal PR-AUC. The CatBoost CV result's “test-Logloss-mean” means CV validation folds, not the separate `X_test` set. ROC-AUC remains meaningful after balancing training, and AP can be calculated externally from any model's scores. Choice of log loss is an evaluation choice, not proof that balancing invalidates other metrics.

## Reconstructed operating point

The [export script](../scripts/build_case_study.py) sums the top three saved deciles. Its precision, recall, and F1 match the original metrics to floating-point tolerance.

| Actual outcome | Not selected | Selected in top 30% |
|---|---:|---:|
| No goal | 210,195 | 77,014 |
| Goal | 5,647 | 15,490 |

This operating point selects 92,504 shots. Its false positives and missed goals represent a workload tradeoff, not a demonstrated optimum. No cost function or stakeholder capacity target was specified. The observed score cutoff is cohort-specific; the numerical probability threshold and a recurring top-30% review policy are different rules.

## Ranking versus calibration

The evaluation prevalence is 21,137 / 308,346 = 6.85496%. The top decile contains 8,909 goals among 30,835 shots: a 28.8925% goal rate and 4.214829× saved lift. The mean score in that decile is 78.9603%, demonstrating overestimation.

A constant predictor using training prevalence, 49,321 / 719,472, yields evaluation log loss 0.249870994. This is a derived reference calculated from aggregate class counts, not a separately trained model or new experiment. The reported CatBoost loss is 0.514662245. Strong ranking does not establish accurate absolute probabilities.

The reliability figure uses saved decile averages. It is descriptive, not a calibration fit, and its points are rounded at the notebook's saved precision. Raw predictions are needed for full calibration metrics, Brier score, final CatBoost AP/ROC-AUC, and uncertainty estimates.

## Validation and interpretation limits

- Random shot splitting can place shots from the same game on both sides and mix seasons. It does not test future-season performance.
- The original evaluation labels informed decile/threshold decisions and comparisons between sampling strategies. Treat results as development evidence, not an untouched final test.
- Rare-category grouping occurs before the split. Scaling/feature selection for some comparisons occurs outside inner CV; oversampling before CV can place duplicate source rows across folds.
- Boosting comparisons use different inputs: 30 selected encoded features for LightGBM/XGBoost versus 73 original predictors for CatBoost. The approximately 0.002 loss gap does not establish statistically superior performance.
- The oversampling branch can overwrite `cat_model`; later feature-importance extraction may refer to that overwritten object even though final metrics use the earlier `cb_proba`. Do not attribute the feature-importance table definitively to the final undersampled model without resolving this.
- Penalty feature names appear reversed relative to the shooting team's advantage in cell 11 and the repository data dictionary. Preserve current values/results; verify the semantics before interpreting importance or rerunning.

The [validation plan](VALIDATION_PLAN.md) separates documentation corrections from experiments that would produce new results.
