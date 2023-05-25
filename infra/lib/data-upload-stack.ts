import * as cdk from 'aws-cdk-lib';
import * as path from 'path';
import * as s3 from 'aws-cdk-lib/aws-s3'
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment'
import * as utility from './utility'
import * as fs from 'fs';
import assert = require('assert');

const RAW = "raw"
const SENTIMENT_FILE_NAME = "sentiment.zip"
const SENTIMENT_URL = "https://static.us-east-1.prod.workshops.aws/public/40de25f9-f9de-4fba-8871-0bf4761d175e/static/resources/finserv/sentiment.zip"
const SENTIMENT_FILE_SHA256SUM = "784cd852f324670fe324a65dc52a67d1f72d05f87677c0f487517b45fc1adc2d"

export interface DataUploadStackProps extends cdk.StackProps {
    dataBucket: s3.Bucket
}

export class DataUploadStack extends cdk.Stack {
    constructor(scope: cdk.App, id: string, props: DataUploadStackProps) {
        super(scope, id, props)

        const filePath = path.join(__dirname, "..", "data", SENTIMENT_FILE_NAME)
        const foundChecksum = utility.computeSHA256Sync(filePath)
        this.verifyFileIntegrity({
            foundChecksum,
            expectedChecksum: SENTIMENT_FILE_SHA256SUM,
            filePath,
        });
        if (!fs.existsSync(filePath)) {
            utility.downloadFileSync(SENTIMENT_URL, filePath)
        }

        new s3deploy.BucketDeployment(this, `Deploy-${SENTIMENT_FILE_NAME}`, {
            sources: [s3deploy.Source.asset(filePath)],
            destinationBucket: props.dataBucket,
            destinationKeyPrefix: RAW,
        })
    }

    private verifyFileIntegrity({foundChecksum, expectedChecksum, filePath} : verifyFileIntegrityProps) {
        assert(foundChecksum == expectedChecksum,
            `found=${foundChecksum} != expected=${SENTIMENT_FILE_SHA256SUM},
                can you trust ${filePath} ?`);
    }
}

interface verifyFileIntegrityProps {
    foundChecksum: string
    expectedChecksum: string
    filePath: string
}
