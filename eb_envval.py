#!/usr/bin/python
# coding: utf-8

DOCUMENTATION = '''
---
module: eb_envval
short_description: Control Elastic Beanstalks environment variables
description:
    - Control Elastic Beanstalks environment variables
options:
author:
    - "Ryo Manzoku (@rmanzoku)"
extends_documentation_fragment: aws
'''

EXAMPLES = '''
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

    changed = False

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
            "Namespace": "aws:elasticbeanstalk:application:environment" ,
            "OptionName": x,
            "Value": desired_envval[x]
        }
        for x in desired_envval.keys()
    ]

    # varidate
    try:
        res = conn.validate_configuration_settings(
            ApplicationName=application,
            EnvironmentName=environment,
            OptionSettings=option_settings
        )

    except ClientError as ex:
        module.fail_json(msg=ex.response['Error']['Message'])

    # Update
    try:
        res = conn.update_environment(
            ApplicationName=application,
            EnvironmentName=environment,
            OptionSettings=option_settings
        )

    except ClientError as ex:
        module.fail_json(msg=ex.response['Error']['Message'])

    module.exit_json(changed=True)


if __name__ == '__main__':
    main()
