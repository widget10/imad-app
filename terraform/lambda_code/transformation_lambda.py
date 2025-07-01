import json
import base64
import datetime

# Standardized Schema:
# {
#   "tenant_id": "string",
#   "timestamp": "ISO8601",
#   "user_id": "string",
#   "event_type": "string (e.g., login, logout, auth_failure)",
#   "event_status": "string (success/failure)",
#   "source_ip": "string",
#   "application_id": "string",
#   "details": "object (additional metadata)"
# }

def transform_okta_log(log_data):
    """Transforms a single Okta log to the standardized schema."""
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
        "tenant_id": tenant_id,
        "timestamp": log_data.get("time"),
        "user_id": log_data.get("user"),
        "event_type": event_type,
        "event_status": log_data.get("status", "").lower(),
        "source_ip": log_data.get("ip"),
        "application_id": application_id,
        "details": log_data.get("details", {})
    }

def transform_azure_ad_log(log_data):
    """Transforms a single Azure AD log to the standardized schema."""
    tenant_id = log_data.get("tenantContextId", "unknown_tenant")
    application_id = log_data.get("applicationContextId", "unknown_app")

    event_type = "login"
    azure_action = log_data.get("action", "").lower()
    azure_result = log_data.get("result", "").lower()

    if azure_action == "auth" and azure_result == "fail":
        event_type = "auth_failure"
    elif azure_action == "auth":
        event_type = "login"
    else:
        event_type = azure_action

    event_status = "failure" if azure_result == "fail" else azure_result

    return {
        "tenant_id": tenant_id,
        "timestamp": log_data.get("timestamp"),
        "user_id": log_data.get("userId"),
        "event_type": event_type,
        "event_status": event_status,
        "source_ip": log_data.get("sourceIp"),
        "application_id": application_id,
        "details": log_data.get("properties", {})
    }

def lambda_handler(event, context):
    output_records = []

    if 'Records' in event and event['Records'] and 'kinesis' in event['Records'][0] and 'data' in event['Records'][0]['kinesis']:
        for record in event['Records']:
            try:
                payload_decoded = base64.b64decode(record['kinesis']['data']).decode('utf-8')
                log_entry = json.loads(payload_decoded)

                provider = log_entry.get("provider", "").lower()
                actual_log_data = log_entry.get("log", {})

                if not actual_log_data:
                    print(f"Skipping record with missing log data: {log_entry}")
                    output_records.append({
                        'recordId': record.get('eventID', record.get('recordId', 'N/A')), # Kinesis Firehose uses recordId
                        'result': 'ProcessingFailed',
                        'data': record['kinesis']['data']
                    })
                    continue

                transformed_log = None
                if provider == "okta":
                    transformed_log = transform_okta_log(actual_log_data)
                elif provider == "azure_ad":
                    transformed_log = transform_azure_ad_log(actual_log_data)
                else:
                    print(f"Unknown log provider: {provider}. Log: {actual_log_data}")
                    output_records.append({
                        'recordId': record.get('eventID', record.get('recordId', 'N/A')),
                        'result': 'ProcessingFailed',
                        'data': record['kinesis']['data']
                    })
                    continue

                if transformed_log:
                    cleaned_log = {k: v for k, v in transformed_log.items() if v is not None}
                    output_records.append({
                        'recordId': record.get('eventID', record.get('recordId', 'N/A')),
                        'result': 'Ok',
                        'data': base64.b64encode(json.dumps(cleaned_log).encode('utf-8')).decode('utf-8')
                    })
            except Exception as e:
                print(f"Error processing record: {record.get('eventID', record.get('recordId', 'N/A'))}, Error: {e}, Record: {record.get('kinesis', {}).get('data', 'NO_DATA')}")
                output_records.append({
                    'recordId': record.get('eventID', record.get('recordId', 'N/A')),
                    'result': 'ProcessingFailed',
                    'data': record['kinesis']['data']
                })
        return {'records': output_records}
    else:
        # Handle direct invocation or other event types if necessary for testing
        print(f"Received non-Kinesis Firehose event or malformed event: {event}")
        # Depending on how you test, you might return an error or a specific response
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Event does not match Kinesis Firehose structure with base64 data.'})
        }

# Minimal test example if run directly (not part of Lambda execution in AWS)
if __name__ == '__main__':
    print("Local test mode for transformation_lambda.py")
    # This part is for very basic local syntax checks, not full simulation.
    # Full simulation would require crafting a Kinesis Firehose-like event.
    sample_okta_payload = {
        "provider": "okta",
        "log": {
            "tenant_id_source": "tenant-xyz", "app_id_source": "app-123",
            "time": datetime.datetime.utcnow().isoformat() + "Z", "user": "test_user_okta",
            "event": "login", "status": "failure", "ip": "1.2.3.4",
            "details": {"reason": "bad_password"}
        }
    }
    # Simulate a Kinesis Firehose record structure for testing the handler
    mock_event = {
        "records": [
            {
                "recordId": "49645189958680400000000000000000000000000000000000000000",
                "kinesis": { # In Firehose, it's just 'data', not nested under 'kinesis'
                    "data": base64.b64encode(json.dumps(sample_okta_payload).encode('utf-8')).decode('utf-8')
                }
            }
        ]
    }
    # Correction for Firehose structure: 'data' is directly under 'records' element for Lambda
    # The lambda_handler is written for Kinesis Firehose events.
    # A Kinesis Firehose event structure is more like:
    # { "invocationId": "...", "deliveryStreamArn": "...", "region": "...", "records": [ { "recordId": "...", "approximateArrivalTimestamp": ..., "data": "base64encodeddata" } ] }

    # Let's adjust the mock_event to better match Firehose's direct Lambda invocation for transformation
    mock_firehose_event = {
        "invocationId": "invocationIdExample",
        "deliveryStreamArn": "arn:aws:firehose:us-east-1:123456789012:deliverystream/exampleStream",
        "region": "us-east-1",
        "records": [
            {
                "recordId": "49546986683135544286507457936321625675700192471156785154",
                "approximateArrivalTimestamp": 1495072949453,
                "data": base64.b64encode(json.dumps(sample_okta_payload).encode('utf-8')).decode('utf-8')
            }
        ]
    }
    print(f"Simulating Firehose event: {json.dumps(mock_firehose_event, indent=2)}")
    results = lambda_handler(mock_firehose_event, None)
    print(f"\nTransformation results: {json.dumps(results, indent=2)}")

    # To decode results for inspection:
    if results and 'records' in results:
        for record in results['records']:
            if record['result'] == 'Ok':
                decoded_data = base64.b64decode(record['data']).decode('utf-8')
                print(f"\nDecoded good record: {json.dumps(json.loads(decoded_data), indent=2)}")
            else:
                print(f"\nBad record processing: {record}")

```
