from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_ec2 as ec2,
    Duration,
)
from constructs import Construct
import os

class LambdaStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc: ec2.Vpc,
        lambda_sg: ec2.SecurityGroup,
        users_table_name: str,
        app_data_table_name: str,
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)

        lambda_role = iam.Role(
            self, "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaVPCAccessExecutionRole"
                ),
            ],
        )

        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "cognito-idp:ListUsers",
                    "cognito-idp:AdminGetUser",
                    "cognito-idp:InitiateAuth",
                ],
                resources=[f"arn:aws:cognito-idp:*:*:userpool/*"],
            )
        )

        # Reference lambda code from root lambda/ folder
        self.handle_users_login = lambda_.Function(
            self, "HandleUsersLogin",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset("../../lambda/handle_users_login"),
            # role=lambda_role,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            security_groups=[lambda_sg],
            environment={
                "CLIENT_ID": os.environ.get("CLIENT_ID", ""),
                "USER_POOL_ID": os.environ.get("USER_POOL_ID", ""),
            },
            timeout=Duration.seconds(30),
            memory_size=256,
        )
