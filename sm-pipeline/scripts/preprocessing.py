"""
EXAMPLE INPUT:
==> /opt/ml/processing/input/data.csv <==
2,"According to Gran , the company has no plans to move all production to Russia , although that is where the company is growing ."
2,"Technopolis plans to develop in stages an area of no less than 100,000 square meters in order to host companies working in computer technologies and telecommunications , the statement said ."
0,"The international electronic industry company Elcoteq has laid off tens of employees from its Tallinn facility ; contrary to earlier layoffs the company contracted the ranks of its office workers , the daily Postimees reported ."

EXAMPLE OUTPUT:
==> /opt/ml/processing/train/train.csv <==
__label__neutral "in a recent interview with the financial times ft sampo s board chairman bjorn wahlroos said if p c was certainly for sale and the price had been set at sek 85 billion confirming earlier statements"
__label__neutral "the annual report will be sent automatically to shareholders holding at least 2 000 sampo plc shares"
__label__neutral "the total restructuring costs are expected to be about eur 30mn of which eur 13 5 mn was booked in december 2008"

==> /opt/ml/processing/validation/validation.csv <==
__label__neutral "telecomworldwire 7 april 2006 tj group plc sells stake in morning digital design oy finnish it company tj group plc said on friday 7 april that it had signed an agreement on selling its shares of morning digital design oy to edita oyj"
__label__good "india s trade with russia currently stands at four billion dollars growing 9 6 per cent in fiscal 2007"
__label__neutral "destia oy is a finnish infrastructure and construction service company building maintaining and designing traffic routes industrial and traffic environments but also complete living environments"

==> /opt/ml/processing/test/test.jsonl <==
{"source": "upm kymmene has generated seventeen consecutive quarters of positive cash flow from operations"}
{"source": "net profit was 35 5 mln compared with 29 8 mln"}
{"source": "helsinki afx cramo said it has agreed to sell cramo nederland bv cnl its dutch machinery and equipment rental unit to jaston groep for an undisclosed sum"}

==> /opt/ml/processing/labels/labels.csv <==
__label__good
__label__good
__label__neutral
"""
import json
import logging
from typing import Tuple

import nltk
import pandas as pd
from nltk.tokenize import RegexpTokenizer
from sklearn.model_selection import train_test_split

import constants

TOKENS = "tokens"
LABELS = "labels"

LABEL_IDX = 0
HEADLINE_IDX = 1

VAL_FRAC = 0.15
TEST_FRAC = 0.05
INDEX2LABEL = {
    0: constants.BAD,
    1: constants.GOOD,
    2: constants.NEUTRAL,
}

logging.basicConfig(level=logging.INFO)


def main():
    """Main entry point of the program."""
    logging.info("Downloading 'punkt")
    nltk.download('punkt')

    logging.info("Reading input DataFrame...")
    df = pd.read_csv(constants.DATA_PATH)

    logging.info("Creating output DataFrame...")
    output_df = create_output_df(df)

    logging.info("Splitting into train, validation, and test sets...")
    train_df, val_df, test_df = train_val_test_split(output_df)
    logging.info(f"Train size={len(train_df)}, Validation size={len(val_df)}, "
                 f"Test size={len(test_df)}")

    logging.info("Creating output directories...")
    create_output_directories()

    logging.info("Saving datasets...")
    save_datasets(train_df=train_df, val_df=val_df, test_df=test_df)


def create_output_df(df: pd.DataFrame) -> pd.DataFrame:
    """Create the output DataFrame with tokens and labels.

    Args:
        df: Input DataFrame.

    Returns:
        The output DataFrame with tokens and labels.
    """
    tokenizer = RegexpTokenizer(r'\w+')
    output_df = pd.DataFrame()
    output_df[TOKENS] = df.apply(lambda row: " ".join(tokenizer.tokenize(row[HEADLINE_IDX].lower())), axis=1)
    output_df[LABELS] = df.apply(lambda row: f"__label__{INDEX2LABEL[row[LABEL_IDX]]}", axis=1)
    output_df = output_df.reindex([LABELS, TOKENS], axis=1)
    return output_df


def train_val_test_split(output_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split the output DataFrame into train, validation, and test sets.

    Args:
        output_df: Output DataFrame.

    Returns:
        A tuple containing train, validation, and test DataFrames.
    """
    n_val = int(VAL_FRAC * len(output_df))
    n_test = int(TEST_FRAC * len(output_df))
    train_val, test = train_test_split(output_df, test_size=n_test)
    train, val = train_test_split(train_val, test_size=n_val)
    return train, val, test


def create_output_directories():
    """Create the output directories if they don't exist."""
    constants.TRAIN_DIR.mkdir(exist_ok=True)
    constants.VAL_DIR.mkdir(exist_ok=True)
    constants.TEST_DIR.mkdir(exist_ok=True)
    constants.LABELS_DIR.mkdir(exist_ok=True)


def save_datasets(train_df: pd.DataFrame, val_df: pd.DataFrame, test_df: pd.DataFrame):
    """Save the train, validation, and test DataFrames as CSV files.

    Args:
        train_df: Train DataFrame.
        val_df: Validation DataFrame.
        test_df: Test DataFrame.
    """
    training_args = [
        (constants.TRAIN_CHANNEL, constants.TRAIN_PATH, train_df),
        (constants.VAL_CHANNEL, constants.VAL_PATH, val_df),
    ]

    for (channel, dst, df) in training_args:
        logging.info(f"Saving {channel} DataFrame for training to {dst}")
        df.to_csv(dst, sep=" ", index=False, header=False)

    logging.info(f"Saving test_df['{TOKENS}'] DataFrame for batch transform to {constants.TEST_PATH}")
    with open(constants.TEST_PATH, "w+") as f:
        for row in test_df[TOKENS].tolist():
            f.write(json.dumps({"source": row}) + "\n")

    logging.info(f"Saving test_df['{LABELS}'] DataFrame for evaluation to {constants.LABELS_PATH}")
    test_df[LABELS].to_csv(constants.LABELS_PATH, index=False, header=False)


if __name__ == "__main__":
    main()
