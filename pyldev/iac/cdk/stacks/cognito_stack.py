from aws_cdk import (
    Stack,
    aws_cognito as cognito,
    Duration,
)
from constructs import Construct

class CognitoStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Cognito User Pool
        self.user_pool = cognito.UserPool(
            self, "UserPool",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            password_policy=cognito.PasswordPolicy(
                min_length=12,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
            ),
        )

        # User Pool Client for your app
        self.user_pool_client = self.user_pool.add_client(
            "AppClient",
            generate_secret=True,
            auth_flows=cognito.AuthFlow(
                user_password=True,
                admin_user_password=True,
                custom=True,
            ),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(implicit_code_grant=True),
                scopes=[cognito.OAuthScope.EMAIL, cognito.OAuthScope.OPENID],
                callback_urls=["https://api.sav.hyper-rag.com/callback"],
            ),
            access_token_validity=Duration.hours(1),
        )

        # Export outputs
        self.export_value(self.user_pool.user_pool_id, name="UserPoolId")
        self.export_value(self.user_pool_client.user_pool_client_id, name="UserPoolClientId")