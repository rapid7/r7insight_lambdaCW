import logging
import json
import socket
import ssl
import certifi
import os
from uuid import UUID
import base64
import zlib
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info('Loading function...')

REGION = os.environ.get('region')
ENDPOINT = f'{REGION}.data.logs.insight.rapid7.com'
PORT = 20000
FAKE_NEWLINE = u'\u2028'


def treat_message(message):
    """
    Replace newline characters in the supplied message with "fake"
    unicode line breaks (\u2028), so that the message can be sent
    as a single log event.
    """
    return message.replace('\n', FAKE_NEWLINE)


def lambda_handler(event, context):
    token = get_token()
    sock = create_socket()

    if not validate_uuid(token):
        logger.critical(f'{token} is not a valid token. Exiting.')
        raise SystemExit
    else:
        cw_data = base64.b64decode(event['awslogs']['data'])
        cw_logs = zlib.decompress(cw_data, 16+zlib.MAX_WBITS)
        log_events = json.loads(cw_logs)
        logger.info('Received log stream...')
        logger.info(log_events)
        for log_event in log_events['logEvents']:
            # look for extracted fields, if not present, send plain message
            try:
                msg = f"{token} {json.dumps(log_event['extractedFields'])}\n"
                sock.sendall(msg.encode('utf-8'))
            except KeyError:
                treated_msg = treat_message(log_event['message'])
                msg = f"{token} {treated_msg}\n"
                sock.sendall(msg.encode('utf-8'))

    sock.close()
    logger.info('Function execution finished.')


def create_socket():
    logger.info('Creating SSL socket')
    s_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s = ssl.wrap_socket(
        sock=s_,
        keyfile=None,
        certfile=None,
        server_side=False,
        cert_reqs=ssl.CERT_REQUIRED,
        ssl_version=getattr(
            ssl,
            'PROTOCOL_TLSv1_2',
            ssl.PROTOCOL_TLSv1
        ),
        ca_certs=certifi.where(),
        do_handshake_on_connect=True,
        suppress_ragged_eofs=True,
    )
    try:
        logger.info(f'Connecting to {ENDPOINT}:{PORT}')
        s.connect((ENDPOINT, PORT))
        return s
    except socket.error as exc:
        logger.error(f'Exception socket.error : {exc}')


def validate_uuid(uuid_string):
    try:
        val = UUID(uuid_string)
    except Exception as uuid_exc:
        logger.error(f'Can not validate token: {uuid_exc}')
        return False
    return val.hex == uuid_string.replace('-', '')


def get_token():
    token_secret_name = os.environ.get('token_secret_name')
    if token_secret_name:
        sm_client = boto3.client("secretsmanager")
        return sm_client.get_secret_value(SecretId=token_secret_name)["SecretString"]
    else:
        return os.environ.get('token')
