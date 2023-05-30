"""
EXAMPLE INPUT:
==> /opt/ml/processing/input/labels.csv <==
__label__good
__label__good
__label__neutral

==> /opt/ml/processing/input/test.jsonl.out <==
{"label": ["__label__neutral"], "prob": [0.9413388967514038]}
{"label": ["__label__good"], "prob": [0.4687191843986511]}
{"label": ["__label__neutral"], "prob": [0.7470827698707581]}

EXAMPLE OUTPUT:
==> /opt/ml/processing/evaluation/evaluation.json <==
{"regression_metrics": {"accuracy": {"value": 0.48760330578512395},
"precision": {"value": 0.28342173262613896}, "recall": {"value": 0.30607037335482135},
"f-score": {"value": 0.29269601677148843}}}
"""
import json
import logging
from collections import namedtuple

import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

import constants

ACCURACY = "accuracy"
FSCORE = "f-score"
PRECISION = "precision"
RECALL = "recall"
REGRESSION_METRICS = "regression_metrics"
VALUE = "value"

LABEL = "label"
TEST_FILE_NAME = f"{constants.TEST_FILE_NAME}.out"

logging.basicConfig(level=logging.INFO)


def main():
    """Main function to read true and found labels, compute metrics and save them."""
    true_labels_df = read_true_labels_df()
    found_labels_df = read_found_labels_df()
    metrics = compute_metrics(true_labels_df=true_labels_df, found_labels_df=found_labels_df)
    logging.info(f"Found metrics={metrics}")
    create_evaluation_dir()
    save_metrics(metrics)


def read_true_labels_df() -> pd.DataFrame:
    """Reads true labels from a CSV file into a DataFrame.

    Returns:
        pd.DataFrame: A DataFrame containing the true labels.
    """
    labels_file_path = constants.INPUT_LABELS_DIR / constants.LABELS_FILE_NAME
    logging.info(f"Reading true labels from {labels_file_path}")
    return pd.read_csv(labels_file_path, names=[LABEL])


def read_found_labels_df() -> pd.DataFrame:
    """Reads found labels from a JSONL file into a DataFrame.

    Returns:
        pd.DataFrame: A DataFrame containing the found labels.
    """
    test_file_path = constants.INPUT_TRANSFORM_DIR / TEST_FILE_NAME
    logging.info(f"Reading found labels from {test_file_path}")
    found_labels = list()
    with open(test_file_path, "r") as f:
        for line in f.readlines():
            found_labels.append(json.loads(line)["label"])
    return pd.DataFrame(found_labels, columns=[LABEL])


def compute_metrics(true_labels_df: pd.DataFrame, found_labels_df: pd.DataFrame) -> dict:
    """Computes evaluation metrics for the given true and found labels.

    Args:
        true_labels_df (pd.DataFrame): A DataFrame containing the true labels.
        found_labels_df (pd.DataFrame): A DataFrame containing the found labels.

    Returns:
        dict: A dictionary containing the computed evaluation metrics.
    """
    true_labels = true_labels_df["label"].to_numpy()
    found_labels = found_labels_df["label"].to_numpy()

    accuracy = accuracy_score(true_labels, found_labels)
    precision = precision_score(true_labels, found_labels, average="macro")
    recall = recall_score(true_labels, found_labels, average="macro")
    fscore = f1_score(true_labels, found_labels, average="macro")

    return {
        REGRESSION_METRICS: {
            ACCURACY: {
                VALUE: accuracy
            },
            PRECISION: {
                VALUE: precision,
            },
            RECALL: {
                VALUE: recall,
            },
            FSCORE: {
                VALUE: fscore,
            },
        }
    }


def create_evaluation_dir():
    """Creates the evaluation directory if it doesn't exist."""
    logging.info("Creating directories")
    constants.EVALUATION_DIR.mkdir(exist_ok=True)


def save_metrics(metrics: dict):
    """Saves the given metrics to a JSON file.

    Args:
        metrics (dict): A dictionary containing the metrics to save.
    """
    logging.info(f"Saving metrics to {constants.EVALUATION_PATH}")
    with open(constants.EVALUATION_PATH, "w+") as f:
        f.write(json.dumps(metrics))


if __name__ == "__main__":
    main()
