#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { SagemakerDataBucketStack as DataBucketStack } from '../lib/data-bucket-stack';
import { SagemakerModelPipelineStack } from '../lib/sagemaker-model-pipeline-stack';
import { DataUploadStack } from '../lib/data-upload-stack';
import { SagemakerSetupStack } from '../lib/sagemaker-setup-stack';

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