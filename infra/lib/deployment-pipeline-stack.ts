import * as cdk from 'aws-cdk-lib';
import * as codepipeline from 'aws-cdk-lib/aws-codepipeline'
import * as codepipeline_actions from 'aws-cdk-lib/aws-codepipeline-actions'
import * as constants from './constants'
import * as iam from 'aws-cdk-lib/aws-iam'
import * as lambda from 'aws-cdk-lib/aws-lambda'
import * as s3 from 'aws-cdk-lib/aws-s3'

export interface DeploymentPipelineStackProps extends cdk.StackProps {
    createOrUpdateEndpoint: lambda.Function
    dataBucket: s3.Bucket
}

export class DeploymentPipelineStack extends cdk.Stack {
    readonly sourceOutput: codepipeline.Artifact

    constructor(app: cdk.App, id: string, props: DeploymentPipelineStackProps) {
        super(app, id, props)

        const pipeline = new codepipeline.Pipeline(this, "DeploymentPipeline")

        this.sourceOutput = new codepipeline.Artifact()
        const sourceStage = pipeline.addStage({
            stageName: "Source",
        })
        sourceStage.addAction(new codepipeline_actions.S3SourceAction({
            actionName: `ON-CHANGE-${constants.APPROVED_MODEL_JSON}`,
            bucket: props.dataBucket,
            bucketKey: constants.APPROVED_MODEL_JSON,
            output: this.sourceOutput,
        }))

        const deployStage = pipeline.addStage({
            stageName: "Deploy",
        })
        deployStage.addAction(new codepipeline_actions.LambdaInvokeAction({
            actionName: "CreateOrUpdateSagemakerEndpoint",
            lambda: props.createOrUpdateEndpoint,
            inputs: [this.sourceOutput],
        }))
    }

}
