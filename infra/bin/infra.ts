#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { SagemakerDataBucketStack as DataBucketStack } from '../lib/data-bucket-stack';
import { SagemakerModelPipelineStack } from '../lib/sagemaker-model-pipeline-stack';
import { DataUploadStack } from '../lib/data-upload-stack';
import { SagemakerSetupStack } from '../lib/sagemaker-setup-stack';
import { DeploymentPipelineLambdasStack } from '../lib/deployment-pipeline-lambdas-stack';
import { DeploymentPipelineStack } from '../lib/deployment-pipeline-stack';
import { DeploymentPipelineTriggerStack } from '../lib/deployment-pipeline-trigger-stack';

interface StackProps {
  env: {account: string, region: string}
}

interface createStacksProps {
  app: cdk.App
  stackProps: StackProps
}

function createStacks({app, stackProps} : createStacksProps) {
  
  const dataBucketStack = new DataBucketStack(app, 'DataBucketStack', {
    ...stackProps,
  });

  const dataUploadStack = new DataUploadStack(app, "DataUploadStack", {
    ...stackProps,
    dataBucket: dataBucketStack.dataBucket,
  })

  const sagemakerSetupStack = new SagemakerSetupStack(app, "SagemakerSetupStack", {
    ...stackProps,
    dataBucket: dataBucketStack.dataBucket,
  })

  const sagemakerModelPipelineStack = new SagemakerModelPipelineStack(app, 'SagemakerModelPipelineStack', {
    ...stackProps,
    dataBucket: dataBucketStack.dataBucket,
  })
  sagemakerModelPipelineStack.addDependency(dataUploadStack)
  sagemakerModelPipelineStack.addDependency(sagemakerSetupStack)

  const deploymentPipelineLambdasStack = new DeploymentPipelineLambdasStack(app, "DeploymentPipelineLambdasStack", {
    ...stackProps,
    dataBucket: dataBucketStack.dataBucket,
    sagemakerExecutionRole: sagemakerSetupStack.executionRole,
  })

  const deploymentPipelineStack = new DeploymentPipelineStack(app, "DeploymentPipelineStack", {
    ...stackProps,
    createOrUpdateEndpoint: deploymentPipelineLambdasStack.createOrUpdateEndpoint,
    dataBucket: dataBucketStack.dataBucket,
  })

  const deploymentPipelineTriggerStack = new DeploymentPipelineTriggerStack(app, "DeploymentPipelineTriggerStack", {
    ...stackProps,
    triggerModelDeploy: deploymentPipelineLambdasStack.triggerModelDeploy,
  })

}

const app = new cdk.App();
const stackProps = {
  env: { 
    account: process.env.CDK_DEFAULT_ACCOUNT!, 
    region: process.env.CDK_DEFAULT_REGION!,
  }
}
createStacks({
  app,
  stackProps,
})