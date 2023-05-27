import * as cdk from 'aws-cdk-lib'
import * as constants from './constants'
import * as iam from 'aws-cdk-lib/aws-iam'
import * as lambda from 'aws-cdk-lib/aws-lambda'
import * as path from 'path'
import * as s3 from 'aws-cdk-lib/aws-s3'

const ASSET_PACKAGE_PATH = path.join("..", "deploy-pipeline")

export interface DeploymentPipelineLambdasProps extends cdk.StackProps {
    dataBucket: s3.Bucket
    sagemakerExecutionRole: iam.Role
}

export class DeploymentPipelineLambdasStack extends cdk.Stack {
    triggerModelDeploy: lambda.Function
    createOrUpdateEndpoint: lambda.Function

    constructor(scope: cdk.App, id: string, props: DeploymentPipelineLambdasProps) {
        super(scope, id, props)

        const code = lambda.Code.fromAsset(ASSET_PACKAGE_PATH)

        const commonLambdaProps = {
            runtime: lambda.Runtime.PYTHON_3_9,
            memorySize: 128,
            code,
        }

        this.triggerModelDeploy = new lambda.Function(this, "TriggerModelDeploy", {
            ...commonLambdaProps,
            handler: "trigger_model_deploy.lambda_handler",
            timeout: cdk.Duration.minutes(3),
            environment: {
                BUCKET_NAME: props.dataBucket.bucketName,
            }
        })
        this.setupTriggerModelDeployPermissions(props.dataBucket)

        this.createOrUpdateEndpoint = new lambda.Function(this, "CreateOrUpdateEndpoint", {
            ...commonLambdaProps,
            handler: "create_or_update_endpoint.lambda_handler",
            timeout: cdk.Duration.minutes(7),
            environment: {
                EXECUTION_ROLE_ARN: props.sagemakerExecutionRole.roleArn,
            },
        })
        this.setupCreateOrUpdateEndpoint(props.dataBucket)
    }

    setupTriggerModelDeployPermissions(dataBucket: s3.Bucket) {
        const resourceArn = dataBucket.arnForObjects(constants.APPROVED_MODEL_JSON)
        this.triggerModelDeploy.addToRolePolicy(new iam.PolicyStatement({
            actions: ["s3:PutObject"],
            resources: [resourceArn],
        }))
        dataBucket.grantPut(this.triggerModelDeploy, resourceArn)
    }

    setupCreateOrUpdateEndpoint(dataBucket: s3.Bucket) {
        this.createOrUpdateEndpoint.addToRolePolicy(new iam.PolicyStatement({
            actions: [
                "iam:PassRole",
            ],
            resources: ["*"],
        }))
        this.createOrUpdateEndpoint.addToRolePolicy(new iam.PolicyStatement({
            actions: [
                "codepipeline:PutJobFailureResult",
                "codepipeline:PutJobSuccessResult",
            ],
            resources: ["*"],
        }))

        this.createOrUpdateEndpoint.addToRolePolicy(new iam.PolicyStatement({
            actions: [
                "sagemaker:CreateEndpoint",
                "sagemaker:CreateEndpointConfig",
                "sagemaker:CreateModel",
                "sagemaker:DescribeEndpoint",
                "sagemaker:UpdateEndpoint",
            ],
            resources: ["*"],
        }))
    }
}
