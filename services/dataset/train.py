#!/usr/bin/env python3
"""
train.py — Train the TF-IDF + LogisticRegression document classifier.

Reads .txt files from samples/ subfolders only. Does not load
generated/training_corpus or any personal documents.

Usage:
  python train.py --samples ./samples --output ../demo-api/models/classifier.joblib

Retrain inside the demo-api image when possible so sklearn matches runtime.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

FOLDER_LABEL_MAP = {
    "invoices": "FACTURE",
    "factures": "FACTURE",
    "devis": "DEVIS",
    "siret": "SIRET_ATTESTATION",
    "kbis": "KBIS",
    "urssaf": "URSSAF",
    "rib": "RIB",
    "noisy": None,
}

FILENAME_LABEL_MAP = {
    "facture": "FACTURE",
    "devis": "DEVIS",
    "siret": "SIRET_ATTESTATION",
    "kbis": "KBIS",
    "urssaf": "URSSAF",
    "rib": "RIB",
    "noisy_facture": "FACTURE",
    "noisy_devis": "DEVIS",
    "noisy_siret": "SIRET_ATTESTATION",
    "noisy_kbis": "KBIS",
    "noisy_urssaf": "URSSAF",
    "noisy_rib": "RIB",
}


def infer_label(folder: str, filename: str) -> str | None:
    label = FOLDER_LABEL_MAP.get(folder)
    if label is not None:
        return label
    if folder not in FOLDER_LABEL_MAP:
        return None
    for prefix, doc_type in FILENAME_LABEL_MAP.items():
        if filename.startswith(prefix):
            return doc_type
    return None


def load_dataset(samples_dir: Path) -> tuple[list[str], list[str]]:
    texts: list[str] = []
    labels: list[str] = []

    for folder in sorted(samples_dir.iterdir()):
        if not folder.is_dir():
            continue
        for txt_file in sorted(folder.glob("*.txt")):
            label = infer_label(folder.name, txt_file.name)
            if label is None:
                print(f"  [SKIP] Cannot infer label for: {txt_file}")
                continue
            texts.append(txt_file.read_text(encoding="utf-8"))
            labels.append(label)

    return texts, labels


def _logistic_regression() -> LogisticRegression:
    kwargs = {
        "max_iter": 1000,
        "C": 5.0,
        "solver": "lbfgs",
    }
    try:
        return LogisticRegression(**kwargs, multi_class="multinomial")
    except TypeError:
        return LogisticRegression(**kwargs)


def train(samples_dir: Path, output_path: Path) -> None:
    print(f"Loading dataset from: {samples_dir}")
    texts, labels = load_dataset(samples_dir)

    if not texts:
        raise ValueError(f"No .txt files found under {samples_dir}. Run the generators first.")

    counts = Counter(labels)
    print(f"Dataset: {len(texts)} samples")
    for doc_type, count in sorted(counts.items()):
        print(f"  {doc_type}: {count}")

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )
    print(f"\nSplit: train={len(X_train)}  test={len(X_test)}")

    pipeline = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    analyzer="word",
                    ngram_range=(1, 2),
                    max_features=20_000,
                    sublinear_tf=True,
                    min_df=2,
                ),
            ),
            ("clf", _logistic_regression()),
        ]
    )

    print("\nTraining...")
    pipeline.fit(X_train, y_train)

    y_train_pred = pipeline.predict(X_train)
    y_pred = pipeline.predict(X_test)
    label_order = sorted(counts)
    print(f"\nTraining accuracy: {accuracy_score(y_train, y_train_pred):.4f}")
    print(f"Test accuracy:     {accuracy_score(y_test, y_pred):.4f}")
    print("\nClassification report (held-out test):")
    print(classification_report(y_test, y_pred, labels=label_order, digits=3))
    print("Confusion matrix (rows=true, cols=pred):")
    print("Labels:", label_order)
    print(confusion_matrix(y_test, y_pred, labels=label_order))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, output_path)
    print(f"\nModel saved to: {output_path.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train GED Metadata AI document classifier")
    parser.add_argument(
        "--samples",
        type=str,
        default="./samples",
        help="Root directory containing factures/, devis/, kbis/, siret/, urssaf/, rib/",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="../demo-api/models/classifier.joblib",
        help="Output path for the .joblib model file",
    )
    args = parser.parse_args()

    train(Path(args.samples), Path(args.output))


if __name__ == "__main__":
    main()
