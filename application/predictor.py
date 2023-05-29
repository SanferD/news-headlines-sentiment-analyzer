import boto3
import json
import nltk
from nltk.tokenize import RegexpTokenizer

nltk.download('punkt')

ENDPOINT_NAME = "news-headlines-endpoint"

tokenizer = RegexpTokenizer(r'\w+')
sm_client = boto3.client("sagemaker-runtime")

def predict(headline):
    response = sm_client.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType='application/json',
        Body=json.dumps({"instances": [preprocess(headline)]})
    )
    results = json.loads(response['Body'].read().decode())
    result = results[0]
    label = result["label"][0][9:]
    probability = result["prob"][0]
    return {"sentiment": label, "probability": probability}


def preprocess(line):
    tokens = tokenizer.tokenize(line.lower())
    return " ".join(tokens)


if __name__ == "__main__":
    input_data = [
        "Dow drops for a fourth straight day on U.S. default worries as debt ceiling talks stumble",
    ]
    for headline in input_data:
        result = predict(headline)
        print(headline, result)


