from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
)
from constructs import Construct

class VpcStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # VPC with private subnets only (no public access directly)
        self.vpc = ec2.Vpc(
            self, "PrivateVpc",
            cidr="10.0.0.0/16",
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    name="Private",
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PUBLIC,
                    name="Public",
                    cidr_mask=24,
                ),
            ],
        )

        # Security group for Lambda
        self.lambda_sg = ec2.SecurityGroup(
            self, "LambdaSg",
            vpc=self.vpc,
            description="Security group for Lambdas",
            allow_all_outbound=True,
        )

        # Security group for DynamoDB (if accessing via VPC endpoint)
        self.dynamodb_sg = ec2.SecurityGroup(
            self, "DynamoDbSg",
            vpc=self.vpc,
            description="Security group for DynamoDB endpoint",
        )
