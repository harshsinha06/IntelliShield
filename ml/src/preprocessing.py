"""Turn raw URL rows into train, validation, and test matrices.

Steps, in order:

1. Map PhiUSIIL labels onto model labels.
2. Extract lexical features with the shared extractor.
3. Drop rows the extractor rejects.
4. Drop normalized URLs whose rows disagree on the label.
5. Drop duplicate normalized URLs.
6. Stratified 70/15/15 split.

The split happens after deduplication, so one normalized URL cannot sit in
two partitions. No statistic used by the forest is fit on the validation or
test partitions. Trees do not need scaled inputs, so this module does not
fit a scaler.
"""

from __future__ import annotations

from collections import Counter

import pandas as pd
from sklearn.model_selection import train_test_split

from src.data_loader import map_source_label
from src.feature_extractor import FEATURE_NAMES, extract_features

RANDOM_STATE = 42
TEST_FRACTION = 0.15
VALIDATION_FRACTION = 0.15
TRAIN_FRACTION = 1.0 - TEST_FRACTION - VALIDATION_FRACTION


def run_preprocessing_pipeline(
    raw: pd.DataFrame,
    random_state: int = RANDOM_STATE,
    progress: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Run every preprocessing step and return disjoint splits plus a report."""
    table, cleaning = build_modeling_table(raw, progress=progress)
    train_df, val_df, test_df = split_labeled_frame(table, random_state=random_state)
    overlap = url_overlap_counts(train_df, val_df, test_df)
    if any(overlap.values()):
        raise RuntimeError(f"URL leakage across splits: {overlap}")
    report = {
        **cleaning,
        "split": {
            "train_rows": int(len(train_df)),
            "validation_rows": int(len(val_df)),
            "test_rows": int(len(test_df)),
            "train_fraction": TRAIN_FRACTION,
            "validation_fraction": VALIDATION_FRACTION,
            "test_fraction": TEST_FRACTION,
            "random_state": random_state,
            "stratified_on": "label",
            "url_overlap": overlap,
        },
        "class_counts": {
            "train": class_counts(train_df),
            "validation": class_counts(val_df),
            "test": class_counts(test_df),
        },
    }
    return train_df, val_df, test_df, report


def build_modeling_table(raw: pd.DataFrame, progress: bool = False) -> tuple[pd.DataFrame, dict]:
    """Extract features, drop failures, and deduplicate on the normalized URL."""
    if "url" not in raw.columns or "source_label" not in raw.columns:
        raise ValueError("Expected columns url and source_label.")

    records: list[dict] = []
    errors: Counter[str] = Counter()
    invalid_labels = 0
    total = len(raw)
    urls = raw["url"].tolist()
    labels = raw["source_label"].tolist()

    for index, (url, source_label) in enumerate(zip(urls, labels), start=1):
        if progress and index % 50_000 == 0:
            print(f"extracted {index}/{total}", flush=True)
        try:
            model_label = map_source_label(source_label)
        except (TypeError, ValueError):
            invalid_labels += 1
            continue
        result = extract_features(url)
        if not result.ok or result.features is None or result.normalized_url is None:
            errors[result.error or "unknown_extraction_error"] += 1
            continue
        row = {
            "normalized_url": result.normalized_url,
            "label": model_label,
        }
        row.update(result.features)
        records.append(row)

    if not records:
        raise ValueError("Feature extraction produced no usable rows.")

    table = pd.DataFrame.from_records(records)
    table, dedupe_report = deduplicate_urls(table)
    table = table.sort_values("normalized_url", kind="mergesort").reset_index(drop=True)
    cleaned_counts = class_counts(table)
    report = {
        "rows_in_input": int(total),
        "invalid_source_labels": invalid_labels,
        "extraction_failures": int(sum(errors.values())),
        "extraction_error_counts": dict(errors),
        **dedupe_report,
        "rows_after_cleaning": int(len(table)),
        "cleaned_class_counts": cleaned_counts,
        "feature_names": list(FEATURE_NAMES),
    }
    return table, report


def deduplicate_urls(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Remove label conflicts, then keep one row per normalized URL."""
    label_counts = frame.groupby("normalized_url", sort=False)["label"].nunique()
    conflict_urls = label_counts[label_counts > 1].index
    conflict_mask = frame["normalized_url"].isin(conflict_urls)
    conflict_rows = int(conflict_mask.sum())
    kept = frame.loc[~conflict_mask].copy()
    before = len(kept)
    kept = kept.drop_duplicates(subset=["normalized_url"], keep="first")
    removed = int(before - len(kept))
    return kept, {
        "label_conflict_urls": int(len(conflict_urls)),
        "label_conflict_rows": conflict_rows,
        "duplicate_rows_removed": removed,
    }


def split_labeled_frame(
    frame: pd.DataFrame,
    random_state: int = RANDOM_STATE,
    test_fraction: float = TEST_FRACTION,
    validation_fraction: float = VALIDATION_FRACTION,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Stratified train/validation/test split.

    Validation is `validation_fraction` of the original rows. The second
    split takes that share out of the train+validation remainder, so the
    test rows are not used to size the validation set beyond the fraction.
    """
    if not 0 < test_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("Split fractions must be between 0 and 1.")
    if test_fraction + validation_fraction >= 1:
        raise ValueError("Train fraction would be empty.")

    train_val, test = train_test_split(
        frame,
        test_size=test_fraction,
        random_state=random_state,
        stratify=frame["label"],
    )
    validation_share_of_train_val = validation_fraction / (1.0 - test_fraction)
    train, validation = train_test_split(
        train_val,
        test_size=validation_share_of_train_val,
        random_state=random_state,
        stratify=train_val["label"],
    )
    return (
        train.reset_index(drop=True),
        validation.reset_index(drop=True),
        test.reset_index(drop=True),
    )


def url_overlap_counts(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> dict[str, int]:
    train_urls = set(train_df["normalized_url"])
    val_urls = set(val_df["normalized_url"])
    test_urls = set(test_df["normalized_url"])
    return {
        "train_validation": len(train_urls & val_urls),
        "train_test": len(train_urls & test_urls),
        "validation_test": len(val_urls & test_urls),
    }


def class_counts(frame: pd.DataFrame) -> dict[str, int]:
    counts = frame["label"].value_counts().to_dict()
    return {
        "legitimate": int(counts.get(0, 0)),
        "phishing": int(counts.get(1, 0)),
    }


def feature_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    """Return columns in the training order and nothing else."""
    return frame.loc[:, list(FEATURE_NAMES)]
