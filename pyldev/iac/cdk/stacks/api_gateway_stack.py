from aws_cdk import (
    Stack,
    aws_apigateway as apigw,
    aws_lambda as lambda_,
)
from constructs import Construct

class ApiGatewayStack(Stack):
    def __init__(
    self,
    scope: Construct,
    id: str,
    api_lambda: lambda_.IFunction,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_origins=["*"],
    **kwargs
    ):
        super().__init__(scope, id, **kwargs)

        api = apigw.RestApi(
            self, "Api",
            endpoint_types=[apigw.EndpointType.REGIONAL],
            description="API",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_methods=allow_methods,
                allow_origins=allow_origins,
            )
        )
        root = api.root

        auth = root.add_resource("auth")
        auth.add_method(
            "POST",
            apigw.LambdaIntegration(api_lambda),
        )

        api_resource = root.add_resource("api")
        api_resource.add_method(
            "GET",
            apigw.LambdaIntegration(api_lambda),
        )

        api_resource.add_method(
            "POST",
            apigw.LambdaIntegration(api_lambda),
        )

        self.api = api
        self.export_value(api.rest_api_id, name="ApiGatewayId")