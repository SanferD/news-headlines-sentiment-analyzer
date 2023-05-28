from botocore.exceptions import ClientError, WaiterError
import boto3
import datetime
import json
import os
import setup_logging
import traceback

ENDPOINT_CONFIG_NAME = "news-headlines-endpoint-config"
ENDPOINT_NAME = "news-headlines-endpoint"
INITIAL_INSTANCE_COUNT = 1
INSTANCE_TYPE = "ml.m5.xlarge"
MODEL_NAME_PREFIX = "news-headlines-"
MODEL_PACKAGE_ARN = "ModelPackageArn"

sagemaker_client = boto3.client("sagemaker")
codepipeline_client = boto3.client('codepipeline')
log = setup_logging.setup_logging()


def lambda_handler(event, context):
    """
    Handle the Lambda function invocation.

    This function is triggered by an event and performs the necessary steps to create a model and
    update or create an endpoint in Amazon SageMaker. It loads input data from S3 designated by
    CodePipeline, creates a model, and creates/updates an endpoint with the created model.

    Parameters:
        event (dict): The event object containing information about the triggering event.
        context (object): The context object passed by Lambda.

    Raises:
        AssertionError: If the EXECUTION_ROLE_ARN environment variable is not specified.
    """
    global job_id_global

    now = datetime.datetime.now()
    now_str = now.isoformat().split('.')[0].replace(':', '-')
    log.info(f"Received event={event}, now={now.isoformat()}")

    execution_role_arn = os.environ.get("EXECUTION_ROLE_ARN")
    assert execution_role_arn is not None, \
        "EXECUTION_ROLE_ARN environment variable must be specified"

    job_id_global = event["CodePipeline.job"]["id"]
    log.info(f"CodePipeline JobId={job_id_global}")

    log.info("Reading artifact credentials")
    artifact_credentials = event["CodePipeline.job"]["data"]["artifactCredentials"]
    aws_access_key_id_global = artifact_credentials["accessKeyId"]
    aws_secret_access_key_global = artifact_credentials["secretAccessKey"]
    aws_session_token_global = artifact_credentials["sessionToken"]

    log.info("Reading input S3 information from the event")
    input_artifact = event["CodePipeline.job"]["data"]["inputArtifacts"][0]
    input_s3_location = input_artifact["location"]["s3Location"]
    input_bucket_name = input_s3_location["bucketName"]
    input_object_key = input_s3_location["objectKey"]

    log.info(f"Load input from s3://{input_bucket_name}/{input_object_key} with artifact creds")
    s3_client_for_codepipeline = boto3.client("s3",
                                              aws_access_key_id=aws_access_key_id_global,
                                              aws_secret_access_key=aws_secret_access_key_global,
                                              aws_session_token=aws_session_token_global)
    input_response = get_s3_object(s3_client=s3_client_for_codepipeline,
                                   input_bucket_name=input_bucket_name,
                                   input_object_key=input_object_key,)
    input_data = json.loads(input_response["Body"].read())
    model_package_arn = input_data[MODEL_PACKAGE_ARN]
    log.info(f"Loaded {MODEL_PACKAGE_ARN}={model_package_arn}")

    model_name = f"{MODEL_NAME_PREFIX}{now_str}"
    log.info(f"Creating model model_name={model_name} with ModelPackageName={model_package_arn}")
    create_sagemaker_model(execution_role_arn=execution_role_arn,
                           model_package_arn=model_package_arn,
                           model_name=model_name)

    upsert_endpoint(model_name=model_name, now_str=now_str)

    put_job_success()


def create_sagemaker_model(execution_role_arn, model_package_arn, model_name):
    """Creates sagemaker model"""
    try:
        sagemaker_client.create_model(
            ModelName=model_name,
            Containers=[{"ModelPackageName": model_package_arn}],
            ExecutionRoleArn=execution_role_arn,
        )
    except ClientError as e:
        log.exception("Unexpected error")
        put_job_failure(e)
        raise e


def get_s3_object(s3_client, input_bucket_name, input_object_key):
    """Gets the S3 object s3://{input_bucket_name}/{input_object_key}"""
    try:
        return s3_client.get_object(Bucket=input_bucket_name, Key=input_object_key)
    except ClientError as e:
        log.exception("Unexpected error")
        put_job_failure(e)
        raise e


def upsert_endpoint(model_name, now_str):
    """
    Upsert the endpoint in Amazon SageMaker.

    This function checks if the endpoint already exists and either updates the existing endpoint
    configuration or creates a new one if the endpoint does not exist. It waits for the endpoint to
    be in-service before returning.

    Parameters:
        model_name (str): The name of the model to associate with the endpoint.
    """
    log.info(f"Upserting Endpoint for model_name={model_name}")

    endpoint_config_name = f"{ENDPOINT_NAME}-config-{now_str}"
    log.info(f"Create EndpointConfig {endpoint_config_name}")
    create_sagemaker_endpoint_config(model_name=model_name,
                                     endpoint_config_name=endpoint_config_name)
    try:
        log.info(f"Checking if Endpoint {ENDPOINT_NAME} already exists")
        sagemaker_client.describe_endpoint(EndpointName=ENDPOINT_NAME)

        log.info(f"Endpoint {ENDPOINT_NAME} exists, "
                 f"update EndpointConfig to {endpoint_config_name}")
        sagemaker_client.update_endpoint(
            EndpointName=ENDPOINT_NAME,
            EndpointConfigName=endpoint_config_name,
        )
    except ClientError as e:
        # ValidationException => triggered by describe-endpoint (ok) or update-endpoint (bad)
        if e.response["Error"]["Code"] == "ValidationException":
            # ValidationException triggered by update-endpoint
            if "Cannot update in-progress endpoint" in e.response["Error"]["Message"]:
                log.exception(f"Endpoint {ENDPOINT_NAME} is already updating, "
                              f"aborting current update")
                put_job_failure(e)
                raise e

            log.info(f"Endpoint does not exist, creating Endpoint {ENDPOINT_NAME} "
                     f"with EndpointConfig {endpoint_config_name}")
            create_sagemaker_endpoint(endpoint_config_name)
        else:
            log.exception("Unexpected error")
            put_job_failure(e)
            raise e

    try:
        log.info(f"Waiting for Endpoint {ENDPOINT_NAME} to be InService")
        waiter = sagemaker_client.get_waiter("endpoint_in_service")
        waiter.wait(EndpointName=ENDPOINT_NAME)
    except WaiterError as e:
        log.exception("Waiter timedout, possibly endpoint failed to deploy ?")
        put_job_failure(e)
        raise e


def create_sagemaker_endpoint_config(model_name, endpoint_config_name):
    try:
        sagemaker_client.create_endpoint_config(
            EndpointConfigName=endpoint_config_name,
            ProductionVariants=[
                {
                    "VariantName": "variant-1",
                    "ModelName": model_name,
                    "InitialInstanceCount": INITIAL_INSTANCE_COUNT,
                    "InstanceType": INSTANCE_TYPE,
                    "InitialVariantWeight": 1,
                }
            ],
        )
    except ClientError as e:
        log.exception("Unexpected error")
        put_job_failure(e)
        raise e


def create_sagemaker_endpoint(endpoint_config_name):
    """Creates a sagemaker endpoint using the endpoint configuration"""
    try:
        sagemaker_client.create_endpoint(
            EndpointName=ENDPOINT_NAME,
            EndpointConfigName=endpoint_config_name)
    except ClientError as e:
        log.exception("Unknown error")
        put_job_failure(e)
        raise e


def put_job_success():
    """Notifies AWS CodePipeline of a successful job execution."""
    log.info(f"JobSuccess, job_id={job_id_global}")
    response = codepipeline_client.put_job_success_result(
        jobId=job_id_global,
    )
    return response


def put_job_failure(exception):
    """Notifies AWS CodePipeline of a failed job execution with exception details."""
    failure_message = str(exception)
    failure_stacktrace = traceback.format_exc()

    failure_details = {
        'type': 'JobFailed',
        'message': f"{failure_message}\n{failure_stacktrace}",
    }
    log.info(f"JobFailure, job_id={job_id_global}, failure_details={failure_details}")
    response = codepipeline_client.put_job_failure_result(
        jobId=job_id_global,
        failureDetails=failure_details,
    )
    return response


if __name__ == "__main__":
    event = {
        "CodePipeline.job": {
            "id": "34bb9d07-b738-4e66-8622-0b5019064c77",
            "data": {
                "inputArtifacts": [
                    {
                        "location": {
                            "s3Location": {
                                "bucketName": "deploymentpipelinestack-deploymentpipelineartifac-19bvk0xe17415",
                                "objectKey": "DeploymentPipelineSt/Artifact_S/8oIuSP0.json",
                            },
                        },
                    }
                ],
                "artifactCredentials": {
                    "accessKeyId": "ASIA25RUNCGS33ZPHLOK",
                    "secretAccessKey": "6amJCpf7MnPZRywD13XL1567Zqh3/bWUa5yQjIdP",
                    "sessionToken": "IQoJb3JpZ2luX2VjEBUaCXVzLWVhc3QtMSJGMEQCIDSln4IW2bCVmeXcdOVzV2KoPvTQo2gw2vjBu7mf8THfAiBN+wrrSMzW/byq0HmC37v9lkrrKrJIoLemdkD3AjD4ySrfBAhOEAMaDDc1MDY1NTQ0MzM2NSIM6/N9wQXhVWKItpCOKrwEWSsKX+GZcvKm2Xv+T+8pfpGYE1S0jWVnl3hCH2FG9UtvpNRN31KAqSyiZUZvZsskPfJf7/F/mbgZLb7Qnpos0n40/Lnva0ER5TNfveNKth5L2ZTX2IL3rJMrC7NPNIInYbB30Mg2BZ0x/NUXHXqR2XFHwwD1hdbFSQpSJysh0hP3UJ97sYOel3Vggve5aC1ZxYMvqf7mSi5NKtvGRzLwq+6OTlzvUWJdHHCp8TBlfi8e6pweV4qBo6A3LGPOh5kExklCKBqnI9D4/IDssjfw0LtCJHTqchu9Dn9BDrPdQwvCMDVT5aIXAVCSREzy7WQ73+CrjgSdQ+kI0QJPENTI0VZ3UbDNK7JKanENqYdUG71M8bk2iaYsFfpgSLzrr5uCw/FKfibC4aaaGP4d+zjU0EtBOZfTgzvUKkUFrzFx5kEj2LYwzOjo1buuWsxuYO7f7r/WFkIuvM7RunAmSYdKFwEg2DiNk05y3N4h0WxVvOnkaTTLj4Kihmia5tlsn+AxIrUxjxXHxBhnVludhSvFuimjfxUHuTdZ/dHslSCpigPnDOaAZxYufVuXnDQyvEBPJfC1PH9/OuUqorGkD1Xbv7zS6GC1FiWVF08iIAfO4SlgpE+MjCQ8l2csabEvVfDzdge6v1iUH7hFJ3e59l6aETjl7MiiIprqUq7L2ZQ+9NePYPGuTUBSDBbCfRkpOGoX9TnP/Jhv34nNZH2okOshUhGIEC/4hLEpYdaYNOUlbHHg7SUhZ5IWhP6ayWMw4tHJowY6ngGUCAfBn3jkVQ8kvwZbFwYWHwygEPP62srwtxeh80fMHcb67LfCaGy/beYPxTZg6mVvB9ltg1lxTdD/SkVM6cXZA1NTFMrkBLKP/VtmKkut60wJ6xtkNZ/G/ZJygG1sWPrSHrcx2g9uO7Sub5QdGEbUnXO0MP4JNpbyc7L+c3sxm7mCw5EqAi8d/OdxMSwLpFE5Q6wEG7oERW81p+scXQ==",
                    "expirationTime": 1685220454000,
                },
            },
        }
    }

    lambda_handler(event=event, context=None)
