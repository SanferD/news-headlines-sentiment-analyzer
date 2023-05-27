import * as cdk from 'aws-cdk-lib'
import * as events from 'aws-cdk-lib/aws-events'
import * as lambda from 'aws-cdk-lib/aws-lambda'
import * as targets from 'aws-cdk-lib/aws-events-targets'
import * as constants from './constants'

export interface DeploymentPipelineTriggerStackProps extends cdk.StackProps {
    triggerModelDeploy: lambda.Function
}

export class DeploymentPipelineTriggerStack extends cdk.Stack {
    constructor(scope: cdk.App, id: string, props: DeploymentPipelineTriggerStackProps) {
        super(scope, id, props)

        const modelApprovedPackageStateChange = {
            "detail-type": ["SageMaker Model Package State Change"],
            "source": ["aws.sagemaker"],
            "detail": {
                "ModelPackageGroupName": [constants.MODEL_PACKAGE_NAME],
                "ModelApprovalStatus": ["Approved"]
            }
        };
     
        const rule = new events.Rule(this, 'EventRule', {
            eventPattern: modelApprovedPackageStateChange,
            ruleName: 'ModelPackageStateChangeRule',
        });
        rule.addTarget(new targets.LambdaFunction(props.triggerModelDeploy))
    }
}
