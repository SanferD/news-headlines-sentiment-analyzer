import os
import boto3
import json
import setup_logging

SOURCE = "source"
DETAIL_TYPE = "detail-type"
DETAIL = "detail"
SOURCE_SAGEMAKER = "aws.sagemaker"
DETAIL_TYPE_MODEL_PKG_STATE_CHANGE = "SageMaker Model Package State Change"
MODEL_PACKAGE_GROUP_NAME = "ModelPackageGroupName"
NEWS_HEADLINES = "news-headlines"
MODEL_APPROVAL_STATUS = "ModelApprovalStatus"
MODEL_PACKAGE_ARN = "ModelPackageArn"
APPROVED = "Approved"
OBJECT_KEY = "approved-model.json"

s3_client = boto3.client("s3")
log = setup_logging.setup_logging()


def lambda_handler(event, context):
    log.info(f"event={event}")
    log.info("Loading environment variables")
    bucket_name = os.environ.get("BUCKET_NAME")
    assert bucket_name is not None, \
        f"BUCKET_NAME environment variable must be specified"

    log.info("Validating event")
    source = event.get(SOURCE)
    detail_type = event.get(DETAIL_TYPE)
    assert source == SOURCE_SAGEMAKER, f"{source} != {SOURCE_SAGEMAKER}"
    assert detail_type == DETAIL_TYPE_MODEL_PKG_STATE_CHANGE, \
        f"{detail_type} != {DETAIL_TYPE_MODEL_PKG_STATE_CHANGE}"

    log.info("Reading event detail")
    detail = event.get(DETAIL)
    model_package_group_name = detail[MODEL_PACKAGE_GROUP_NAME]
    if model_package_group_name != NEWS_HEADLINES:
        log.info(f"{model_package_group_name} != {NEWS_HEADLINES}")
        return

    model_package_arn = detail[MODEL_PACKAGE_ARN]
    model_approval_status = detail[MODEL_APPROVAL_STATUS]
    log.info(f"model_package_arn={model_package_arn}, "
             f"model_approval_status={model_approval_status}")

    if model_approval_status != APPROVED:
        log.info(f"{MODEL_APPROVAL_STATUS}={model_approval_status} != "
                 f"{APPROVED}, skipping...")
        return

    log.info(f"Updating s3://{bucket_name}/{OBJECT_KEY}")
    json_data = json.dumps({
        MODEL_PACKAGE_ARN: model_package_arn
    })
    s3_client.put_object(Body=json_data, Bucket=bucket_name, Key=OBJECT_KEY)


if __name__ == "__main__":
    lambda_handler(event={
      "version": "0",
        "id": "10d3ad8b-50de-af8e-5b57-d839bd42cb09",
        "detail-type": "SageMaker Model Package State Change",
        "source": "aws.sagemaker",
        "account": "<accountId>",
        "time": "2023-05-26T14:31:22Z",
        "region": "us-east-1",
        "detail": {
            "ModelPackageName": "news-headlines/4",
            "ModelPackageGroupName": "news-headlines",
            "ModelPackageArn": "arn:aws:sagemaker:us-east-1:accountId:model-package/news-headlines/4",
            "ModelApprovalStatus": "Approved"
        }
    }, context=None)
