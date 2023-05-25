import * as cdk from 'aws-cdk-lib';
import * as sagemaker from 'aws-cdk-lib/aws-sagemaker'
import * as utility from './utility'
import * as iam from 'aws-cdk-lib/aws-iam'
import * as s3 from 'aws-cdk-lib/aws-s3'

const DOMAIN_NAME = "news-headlines"

export interface SagemakerSetupStackProps extends cdk.StackProps {
    dataBucket: s3.Bucket
}

export class SagemakerSetupStack extends cdk.Stack {
    readonly domain: sagemaker.CfnDomain
    readonly executionRole: iam.Role

    constructor(scope: cdk.App, id: string, props: SagemakerSetupStackProps) {
        super(scope, id, props);

        const defaultVpc = utility.getDefaultVpc(this)
        const publicSubnetIds = defaultVpc.publicSubnets.map(subnet => subnet.subnetId)

        this.executionRole = this.createExecutionRole(props.dataBucket)
        this.domain = new sagemaker.CfnDomain(this, "Domain", {
            authMode: "IAM",
            defaultUserSettings: {
                executionRole: this.executionRole.roleArn,
            },
            domainName: DOMAIN_NAME,
            subnetIds: publicSubnetIds,
            vpcId: defaultVpc.vpcId,
        })
        this.createUserProfile("myuser")
    }

    createExecutionRole(sagemakerBucket: s3.Bucket): iam.Role {
        const role = new iam.Role(this, "ExecutionRole", {
            assumedBy: new iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managedPolicies: [
                iam.ManagedPolicy.fromAwsManagedPolicyName("AmazonSageMakerFullAccess")
            ]
        })
        sagemakerBucket.grantReadWrite(role)
        return role
    }

    createUserProfile(username: string) {
        new sagemaker.CfnUserProfile(this, `UserProfile-${username}`, {
            domainId: this.domain.attrDomainId,
            userProfileName: username,
            userSettings: {
                executionRole: this.executionRole.roleArn,
            }
        })
    }

}
