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
    """
    Process Kinesis Data Stream records containing CloudWatch log data
    """
    token = get_token()
    
    if not validate_uuid(token):
        logger.critical(f'{token} is not a valid token. Exiting.')
        raise SystemExit
    
    sock = create_socket()
    logger.info('Socket created successfully')
    failed_records = []
    
    try:
        # Process each Kinesis record in the batch
        for record in event['Records']:
            try:
                # Kinesis data is base64 encoded
                kinesis_data = base64.b64decode(record['kinesis']['data'])
                
                # The data from CloudWatch is still compressed
                cw_logs = zlib.decompress(kinesis_data, 16+zlib.MAX_WBITS)
                log_events = json.loads(cw_logs)
                
                log_group = log_events.get("logGroup", "unknown")
                log_stream = log_events.get("logStream", "unknown")
                logger.info(f'Processing record with {len(log_events.get("logEvents", []))} log events from log group: {log_group}, log stream: {log_stream}')
                
                # Process each log event within this Kinesis record
                log_events_list = log_events.get('logEvents', [])
                for idx, log_event in enumerate(log_events_list):
                    try:
                        # look for extracted fields, if not present, send plain message
                        if 'extractedFields' in log_event:
                            msg = f"{token} {json.dumps(log_event['extractedFields'])}\n"
                            logger.debug(f'Sending extracted fields: {json.dumps(log_event["extractedFields"])}')
                        else:
                            treated_msg = treat_message(log_event['message'])
                            msg = f"{token} {treated_msg}\n"
                            logger.debug(f'Sending log message: {log_event["message"][:200]}{"..." if len(log_event["message"]) > 200 else ""}')
                        
                        # Log the actual message being sent (truncated for readability)
                        # Sample logging: show first 3, last 3, and every 10th message for large batches
                        should_log = (idx < 3 or 
                                    idx >= len(log_events_list) - 3 or 
                                    idx % 10 == 0 or 
                                    len(log_events_list) <= 10)
                        
                        if should_log:
                            msg_preview = msg.replace(token, "[TOKEN]")[:300] + ("..." if len(msg) > 300 else "")
                            logger.info(f'Sending to Rapid7 [{idx+1}/{len(log_events_list)}]: {msg_preview}')
                        
                        sock.sendall(msg.encode('utf-8'))
                        
                    except Exception as log_error:
                        logger.error(f'Failed to process individual log event: {log_error}')
                        # Continue processing other log events
                        
            except Exception as record_error:
                logger.error(f'Failed to process Kinesis record {record["kinesis"]["sequenceNumber"]}: {record_error}')
                failed_records.append({
                    'itemIdentifier': record['kinesis']['sequenceNumber'],
                    'errorCode': 'ProcessingError',
                    'errorMessage': str(record_error)
                })
    
    finally:
        sock.close()
    
    # Calculate total log events processed
    total_log_events = 0
    successful_records = len(event["Records"]) - len(failed_records)
    
    for record in event["Records"]:
        try:
            kinesis_data = base64.b64decode(record['kinesis']['data'])
            cw_logs = zlib.decompress(kinesis_data, 16+zlib.MAX_WBITS)
            log_events = json.loads(cw_logs)
            total_log_events += len(log_events.get('logEvents', []))
        except:
            pass  # Already handled in main processing loop
    
    logger.info(f'Function execution finished. Processed {successful_records}/{len(event["Records"])} Kinesis records successfully, {total_log_events} total log events, {len(failed_records)} records failed.')
    
    # Return partial batch failure response if there were failures
    if failed_records:
        return {
            'batchItemFailures': failed_records
        }
    
    return {'statusCode': 200}


def create_socket():
    logger.info('Creating SSL socket')
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(certifi.where())

    s_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s = context.wrap_socket(
        sock=s_,
        server_side=False,
        do_handshake_on_connect=True,
        suppress_ragged_eofs=True,
        server_hostname=ENDPOINT,
    )

    # Retry logic to handle connection errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f'Connecting to {ENDPOINT}:{PORT} (attempt {attempt + 1}/{max_retries})')
            s.connect((ENDPOINT, PORT))
            return s
        except socket.error as exc:
            if attempt == max_retries - 1:
                logger.error(f'Failed to connect after {max_retries} attempts. Final exception: {exc}')
                raise # Raise the exception to the caller
            else:
                logger.warning(f'Connection attempt {attempt + 1} failed: {exc}. Retrying...')


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
        secret_value = sm_client.get_secret_value(SecretId=token_secret_name)["SecretString"]
        # Parse JSON and extract R7TOKEN
        secret_data = json.loads(secret_value)
        r7_token = secret_data.get("R7TOKEN")
        if r7_token:            
            if ":" in r7_token:
                return r7_token.split(":", 1)[1]  # Return everything after the first ":"
            return r7_token
        else:
            logger.error("R7TOKEN not found in secret")
            return None
    else:
        return os.environ.get('token')
