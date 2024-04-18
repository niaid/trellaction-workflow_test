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
    logger.info(f"Rotation stage: {step}")

    # Make sure the version is staged correctly
    metadata = sm_client.describe_secret(SecretId=arn)
    if not metadata['RotationEnabled']:
        logger.error(f"Secret {arn} is not enabled for rotation")
        raise ValueError(f"Secret {arn} is not enabled for rotation")
    versions = metadata['VersionIdsToStages']
    if token not in versions:
        logger.error(f"Secret version {token} has no stage for rotation of secret {arn}.")
        raise ValueError(f"Secret version {token} has no stage for rotation of secret {arn}.")
    if "AWSCURRENT" in versions[token]:
        logger.info(f"Secret version {token} already set as AWSCURRENT for secret {arn}.")
        return
    elif "AWSPENDING" not in versions[token]:
        logger.error(f"Secret version {token} not set as AWSPENDING for rotation of secret {arn}.")
        raise ValueError(f"Secret version {token} not set as AWSPENDING for rotation of secret {arn}.")

    if step == "createSecret":
        create_secret(sm_client, arn, token)
    elif step == "setSecret":
        set_secret(sm_client, arn, token)
    elif step == "testSecret":
        test_secret(sm_client, arn, token)
    elif step == "finishSecret":
        finish_secret(sm_client, arn, token)
    else:
        raise ValueError("Invalid step parameter")


def create_secret(sm_client, arn, token):
    """Create the secret

    This method first checks for the existence of a secret for the passed in token. If one does not exist, it will generate a
    new secret and put it with the passed in token.

    Args:
        sm_client (client): The Secrets Manager service client
        arn (string): The secret ARN or other identifier
        token (string): The ClientRequestToken associated with the secret version
    Raises:
        ResourceNotFoundException: If the secret with the specified arn and stage does not exist.

    """
    
    # Make sure the current secret exists
    current_dict = get_secret_dict(sm_client, arn, "AWSCURRENT")

    logger.info(f"Starting OpenSearch password and secret rotation\n\nCluster: {current_dict['endpoint']}\nUser: {current_dict['login']}")
    
    # Check if the AWSPENDING version already exists by trying to retrieve it. If that fails, create a new secret version
    try:
        get_secret_dict(sm_client, arn, "AWSPENDING", token)
        logger.info(f"Successfully retrieved secret for {arn}.")
    except sm_client.exceptions.ResourceNotFoundException:
        # Get exclude characters from environment variable
        exclude_characters = os.environ['EXCLUDE_CHARACTERS'] if 'EXCLUDE_CHARACTERS' in os.environ else '/@"\'\\'
        # Generate a random password and update the secret with it
        passwd = sm_client.get_random_password(ExcludeCharacters=exclude_characters)
        secret_string = current_dict
        secret_string['password'] = passwd['RandomPassword']
        # Put the new secret version as Pending
        sm_client.put_secret_value(
            SecretId=arn,
            ClientRequestToken=token,
            SecretString=json.dumps(secret_string),
            VersionStages=['AWSPENDING']
        )
        logger.info(f"Successfully put secret for ARN {arn} and version {token}.")


def set_secret(sm_client, arn, token):
    """Set the secret
    
    Connect to the OpenSearch cluster using the login and password value stored in the AWSCURRENT secret version
    and update the OpenSearch password to the AWSPENDING value.

    Args:
        sm_client (client): The Secrets Manager service client
        arn (string): The secret ARN or other identifier
        token (string): The ClientRequestToken associated with the secret version.

    """

    pending_dict = get_secret_dict(sm_client, arn, "AWSPENDING", token)
    current_dict = get_secret_dict(sm_client, arn, "AWSCURRENT")

    logger.info(f"Updating OpenSearch password for user \'{current_dict['login']}\', cluster \'{current_dict['endpoint']}\'")
    opensearch_conn = opensearch_connect(current_dict['endpoint'], current_dict['login'], current_dict['password'])
    # Update the cluster user password with the value from the pending secret
    update_opensearch_password(opensearch_conn, current_dict['login'], current_dict['password'], pending_dict['password'])


def test_secret(sm_client, arn, token):
    """ Test the secret

    Connect to the OpenSearch cluster with the updated user password
    
    Args:
        sm_client (client): The Secrets Manager service client
        arn (string): The secret ARN or other identifier
        token (string): The ClientRequestToken associated with the secret version

    """
    
    pending_dict = get_secret_dict(sm_client, arn, "AWSPENDING", token)
    try:
        opensearch_connect(pending_dict['endpoint'], pending_dict['login'], pending_dict['password'])
    except:
        logger.critical(f"ERROR - failed to update the OpenSearch credentials and secret for user \'{pending_dict['login']}\'")
        raise

def finish_secret(sm_client, arn, token):
    """Finish the secret

    Finalize the rotation process by marking the AWSPENDING secret version as AWSCURRENT.
    
    Args:
        sm_client (client): The Secrets Manager service client
        arn (string): The secret ARN or other identifier
        token (string): The ClientRequestToken associated with the secret version
    Raises:
        ResourceNotFoundException: If the secret with the specified arn does not exist

    """
    # First describe the secret to get the current version
    metadata = sm_client.describe_secret(SecretId=arn)
    current_version = None
    for version in metadata["VersionIdsToStages"]:
        if "AWSCURRENT" in metadata["VersionIdsToStages"][version]:
            if version == token:
                # The correct version is already marked as current, return
                logger.info(f"finishSecret: Version {version} already marked as AWSCURRENT for {arn}")
                return
            current_version = version
            break
    # Finalize by staging the secret version current
    sm_client.update_secret_version_stage(SecretId=arn, VersionStage="AWSCURRENT", MoveToVersionId=token, RemoveFromVersionId=current_version)
    current_dict = get_secret_dict(sm_client, arn, "AWSCURRENT")
    msg = f"Successfully updated the OpenSearch credentials and secret for the user \'{current_dict['login']}\'."
    logger.info(msg)

""" Helper functions """

def get_secret_dict(sm_client, arn, stage, token=None):
    """ Get secret value dictionary
    
    Args:
        sm_client (client): The Secrets Manager service client
        arn (string): The secret ARN or other identifier
        stage: Secret version stage
        token (string): The ClientRequestToken associated with the secret version
    Raises:
        KeyError: If the secret dictionary does not contain the required keys

    """

    required_fields = ['endpoint', 'login', 'password']
    # Only do VersionId validation against the stage if a token is passed in
    if token:
        secret = sm_client.get_secret_value(SecretId=arn, VersionId=token, VersionStage=stage)
    else:
        secret = sm_client.get_secret_value(SecretId=arn, VersionStage=stage)
    secret_dict = json.loads(secret['SecretString'])
    # Run validations against the secret
    for field in required_fields:
        if field not in secret_dict:
            raise KeyError(f"{field} key is missing from secret JSON")
    # Parse and return the secret JSON string
    return secret_dict

def opensearch_connect(host: str, user: str, password: str):
    """ Connect to the OpenSearch cluster

    Args:
        host: cluster hostname
        user: cluster login
        password: user password
    
    """

    logger.info(f"Connecting to OpenSearch domain endpoint '{host}' as '{user}'")
    try:
        client = OpenSearch(
            hosts = [{'host': host, 'port': 443}],
            http_auth = (user, password),
            use_ssl = True,
            verify_certs = True,
            connection_class = RequestsHttpConnection,
            timeout=60
            )
    except exceptions.AuthenticationException as e:
        logger.error(e)
        return "AuthenticationException"
    except exceptions.AuthorizationException as e:
        logger.error(e)
        return "AuthorizationException"
    except Exception as e:
        logger.error(e)
        return "Exception"
    else:
        logger.info("Success!")
        return client

def update_opensearch_password(client: OpenSearch, user: str, old_password: str, new_password: str):
    """  Update OpenSearch user password

    Args:
        client: OpenSearch client object
        user: OpenSearch user name
        old_password: current password
        new_password: new password
    
    """

    logger.info(f'Updating password for user {user}')
    body = {
        "current_password": old_password,
        "password": new_password
    }
 
    try:
        client.security.change_password(body=body)
    except Exception as e:
        logger.error(e)
    else:
        logger.info(f"Success - password updated")

def delete_secret(secret):
    logger.info(f"Deleting the secret {secret}")
    days_to_recover = 30
    try:
        sm_client.delete_secret(SecretId=secret, RecoveryWindowInDays=days_to_recover)
    except Exception as e:
        return e
    else:
        return f"The secret {secret} has been deleted. If it was a mistake you can recover it within {days_to_recover} days."



