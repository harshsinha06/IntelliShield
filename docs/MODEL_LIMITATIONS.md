# Model limitations

The numbers below are copied from `ml/models/metrics.json`. They are the PhiUSIIL holdout scores for this forest. They are not a live-traffic false-positive rate, and they are not the scores published in the PhiUSIIL paper.

Positive class is phishing. File label `1` was mapped to model label `0` (legitimate). File label `0` was mapped to model label `1` (phishing). The API then maps legitimate to `safe`.

## Data leakage

The loader reads only `URL` and `label`. The other PhiUSIIL columns, including HTML-derived fields, are not model inputs.

Features are computed from each URL on its own. The keyword list and the shortener list are frozen constants. They were not mined from the validation or test rows.

Rows are deduplicated and sorted by normalized URL, then split stratified 70/15/15 with `random_state` 42. The saved overlap of normalized URLs is:

| Pair | Overlap |
|------|---------|
| Train and validation | 0 |
| Train and test | 0 |
| Validation and test | 0 |

That check does not prove the features are independent of the label construction in the original corpus. The scheme composition below is a corpus artifact, not a leak across the split.

## Class imbalance

After cleaning, the file has 134,850 legitimate URLs and 100,302 phishing URLs. 643 duplicate phishing rows were removed. The split is stratified. `class_weight` is `null`.

| Split | Legitimate | Phishing |
|-------|------------|----------|
| Train | 94,394 | 70,212 |
| Validation | 20,228 | 15,045 |
| Test | 20,228 | 15,045 |

The classes are uneven, not rare-class uneven. The larger problem is that every legitimate URL in the file is HTTPS and every HTTP URL is phishing. `uses_https` has importance `0.39823569344292997`.

## Overfitting

The forest selected on validation phishing F1 uses `n_estimators` 100, `max_depth` 20, and `min_samples_leaf` 2. Validation metrics below were computed on a model fit on the training split only. Test metrics are from the saved model, which was refit on train plus validation.

| Split | F1 | Accuracy |
|-------|----|----------|
| Validation, before refit | 0.9963018490754623 | 0.9968531171150739 |
| Test, saved model | 0.9967018689409335 | 0.997193320670201 |

The test F1 is not lower than the validation F1. That gap does not show a classic validation-to-test drop. It also does not show that the forest generalizes to the open web. Depth 20 on a feature that already separates most of this file can memorize corpus patterns. `https://example.com/docs/guide` is outside this file and was scored phishing with phishing probability 1.0. HTTPS does not force a safe label.

## Precision and recall

Test set, phishing as the positive class, support 20,228 legitimate and 15,045 phishing:

| Metric | Value |
|--------|-------|
| Precision | 0.9991317125300561 |
| Recall | 0.9942838152210036 |
| F1 | 0.9967018689409335 |
| ROC-AUC | 0.9981371405525038 |

Validation, same positive class, before the refit:

| Metric | Value |
|--------|-------|
| Precision | 0.9987975951903808 |
| Recall | 0.9938185443668993 |
| F1 | 0.9963018490754623 |
| ROC-AUC | 0.9980541024740688 |

Vote fractions from `predict_proba` are not calibrated probabilities.

## False positives and false negatives

Test confusion matrix. Rows are the true class. Columns are the predicted class.

|  | Predicted legitimate | Predicted phishing |
|--|----------------------|--------------------|
| True legitimate | 20,215 | 13 |
| True phishing | 86 | 14,959 |

A false positive here is a legitimate URL predicted phishing: 13 on the test split. A false negative is a phishing URL predicted legitimate: 86 on the test split.

Validation, before the refit: 18 false positives and 93 false negatives.

These counts are inside the PhiUSIIL holdout. They are not the number of mistakes the dashboard will make on URLs a person pastes in.

## Limits of URL-based detection

The model sees 15 lexical features of the URL string. It does not open the page, read HTML, follow redirects, check a certificate, or consult a blocklist.

Domain length is the last two hostname labels, not the Public Suffix List. An IP host has subdomain count 0, and its domain length equals the hostname length.

The keyword feature matches whole alphanumeric tokens from a fixed list. `loginlogin` does not match `login`. A phishing URL with none of those tokens can still be labeled phishing by the other features, and a legitimate URL that contains `login` can still be labeled safe.

Because every HTTP URL in the training file is phishing, an HTTP URL is easy for this forest to call phishing. That is a property of PhiUSIIL, not a rule the product hard-codes. A new phishing site on HTTPS, or a benign HTTP site that was never in this file, is outside what these scores measure.

The explanation text describes the forest output. It is not a second detector, and it cannot see the page either.
