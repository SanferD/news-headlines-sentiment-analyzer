import * as iam from 'aws-cdk-lib/aws-iam'
import * as cdk from 'aws-cdk-lib';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { DockerImageAsset } from 'aws-cdk-lib/aws-ecr-assets';
import * as utility from './utility'
import * as path from 'path'
import * as logs from 'aws-cdk-lib/aws-logs'

const APPLICATION_DIRECTORY = path.join("..", "application")
const PORT = 80
const LOG_GROUP_NAME = "EcsApplicationLogs"

export class EcsApplicationStack extends cdk.Stack {
  constructor(scope: cdk.App, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const defaultVpc = utility.getDefaultVpc(this)

    // Create cluster
    const cluster = new ecs.Cluster(this, 'Cluster', {
      vpc: defaultVpc
    });

    // Create ECR asset
    const imageAsset = new DockerImageAsset(this, 'DockerImageAsset', {
      directory: APPLICATION_DIRECTORY,
    });

    // Log group for ECS logs
    const logGroup = new logs.LogGroup(this, "LogGroup", {
        logGroupName: LOG_GROUP_NAME,
    })

    // Create Task definition
    const taskDefinition = new ecs.FargateTaskDefinition(this, 'FargetTaskDefinition');

    const container = taskDefinition.addContainer('Container', {
      image: ecs.ContainerImage.fromDockerImageAsset(imageAsset),
      memoryLimitMiB: 512,
      cpu: 256,
      logging: new ecs.AwsLogDriver({
        streamPrefix: "EcsApplication",
        logGroup: logGroup,
        }),
    });

    container.addPortMappings({
      containerPort: PORT,
    });

    // Configure task permission
    taskDefinition.taskRole.addToPrincipalPolicy(new iam.PolicyStatement({
      actions: ['sagemaker:InvokeEndpoint'],
      resources: ['*'],
    }));


    // Create security group
    const lbSecurityGroup = new ec2.SecurityGroup(this, 'SecurityGroup', {
      vpc: defaultVpc,
      allowAllOutbound: true,
    });
    lbSecurityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(PORT));

    // Create Fargate service
    const service = new ecs.FargateService(this, 'FargateService', {
      cluster: cluster,
      taskDefinition: taskDefinition,
      desiredCount: 2,
      assignPublicIp: true,
      securityGroups: [lbSecurityGroup],
    });

    // Create load balancer
    const loadBalancer = new elbv2.ApplicationLoadBalancer(this, 'ApplicationLoadBalancer', {
      vpc: defaultVpc,
      internetFacing: true,
      securityGroup: lbSecurityGroup
    });


    // Create target group to Farget service
    const targetGroup = new elbv2.ApplicationTargetGroup(this, 'ApplicationTargetGroup', {
      vpc: defaultVpc,
      port: PORT,
      targets: [service],
      targetType: elbv2.TargetType.IP,
    });

    // Add listener
    loadBalancer.addListener('Listener', {
      port: PORT,
      defaultTargetGroups: [targetGroup]
    });

  }
}
