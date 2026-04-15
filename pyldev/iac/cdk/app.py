
from dotenv import load_dotenv
from pathlib import Path
import os

from aws_cdk import App
from aws_cdk import Environment

from stacks.vpc_stack import VpcStack
from stacks.cognito_stack import CognitoStack
from stacks.dynamodb_stack import DynamoDbStack
from stacks.lambda_stack import LambdaStack
from stacks.api_gateway_stack import ApiGatewayStack
from stacks.s3_cloudfront_stack import S3CloudFrontStack
from stacks.route53_stack import Route53Stack


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

env = Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"),
    region=os.getenv("CDK_DEFAULT_REGION"),
)
app = App()

vpc_stack = VpcStack(app, "VpcStack", env=env)

cognito_stack = CognitoStack(app, "CognitoStack", env=env)

dynamodb_stack = DynamoDbStack(app, "DynamoDbStack", env=env)

lambda_stack = LambdaStack(
    app, "LambdaStack",
    vpc=vpc_stack.vpc,
    lambda_sg=vpc_stack.lambda_sg,
    users_table_name=dynamodb_stack.users_table.table_name,
    app_data_table_name=dynamodb_stack.app_data_table.table_name,
    env=env)

api_stack = ApiGatewayStack(
    app, "ApiGatewayStack",
    api_lambda=lambda_stack.handle_users_login,
    env=env)

# S3 + CloudFront
s3_stack = S3CloudFrontStack(app, "S3CloudFrontStack", env=env)

# Route 53 (cross-account)
route53_stack = Route53Stack(
    app, "Route53Stack",
    distribution=s3_stack.distribution,
    hosted_zone_id=os.getenv("HOSTED_ZONE_ID", ""),  
    hosted_zone_name=os.getenv("HOSTED_ZONE_NAME", ""),
    env=env)

app.synth()