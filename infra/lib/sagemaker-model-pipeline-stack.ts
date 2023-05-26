import * as assert from 'assert';
import * as cdk from 'aws-cdk-lib';
import * as fs from 'fs'
import * as iam from 'aws-cdk-lib/aws-iam'
import * as path from 'path'
import * as s3 from 'aws-cdk-lib/aws-s3'
import * as sagemaker from 'aws-cdk-lib/aws-sagemaker'
import { execSync } from 'child_process'

const PIPELINE_NAME = "NEWS-HEADLINES-PIPELINE"
const SM_PIPELINE_PATH = path.join("..", "sm-pipeline");
const PIPELINE_PY_PATH = path.join(SM_PIPELINE_PATH, "pipeline.py")
const PIPELINE_JSON_PATH = path.join(SM_PIPELINE_PATH, "pipeline.json")
const DATA_BUCKET_NAME = "DataBucketName"

export interface SagemakerModelPipelineStackProps extends cdk.StackProps {
    dataBucket: s3.Bucket
}

export class SagemakerModelPipelineStack extends cdk.Stack {
    constructor(scope: cdk.App, id: string, props: SagemakerModelPipelineStackProps) {
        super(scope, id, props);
        
        // run the python script and fetch the pipeline body
        execSync(`python ${PIPELINE_PY_PATH}`)
        const pipelineDefinitionJson = fs.readFileSync(PIPELINE_JSON_PATH, 'utf-8')
        const pipelineDefinitionBody = JSON.parse(pipelineDefinitionJson)
        let foundDataBucketNameParameter = false
        pipelineDefinitionBody["Parameters"].forEach((param: any) => {
            if (param["Name"] == DATA_BUCKET_NAME) {
                param["DefaultValue"] = props.dataBucket.bucketName
                foundDataBucketNameParameter = true
            }
        });
        assert.ok(foundDataBucketNameParameter,
            `Parameter with "Name" == ${DATA_BUCKET_NAME} not in pipelineDefinition`)

        // create the model pipeline
        const role = this.createSagemakerPipelineRole(props);
        new sagemaker.CfnPipeline(this, 'ModelPipeline', {
            pipelineName: PIPELINE_NAME,
            pipelineDefinition: {
                PipelineDefinitionBody: JSON.stringify(pipelineDefinitionBody),
            },
            roleArn: role.roleArn,
        })
    }

    private createSagemakerPipelineRole(props: SagemakerModelPipelineStackProps) {
        
        // create service-linked-role for sagemaker
        const role = new iam.Role(this, "SageMakerRole", {
            assumedBy: new iam.ServicePrincipal('sagemaker.amazonaws.com'),
        });

        role.addManagedPolicy(
            iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSageMakerFullAccess')
        );

        // add full access to s3 bucket created for model pipeline
        role.addToPolicy(new iam.PolicyStatement({
            actions: ['s3:*'],
            resources: [
                props.dataBucket.bucketArn,
                `${props.dataBucket.bucketArn}/*`,
            ],
        }));
        return role;
    }
}

