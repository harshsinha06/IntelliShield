"""Load the PhiUSIIL phishing URL dataset.

Source, recorded before this module is allowed to download the file
-------------------------------------------------------------------
Name: PhiUSIIL Phishing URL Dataset
Creators: Arvind Prasad and Shalini Chandra
UCI: https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset
UCI citation: Prasad, A. & Chandra, S. (2024). PhiUSIIL Phishing URL (Website)
[Dataset]. UCI Machine Learning Repository.
https://doi.org/10.1016/j.cose.2023.103545
Mendeley: Prasad, Arvind; Chandra, Shalini (2023), "PhiUSIIL Phishing URL
Dataset", Mendeley Data, V2, doi: 10.17632/shwpxscxy2.2
License: Creative Commons Attribution 4.0 International (CC BY 4.0).
Stated on Mendeley (doi above) and on
https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+website+dataset

Publisher-stated size, from those pages, not from a model:
235,795 URLs; 134,850 legitimate; 100,945 phishing.
In the file, label 1 is legitimate and label 0 is phishing.

This loader keeps two columns only: URL and label. The other 54 published
columns include page-HTML measurements and derived scores. Those cannot be
recomputed by predict_url from a URL string, so they are not model inputs.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

ML_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ML_ROOT / "data"
CSV_PATH = DATA_DIR / "PhiUSIIL_Phishing_URL_Dataset.csv"
ZIP_PATH = DATA_DIR / "phiusiil.zip"
DOWNLOAD_URL = "https://archive.ics.uci.edu/static/public/967/phiusiil+phishing+url+dataset.zip"

PUBLISHER_STATED = {
    "rows": 235_795,
    "legitimate_label_1": 134_850,
    "phishing_label_0": 100_945,
}

SOURCE_LEGITIMATE = 1
SOURCE_PHISHING = 0
MODEL_LEGITIMATE = 0
MODEL_PHISHING = 1


def map_source_label(value: object) -> int:
    """Map a PhiUSIIL label onto the model label.

    PhiUSIIL uses 1 for legitimate and 0 for phishing.
    The model uses 0 for legitimate and 1 for phishing.
    """
    number = int(value)
    if number == SOURCE_LEGITIMATE:
        return MODEL_LEGITIMATE
    if number == SOURCE_PHISHING:
        return MODEL_PHISHING
    raise ValueError(f"Unexpected PhiUSIIL label: {value!r}")


def load_raw_dataset(csv_path: Path = CSV_PATH) -> tuple[pd.DataFrame, dict]:
    """Return URL/label rows and a measured distribution report.

    Downloads the UCI zip only when the CSV is absent.
    """
    ensure_csv(csv_path)
    header = pd.read_csv(csv_path, nrows=0, encoding="utf-8-sig")
    column_lookup = {column.lower(): column for column in header.columns}
    if "url" not in column_lookup or "label" not in column_lookup:
        found = list(header.columns)
        raise ValueError(f"Expected URL and label columns, found {found}")

    url_column = column_lookup["url"]
    label_column = column_lookup["label"]
    frame = pd.read_csv(
        csv_path,
        usecols=[url_column, label_column],
        encoding="utf-8-sig",
    )
    frame = frame.rename(columns={url_column: "url", label_column: "source_label"})
    if list(frame.columns) != ["url", "source_label"]:
        raise ValueError(f"Loader produced unexpected columns: {list(frame.columns)}")

    report = measure_distribution(frame, csv_path)
    return frame, report


def measure_distribution(frame: pd.DataFrame, csv_path: Path) -> dict:
    """Count rows and source labels from the frame that was actually loaded."""
    labels = pd.to_numeric(frame["source_label"], errors="coerce")
    counts = {
        str(int(key)): int(value)
        for key, value in labels.value_counts(dropna=False).items()
        if pd.notna(key)
    }
    missing_labels = int(labels.isna().sum())
    measured_rows = int(len(frame))
    legitimate = counts.get(str(SOURCE_LEGITIMATE), 0)
    phishing = counts.get(str(SOURCE_PHISHING), 0)
    publisher_match = (
        measured_rows == PUBLISHER_STATED["rows"]
        and legitimate == PUBLISHER_STATED["legitimate_label_1"]
        and phishing == PUBLISHER_STATED["phishing_label_0"]
        and missing_labels == 0
        and set(counts) <= {"0", "1"}
    )
    return {
        "csv_path": str(csv_path),
        "sha256": file_sha256(csv_path),
        "rows": measured_rows,
        "source_label_counts": counts,
        "missing_source_labels": missing_labels,
        "publisher_stated": PUBLISHER_STATED,
        "publisher_stated_matches_file": publisher_match,
        "columns_loaded": ["url", "source_label"],
        "source_label_legend": {
            "1": "legitimate",
            "0": "phishing",
        },
    }


def ensure_csv(csv_path: Path = CSV_PATH) -> Path:
    if csv_path.exists():
        return csv_path
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if not ZIP_PATH.exists():
        _download(DOWNLOAD_URL, ZIP_PATH)
    with zipfile.ZipFile(ZIP_PATH) as archive:
        members = [name for name in archive.namelist() if name.endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"Expected one CSV in the zip, found {members}")
        with archive.open(members[0]) as source, csv_path.open("wb") as target:
            shutil.copyfileobj(source, target)
    return csv_path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, destination: Path) -> None:
    temporary = destination.with_suffix(destination.suffix + ".partial")
    request = urllib.request.Request(url, headers={"User-Agent": "IntelliShield-research/0.1"})
    with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    temporary.replace(destination)


def main() -> None:
    frame, report = load_raw_dataset()
    print(json.dumps(report, indent=2))
    print(f"rows_loaded={len(frame)} columns={list(frame.columns)}")


if __name__ == "__main__":
    main()
