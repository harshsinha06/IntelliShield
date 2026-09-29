"""Tests for label mapping, column selection, and split leakage."""

from pathlib import Path

import pandas as pd
import pytest

from src.data_loader import CSV_PATH, load_raw_dataset, map_source_label
from src.preprocessing import build_modeling_table, run_preprocessing_pipeline


def test_phiusiil_label_mapping_is_not_inverted():
    assert map_source_label(1) == 0
    assert map_source_label(0) == 1
    assert map_source_label("1") == 0
    assert map_source_label("0") == 1


def test_loader_keeps_url_and_label_only():
    if not Path(CSV_PATH).exists():
        pytest.skip("PhiUSIIL CSV is not downloaded")
    frame, report = load_raw_dataset()
    assert list(frame.columns) == ["url", "source_label"]
    assert report["rows"] == len(frame)
    assert report["source_label_counts"] == {"0": 100945, "1": 134850}
    assert report["publisher_stated_matches_file"] is True
    assert report["columns_loaded"] == ["url", "source_label"]


def test_splits_are_disjoint_and_duplicates_do_not_cross_them():
    rows = []
    for index in range(80):
        rows.append({"url": f"https://legit{index}.example/docs", "source_label": 1})
        rows.append({"url": f"http://phish{index}.example/login", "source_label": 0})
    rows.append({"url": "https://legit0.example/docs#fragment", "source_label": 1})
    raw = pd.DataFrame(rows)
    train_df, val_df, test_df, report = run_preprocessing_pipeline(raw)
    groups = [set(part["normalized_url"]) for part in (train_df, val_df, test_df)]
    assert groups[0].isdisjoint(groups[1])
    assert groups[0].isdisjoint(groups[2])
    assert groups[1].isdisjoint(groups[2])
    assert sum(len(group) for group in groups) == report["rows_after_cleaning"]
    assert report["duplicate_rows_removed"] == 1
    assert report["split"]["url_overlap"] == {
        "train_validation": 0,
        "train_test": 0,
        "validation_test": 0,
    }


def test_conflicting_labels_are_dropped_before_the_split():
    raw = pd.DataFrame(
        [
            {"url": "https://example.com/a", "source_label": 1},
            {"url": "https://example.com/a", "source_label": 0},
            {"url": "https://other.example/b", "source_label": 1},
            {"url": "ftp://example.com/skip", "source_label": 1},
        ]
    )
    table, report = build_modeling_table(raw)
    assert report["label_conflict_rows"] == 2
    assert report["extraction_failures"] == 1
    assert list(table["normalized_url"]) == ["https://other.example/b"]
    assert int(table.iloc[0]["label"]) == 0
