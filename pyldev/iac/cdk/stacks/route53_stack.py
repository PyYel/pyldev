from aws_cdk import (
    Stack,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_cloudfront as cloudfront,
)
from constructs import Construct

class Route53Stack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        distribution: cloudfront.Distribution,
        hosted_zone_id: str,
        hosted_zone_name: str,
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)

        # Reference existing hosted zone in management account
        # Note: You need cross-account permissions or use delegation set
        hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
            self, "HostedZone",
            hosted_zone_id=hosted_zone_id,
            zone_name=hosted_zone_name,
        )

        # Create alias record pointing to CloudFront
        route53.ARecord(
            self, "ApiAliasRecord",
            zone=hosted_zone,
            target=route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(distribution)
            ),
            record_name="api.sav.hyper-rag",
        )

        self.export_value("https://api.sav.hyper-rag.com", name="ApiUrl")