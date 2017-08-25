#!/usr/bin/python
# coding: utf-8

DOCUMENTATION = '''
---
module: eb_envval
short_description: Control Elastic Beanstalks environment variables
description:
    - Control Elastic Beanstalks environment variables
options:
  application:
    description: Application name
    required: true
  environment:
    description: Enviromnent name
    required: true
  envval:
    description: Envronment variable key and value
    required: true
author:
    - "Ryo Manzoku (@rmanzoku)"
extends_documentation_fragment: aws
'''

EXAMPLES = '''
tasks:
  - name: Set environment values
    eb_envval:
      application: example
      environment: example-production
      envval:
        BUNDLE_WITHOUT: "test:development"
        PASSENGER_MAX_POOL_SIZE: "2"
        PASSENGER_MIN_INSTANCES: "10"
        RACK_ENV: "production"
        RAILS_ENV: "production"
        RAILS_SKIP_ASSET_COMPILATION: "true"
        RAILS_SKIP_MIGRATIONS: "true"
'''

try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

try:
    from botocore.exceptions import ClientError, NoCredentialsError
    HAS_BOTOCORE = True
except ImportError:
    HAS_BOTOCORE = False

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ec2 import ec2_argument_spec, boto3_conn, get_aws_connection_info


def main():

    argument_spec = ec2_argument_spec()
    argument_spec.update(
        dict(
            application=dict(type='str', required=True),
            environment=dict(type='str', required=True),
            envval=dict(type='dict', required=True),
        )
    )

    module = AnsibleModule(argument_spec=argument_spec)

    application = module.params['application']
    environment = module.params['environment']
    desired_envval = module.params['envval']

    for v in desired_envval.values():
        if not isinstance(v, str):
            module.fail_json(msg="envval dict must be string")

    if not HAS_BOTO3:
        module.fail_json(msg='boto3 required for this module')
    if not HAS_BOTOCORE:
        module.fail_json(msg='botocore required for this module')

    # Connect to AWS
    try:
        region, ec2_url, aws_connect_kwargs = get_aws_connection_info(module, boto3=True)
        conn = boto3_conn(module, conn_type="client", resource="elasticbeanstalk", region=region,
                          **aws_connect_kwargs)
    except NoCredentialsError as ex:
        module.fail_json(msg=ex.message)

    # Check current envvals
    try:
        res = conn.describe_configuration_settings(
                ApplicationName=application,
                EnvironmentName=environment
        )

    except ClientError as ex:
        module.fail_json(msg=ex.response['Error']['Message'])

    current_envval = {
        str(x['OptionName']): str(x['Value'])
        for x in res['ConfigurationSettings'][0]['OptionSettings']
        if x['Namespace'] == "aws:elasticbeanstalk:application:environment"
    }

    # The desired envvals is same as current envvals
    if current_envval == desired_envval:
        module.exit_json(changed=False)

    # Update envval
    option_settings = [
        {
            "Namespace": "aws:elasticbeanstalk:application:environment",
            "OptionName": x,
            "Value": desired_envval[x]
        }
        for x in desired_envval.keys()
    ]

    options_to_remove = None
    revoke_envval = list(set(current_envval.keys()) - set(desired_envval.keys()))

    if revoke_envval != 0:
        options_to_remove = [
            {
                "Namespace": "aws:elasticbeanstalk:application:environment",
                "OptionName": x
            }
            for x in revoke_envval
        ]

    # Update
    try:
        res = conn.update_environment(
            ApplicationName=application,
            EnvironmentName=environment,
            OptionSettings=option_settings,
            OptionsToRemove=options_to_remove
        )

    except ClientError as ex:
        module.fail_json(msg=ex.response['Error']['Message'])

    module.exit_json(changed=True)


if __name__ == '__main__':
    main()
