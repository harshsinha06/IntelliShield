# IntelliShield — ML Pipeline

Phase 1 trains a Random Forest on lexical features of raw URLs and saves it for `predict_url`. The API and the dashboard are not part of this phase.

The numbers below are the ones written by `python -m src.train` on 26 September 2026. They are copied from `ml/models/metrics.json` and from a direct count of the CSV. They are not a target that the code was edited to hit.

## Dataset

| Item | Value |
|------|--------|
| Name | PhiUSIIL Phishing URL Dataset |
| Creators | Arvind Prasad and Shalini Chandra |
| UCI | [archive.ics.uci.edu/dataset/967](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset) |
| Paper | Prasad & Chandra, *Computers & Security*, 2024, 103545. https://doi.org/10.1016/j.cose.2023.103545 |
| Mendeley | V2, doi [10.17632/shwpxscxy2.2](https://doi.org/10.17632/shwpxscxy2.2) |
| License | CC BY 4.0, stated on the Mendeley record and on the UCI page titled "PhiUSIIL Phishing URL (Website)" |
| File used | `ml/data/PhiUSIIL_Phishing_URL_Dataset.csv` |
| SHA-256 | `a236549cd369cd80bd478ff8e1779cbf44c58d5c3f79f7a51a1adbed7d06d1c6` |
| Download | `https://archive.ics.uci.edu/static/public/967/phiusiil+phishing+url+dataset.zip` |

Publisher-stated size, from the UCI and Mendeley pages: 235,795 URLs, 134,850 legitimate, 100,945 phishing.

Measured from this file, before any cleaning:

| File label | Meaning in the file | Rows |
|------------|---------------------|------|
| 1 | legitimate | 134,850 |
| 0 | phishing | 100,945 |
| Total | | 235,795 |

`publisher_stated_matches_file` in `metrics.json` is true. Missing labels: 0.

The loader keeps `URL` and `label` only. The file has 54 other columns, including HTML measurements (`LineOfCode`, `NoOfiFrame`, `HasPasswordField`) and corpus-derived scores (`URLSimilarityIndex`, `TLDLegitimateProb`). Those columns are not model inputs. `predict_url` cannot rebuild them from a URL string.

### Label mapping

The file and the model use opposite integers. The mapping is explicit in `map_source_label` and covered by a unit test.

| PhiUSIIL `label` | Meaning | Model integer | `predict_url` string |
|------------------|---------|---------------|----------------------|
| 1 | legitimate | 0 | `legitimate` |
| 0 | phishing | 1 | `phishing` |

Precision, recall, and F1 use phishing as the positive class.

### Scheme composition, counted from the raw URL text

Splitting each raw URL on the first `:` and grouping by the file label:

| Class | HTTPS | HTTP |
|-------|------:|-----:|
| Legitimate (label 1) | 134,850 | 0 |
| Phishing (label 0) | 49,196 | 51,749 |

Every legitimate URL in this file is HTTPS. Every HTTP URL is phishing. That is a property of the corpus, not a rule IntelliShield adds. It is why `uses_https` is the top feature below, and why the test scores are high. A phishing page with a certificate does not look like an HTTP row in this file, and about half of the phishing rows are already HTTPS.

Duplicate removal did not drop any legitimate row, so the legitimate class remains 100% HTTPS after cleaning.

## Cleaning and split

`run_preprocessing_pipeline` does the following, in order:

1. Map labels.
2. Extract the 15 features with `extract_features`. Rows that fail stay out of the matrix. This run had 0 extraction failures.
3. Drop a normalized URL if its rows disagree on the label. This run had 0 conflicts.
4. Keep one row per normalized URL. This run removed 643 duplicate rows, all from the phishing class.
5. Sort by normalized URL, then make a stratified 70/15/15 split with `random_state=42`.

Rows after cleaning: 235,152. Legitimate 134,850. Phishing 100,302.

| Partition | Rows | Legitimate | Phishing |
|-----------|-----:|----------:|---------:|
| Train | 164,606 | 94,394 | 70,212 |
| Validation | 35,273 | 20,228 | 15,045 |
| Test | 35,273 | 20,228 | 15,045 |

Normalized-URL overlap between every pair of partitions: 0. The check runs before fitting and aborts if it is not zero.

No scaler is fit. Tree splits do not depend on feature scale, and a scaler fit on all rows would be a leakage path with nothing to gain.

The keyword list and the shortener list are constants in `feature_extractor.py`. They were not mined from the validation or test rows.

## Model selection

Candidates are fit on the training partition only. The winner is the highest phishing-class F1 on the validation partition. The test partition is not read during selection.

Fixed settings: `criterion=gini`, `max_features=sqrt`, `bootstrap=true`, `class_weight=null`, `random_state=42`, `n_jobs=-1`.

Validation F1 for each candidate:

| n_estimators | max_depth | min_samples_leaf | Validation F1 |
|-------------:|----------:|-----------------:|--------------:|
| 100 | 20 | 2 | 0.9963018490754623 |
| 200 | 20 | 2 | 0.9962681594029055 |
| 100 | 30 | 2 | 0.9962681594029055 |
| 200 | 30 | 2 | 0.9962347139382226 |
| 100 | 20 | 5 | 0.9955665188839627 |
| 200 | 20 | 5 | 0.9956002933137791 |

Selected configuration: `n_estimators=100`, `max_depth=20`, `min_samples_leaf=2`.

That model, still fit on the training partition only, scored the validation partition as:

| Metric | Validation |
|--------|------------|
| Accuracy | 0.9968531171150739 |
| Precision | 0.9987975951903808 |
| Recall | 0.9938185443668993 |
| F1 | 0.9963018490754623 |
| ROC-AUC | 0.9980541024740688 |

Validation confusion matrix, rows true class (legitimate, phishing) and columns predicted class (legitimate, phishing):

|  | Predicted legitimate | Predicted phishing |
|--|---------------------:|-------------------:|
| True legitimate | 20,210 | 18 |
| True phishing | 93 | 14,952 |

The saved model is then refit with those hyperparameters on train+validation (199,879 rows). The test numbers below belong to that refit model.

## Test metrics of the saved model

Scored once on the 35,273 test rows. `python -m src.evaluate` loads the saved model and the saved split and reproduces these values.

| Metric | Test |
|--------|------|
| Accuracy | 0.997193320670201 |
| Precision | 0.9991317125300561 |
| Recall | 0.9942838152210036 |
| F1 | 0.9967018689409335 |
| ROC-AUC | 0.9981371405525038 |

Test confusion matrix, same row and column order:

|  | Predicted legitimate | Predicted phishing |
|--|---------------------:|-------------------:|
| True legitimate | 20,215 | 13 |
| True phishing | 86 | 14,959 |

Support: 20,228 legitimate, 15,045 phishing.

### How to read the scores

These are holdout scores on PhiUSIIL after the split above. They are not a measured false-positive rate on live browser traffic.

`uses_https` has impurity importance 0.398236. Combined with the scheme table, a large part of the separation is "HTTP appears only in the phishing class of this file." The other features still matter: about half of the phishing URLs are HTTPS, and the model does not classify every HTTPS URL as legitimate. After training, `predict_url("https://example.com/docs/guide")` returned `phishing` with `phishing_probability` 1.0. That URL is not in the evaluation tables. It is a reminder that a unanimous tree vote is a vote fraction, not a calibrated probability, and that a URL outside this corpus can be scored phishing even when it uses HTTPS.

## Feature importance

Mean decrease in Gini impurity on the saved forest. Values are the floats stored in `metrics.json`.

| Feature | Importance |
|---------|-----------:|
| uses_https | 0.398236 |
| special_char_count | 0.140812 |
| digit_count | 0.118203 |
| url_length | 0.090000 |
| path_segment_count | 0.051152 |
| domain_length | 0.049926 |
| subdomain_count | 0.039821 |
| dot_count | 0.037616 |
| hostname_length | 0.035622 |
| hyphen_count | 0.035088 |
| query_param_count | 0.001637 |
| has_suspicious_keyword | 0.001611 |
| is_url_shortener | 0.000179 |
| has_at_symbol | 0.000091 |
| has_ip_address | 0.000006 |

Definitions are in `FEATURE_ENGINEERING.md`. Low importance means the feature rarely changed the splits in this forest. It does not mean the feature is useless on another corpus. IP hosts, `@`, and shorteners are rare in this file, so their importances are near zero here.

## Artifacts

| File | Role |
|------|------|
| `ml/models/phishing_rf.joblib` | Saved bundle. The classifier is `bundle["model"]`. |
| `ml/models/feature_config.json` | Feature order, keyword list, shortener list, label mapping. `predict_url` refuses to run if this file disagrees with the extractor. |
| `ml/models/metrics.json` | Dataset hash, cleaning counts, grid, validation metrics, test metrics, importances. |
| `ml/data/processed/splits.joblib` | Train, validation, and test frames used by `evaluate`. Gitignored. Rebuilt by training. |

Training metadata in the metrics file: `trained_at` `2026-09-26T13:38:01.511664+00:00`, `sklearn_version` `1.9.1`, feature spec `lexical-v1`.

`predict_url` extracts features, builds one row in the saved column order, and returns the label, both class probabilities, and the feature dict. A malformed URL returns `prediction: null` and an error code. It does not return a zero vector.

## Commands

From `ml/`, with the virtualenv activated:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.train
python -m src.evaluate
python -m pytest
python -m src.predict "https://example.com/docs/guide"
```

`src.train` downloads the UCI zip if `data/PhiUSIIL_Phishing_URL_Dataset.csv` is absent. The CSV and zip are gitignored. The model, feature config, and metrics file are kept.

`ml/notebooks/01_pipeline_walkthrough.ipynb` calls the same modules. It does not fit a second forest.
