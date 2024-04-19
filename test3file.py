import boto3
import logging
import json
import os
import certifi
from opensearchpy import OpenSearch, RequestsHttpConnection, exceptions

# Reset logging configuration to enable proper tagging of the functions logs
root = logging.getLogger()
if root.handlers:
    for handler in root.handlers:
        root.removeHandler(handler)
log_format = '%(levelname)s - %(message)s'
logging.basicConfig(format=log_format, level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

security_api = '/_opendistro/_security/api'

sm_client = boto3.client('secretsmanager')

class InvalidUserCredentials(Exception):
    """ Raise if connection to a cluster with user credentials failed """

class InvalidUserPermissions(Exception):
    """ Raise if connection to a cluster with user credentials failed """

def lambda_handler(event, context):
    """Secrets Manager secret rotation for OpenSearch
    
    The function expects a JSON-formatted OpenSearch credential secret with the following keys:
        'endpoint': OpenSearch cluster endpoint, e.g. mycluster.domain.com
        'login': user login
        'password': user password
    
    If a secret stores cluster admin credentials the 'master_secret' key value must be set to 'self'.

    Args:
        event (dict): Lambda dictionary of event parameters. These keys must include the following:
            - SecretId: The secret ARN or identifier
            - ClientRequestToken: The ClientRequestToken of the secret version
            - Step: The rotation step (one of createSecret, setSecret, testSecret, or finishSecret)
        context (LambdaContext): The Lambda runtime information
    
    Raises:
        ResourceNotFoundException: If the secret with the specified arn and stage does not exist
        ValueError: If the secret is not properly configured for rotation
        KeyError: If the event parameters do not contain the expected keys
    
    """

    arn = event['SecretId']
    token = event['ClientRequestToken']
    step = event['Step']

    logger.info(f"Secret: {arn}")
    logger.info(f"Rotation test stage: {step}")
