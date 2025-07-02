import json
import base64
import datetime
import os
import logging

# Try to import opensearch_py. If not available, log an error.
# This Lambda will require this library to be packaged with it or available in a Lambda Layer.
try:
    from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
    OPENSEARCH_PY_AVAILABLE = True
except ImportError:
    OPENSEARCH_PY_AVAILABLE = False

# Logger setup
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment Variables
OPENSEARCH_ENDPOINT = os.environ.get('OPENSEARCH_ENDPOINT')
MSK_TOPIC_NAME = os.environ.get('MSK_TOPIC_NAME') # For logging/awareness, not direct use in handler
OPENSEARCH_INDEX_PREFIX = os.environ.get('OPENSEARCH_INDEX_PREFIX', 'siem-identity-logs') # Default prefix

# Global OpenSearch client (initialized in handler for better testing and context)
os_client = None

# --- Transformation Logic (copied and adapted from original transformation_lambda.py) ---
def transform_okta_log(log_data):
    tenant_id = log_data.get("tenant_id_source", "unknown_tenant")
    application_id = log_data.get("app_id_source", "unknown_app")
    event_type = "login"
    if log_data.get("event", "").lower() == "login" and log_data.get("status", "").lower() == "failure":
        event_type = "auth_failure"
    elif log_data.get("event", "").lower() == "login":
        event_type = "login"
    else:
        event_type = log_data.get("event", "unknown_event")
    return {
        "tenant_id": tenant_id, "timestamp": log_data.get("time"), "user_id": log_data.get("user"),
        "event_type": event_type, "event_status": log_data.get("status", "").lower(),
        "source_ip": log_data.get("ip"), "application_id": application_id,
        "details": log_data.get("details", {})
    }

def transform_azure_ad_log(log_data):
    tenant_id = log_data.get("tenantContextId", "unknown_tenant")
    application_id = log_data.get("applicationContextId", "unknown_app")
    event_type = "login"
    azure_action = log_data.get("action", "").lower()
    azure_result = log_data.get("result", "").lower()
    if azure_action == "auth" and azure_result == "fail": event_type = "auth_failure"
    elif azure_action == "auth": event_type = "login"
    else: event_type = azure_action
    event_status = "failure" if azure_result == "fail" else azure_result
    return {
        "tenant_id": tenant_id, "timestamp": log_data.get("timestamp"), "user_id": log_data.get("userId"),
        "event_type": event_type, "event_status": event_status, "source_ip": log_data.get("sourceIp"),
        "application_id": application_id, "details": log_data.get("properties", {})
    }
# --- End Transformation Logic ---

def get_opensearch_client():
    """Initializes and returns the OpenSearch client."""
    global os_client
    if os_client is None:
        if not OPENSEARCH_PY_AVAILABLE:
            logger.error("OpenSearch Python client (opensearch-py) not available. Cannot send data.")
            raise ImportError("opensearch-py library is required but not found.")
        if not OPENSEARCH_ENDPOINT:
            logger.error("OpenSearch endpoint not configured in environment variables (OPENSEARCH_ENDPOINT).")
            raise ValueError("OPENSEARCH_ENDPOINT environment variable is not set.")

        # Credentials will be picked up from the Lambda execution role
        # when running in AWS. For local testing, AWS CLI profile or env vars need to be set.
        # The region should ideally be dynamic or from an env var too.
        # For now, let's assume the Lambda execution role handles auth.
        # If using AWSV4SignerAuth, you need the AWS region.
        aws_region = os.environ.get('AWS_REGION', 'us-east-1') # Default if not set
        credentials = boto3.Session().get_credentials() # Requires boto3
        auth = AWSV4SignerAuth(credentials, aws_region, 'es') # 'es' for OpenSearch Service

        logger.info(f"Initializing OpenSearch client for endpoint: {OPENSEARCH_ENDPOINT}")
        os_client = OpenSearch(
            hosts=[{'host': OPENSEARCH_ENDPOINT, 'port': 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=30 # seconds
        )
    return os_client

def lambda_handler(event, context):
    logger.info(f"Received event from MSK: {json.dumps(event)[:500]}...") # Log first 500 chars

    if not OPENSEARCH_PY_AVAILABLE:
        logger.error("Critical: opensearch-py library not found. Cannot process records.")
        # Depending on Lambda config, this might retry or go to DLQ if configured.
        return {'status': 'Error', 'message': 'opensearch-py not available'}

    try:
        client = get_opensearch_client()
    except Exception as e:
        logger.error(f"Failed to initialize OpenSearch client: {e}")
        return {'status': 'Error', 'message': f"Failed to initialize OpenSearch client: {e}"}

    processed_records = 0
    failed_records = 0
    actions_for_bulk = []

    for topic, records in event.get('records', {}).items():
        logger.info(f"Processing {len(records)} records from topic: {topic}")
        for record in records:
            try:
                # MSK messages are base64 encoded
                payload_decoded_str = base64.b64decode(record['value']).decode('utf-8')
                log_entry_with_provider = json.loads(payload_decoded_str)

                provider = log_entry_with_provider.get("provider", "").lower()
                actual_log_data = log_entry_with_provider.get("log", {})

                if not actual_log_data:
                    logger.warning(f"Skipping record with missing log data: {log_entry_with_provider}")
                    failed_records += 1
                    continue

                transformed_log = None
                if provider == "okta":
                    transformed_log = transform_okta_log(actual_log_data)
                elif provider == "azure_ad":
                    transformed_log = transform_azure_ad_log(actual_log_data)
                else:
                    logger.warning(f"Unknown log provider: {provider}. Log: {actual_log_data}")
                    failed_records += 1
                    continue

                if transformed_log:
                    # Ensure timestamp is valid for OpenSearch
                    if 'timestamp' not in transformed_log or not transformed_log['timestamp']:
                        transformed_log['timestamp'] = datetime.datetime.utcnow().isoformat() + "Z"
                        logger.info(f"Generated timestamp for log without one: User {transformed_log.get('user_id')}")

                    # Prepare for OpenSearch bulk ingestion
                    # Index name can be dynamic, e.g., based on date
                    # For this PoC, using a daily index based on the event's timestamp
                    try:
                        event_dt = datetime.datetime.fromisoformat(transformed_log['timestamp'].replace('Z', '+00:00'))
                        index_name = f"{OPENSEARCH_INDEX_PREFIX}-{event_dt.strftime('%Y-%m-%d')}"
                    except Exception: # Fallback if timestamp is weird
                        index_name = f"{OPENSEARCH_INDEX_PREFIX}-{datetime.datetime.utcnow().strftime('%Y-%m-%d')}"

                    action = {"index": {"_index": index_name}}
                    actions_for_bulk.append(action)
                    actions_for_bulk.append(transformed_log)
                    processed_records += 1

            except json.JSONDecodeError as je:
                logger.error(f"JSON decoding error for record value (base64 decoded): {record.get('value')[:200]}... Error: {je}")
                failed_records +=1
            except Exception as e:
                logger.error(f"Error processing MSK record: {e}. Record: {str(record)[:200]}...")
                failed_records += 1

    if actions_for_bulk:
        logger.info(f"Attempting to bulk ingest {len(actions_for_bulk)//2} transformed records to OpenSearch.")
        try:
            response = client.bulk(body=actions_for_bulk)
            if response['errors']:
                error_count = 0
                for item in response['items']:
                    if item.get('index') and item['index'].get('error'):
                        error_count +=1
                        logger.error(f"OpenSearch bulk ingest error: {item['index']['error']}. Document: (not logged for brevity)")
                logger.error(f"OpenSearch bulk ingestion completed with {error_count} errors out of {len(actions_for_bulk)//2} documents.")
                # Note: Partial success is possible. Some documents might be indexed.
                # Proper error handling might involve retries or sending failed docs to a DLQ.
            else:
                logger.info(f"Successfully ingested {len(actions_for_bulk)//2} records into OpenSearch.")
        except Exception as e:
            logger.error(f"Exception during OpenSearch bulk ingest: {e}")
            # All records in this batch might have failed to ingest
            failed_records += len(actions_for_bulk)//2 # Approximate
            processed_records -= len(actions_for_bulk)//2 # Adjust count

    logger.info(f"Lambda execution finished. Processed: {processed_records}, Failed: {failed_records}")
    return {
        'status': 'Completed',
        'processed_records': processed_records,
        'failed_records': failed_records
    }

# For local testing, you would need to mock the MSK event structure and OpenSearch client.
# This requires `boto3` for AWSV4SignerAuth, even if just for local credential chain.
if __name__ == '__main__':
    logger.info("Local test mode for msk_consumer_lambda.py")
    # This is a very basic test. Proper local testing needs more setup.
    if not OPENSEARCH_PY_AVAILABLE:
        logger.error("Local test: opensearch-py is not installed. pip install opensearch-py")
    if not os.environ.get('OPENSEARCH_ENDPOINT'):
         os.environ['OPENSEARCH_ENDPOINT'] = 'your-dummy-opensearch-endpoint.es.amazonaws.com' # Replace for real test
         logger.warning(f"OPENSEARCH_ENDPOINT not set, using dummy: {os.environ['OPENSEARCH_ENDPOINT']}")

    # Requires Boto3 for AWSV4SignerAuth if testing client initialization
    try:
        import boto3
        logger.info("Boto3 available for local testing of OpenSearch client init.")
    except ImportError:
        logger.error("Boto3 not available. OpenSearch client initialization with AWSV4SignerAuth will fail.")


    # Example MSK event structure (simplified)
    sample_okta_payload = {
        "provider": "okta",
        "log": { "tenant_id_source": "tenant-alpha", "app_id_source": "app-crm", "time": datetime.datetime.utcnow().isoformat() + "Z",
                 "user": "local_test_okta", "event": "login", "status": "failure", "ip": "1.2.3.4" }
    }
    sample_azure_payload = {
        "provider": "azure_ad",
        "log": { "tenantContextId": "tenant-beta", "applicationContextId": "app-hr", "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                 "userId": "local_test_azure", "action": "auth", "result": "fail", "sourceIp": "5.6.7.8" }
    }

    mock_msk_event = {
        "eventSource": "aws:kafka",
        "eventSourceArn": "arn:aws:kafka:us-east-1:123456789012:cluster/siem-msk-cluster/uuid",
        "records": {
            "identity-logs-0": [ # Topic-Partition
                {"topic": "identity-logs", "partition": 0, "offset": 1, "timestamp": 1678886400000, "timestampType": "CREATE_TIME",
                 "key": None, "value": base64.b64encode(json.dumps(sample_okta_payload).encode('utf-8')).decode('utf-8')},
                {"topic": "identity-logs", "partition": 0, "offset": 2, "timestamp": 1678886401000, "timestampType": "CREATE_TIME",
                 "key": None, "value": base64.b64encode(json.dumps(sample_azure_payload).encode('utf-8')).decode('utf-8')}
            ]
        }
    }

    logger.info(f"Simulating MSK event: {json.dumps(mock_msk_event, indent=2)[:500]}")
    try:
        result = lambda_handler(mock_msk_event, None)
        logger.info(f"Local test handler result: {result}")
    except Exception as e:
        logger.error(f"Local test handler failed: {e}", exc_info=True)

```
