import aws_cdk as cdk
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_cloudfront as cf
from aws_cdk import aws_iam as iam
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as route53_targets
from aws_cdk import aws_s3 as s3
from constructs import Construct


class MySiteStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        domain_name: str,
        certificate_arn: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.bucket = self._create_bucket(domain_name)
        self.cf_oai = self._configure_iam(self.bucket, domain_name)
        self.distribution = self._create_cloudfront_distribution(
            self.bucket, self.cf_oai, domain_name, certificate_arn
        )
        self._configure_route53(domain_name)

    def _create_bucket(self, domain_name: str) -> s3.Bucket:
        bucket = s3.Bucket(
            self,
            "MySiteWebsiteBucket",
            bucket_name=domain_name,
            website_error_document="error.html",
            website_index_document="index.html",
            removal_policy=cdk.RemovalPolicy.RETAIN,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        return bucket

    def _configure_iam(
        self, bucket: s3.Bucket, domain_name: str
    ) -> cf.OriginAccessIdentity:
        cf_oai = cf.OriginAccessIdentity(
            self, "CloudfrontOAI", comment=f"Cloudfront OAI for {domain_name}"
        )

        bucket.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[bucket.arn_for_objects("*")],
                principals=[
                    iam.CanonicalUserPrincipal(
                        cf_oai.cloud_front_origin_access_identity_s3_canonical_user_id
                    )
                ],
            )
        )

        return cf_oai

    def _create_cloudfront_distribution(
        self,
        bucket: s3.Bucket,
        origin_access_identity: cf.OriginAccessIdentity,
        domain_name: str,
        certificate_arn: str,
    ) -> cf.CloudFrontWebDistribution:
        certificate = acm.Certificate.from_certificate_arn(
            self, "MySiteWebsiteCeritifcate", certificate_arn=certificate_arn
        )

        viewer_cert = cf.ViewerCertificate.from_acm_certificate(
            certificate=certificate,
            ssl_method=cf.SSLMethod.SNI,
            aliases=[domain_name, f"www.{domain_name}"],
            security_policy=cf.SecurityPolicyProtocol.TLS_V1_2_2021,
        )

        distribution = cf.CloudFrontWebDistribution(
            self,
            "MySiteCDN",
            price_class=cf.PriceClass.PRICE_CLASS_100,
            geo_restriction=cf.GeoRestriction.denylist("RU", "BY", "HU"),
            viewer_certificate=viewer_cert,
            origin_configs=[
                cf.SourceConfiguration(
                    s3_origin_source=cf.S3OriginConfig(
                        s3_bucket_source=bucket,
                        origin_access_identity=origin_access_identity,
                    ),
                    behaviors=[
                        cf.Behavior(
                            default_ttl=cdk.Duration.hours(1),
                            min_ttl=cdk.Duration.hours(1),
                            max_ttl=cdk.Duration.days(10),
                            is_default_behavior=True,
                            allowed_methods=cf.CloudFrontAllowedMethods.GET_HEAD_OPTIONS,
                            cached_methods=cf.CloudFrontAllowedCachedMethods.GET_HEAD_OPTIONS,
                        )
                    ],
                )
            ],
            default_root_object="index.html",
            http_version=cf.HttpVersion.HTTP2,
            viewer_protocol_policy=cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            error_configurations=[
                cf.CfnDistribution.CustomErrorResponseProperty(
                    error_code=404,
                    response_code=404,
                    response_page_path="/404.html",
                ),
                cf.CfnDistribution.CustomErrorResponseProperty(
                    error_code=403,
                    response_code=403,
                    response_page_path="/403.html",
                ),
            ],
        )

        return distribution

    def _configure_route53(self, domain_name: str) -> None:
        zone = route53.HostedZone.from_lookup(
            self, "MySiteWebsiteHostedZone", domain_name=domain_name
        )

        route53.ARecord(
            self,
            "MySiteWWWArecored",
            record_name=f"www.{domain_name}",
            target=route53.RecordTarget.from_alias(
                route53_targets.CloudFrontTarget(self.distribution)
            ),
            zone=zone,
        )
        route53.ARecord(
            self,
            "MySiteArecored",
            record_name=domain_name,
            target=route53.RecordTarget.from_alias(
                route53_targets.CloudFrontTarget(self.distribution)
            ),
            zone=zone,
        )

