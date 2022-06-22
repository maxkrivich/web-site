
import os
import aws_cdk as cdk

from cloudformation.my_site_stack import MySiteStack


DOMAIN_NAME = "kryvych.cc"
CERTIFICATE_ARN = os.environ.get("CERTIFICATE_ARN")
ACCOUNT_ID = os.environ.get("ACCOUNT_ID")
REGION = os.environ.get("REGION")

def main() -> None:
    env = cdk.Environment(
        account=ACCOUNT_ID,
        region=REGION
    )
    application = cdk.App()
    stack = MySiteStack(
        application,
        "MySiteStack",
        env=env,
        domain_name=DOMAIN_NAME,
        certificate_arn=CERTIFICATE_ARN
    )

    cdk.Tags.of(stack).add("web-site", DOMAIN_NAME)
    application.synth()


if __name__ == "__main__":
    main()
