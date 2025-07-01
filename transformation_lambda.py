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
    # Extract tenant_id and application_id from the source log if they exist,
    # otherwise, they might need to be passed in or derived differently in a real scenario.
    # For this PoC, the generator includes them as 'tenant_id_source' and 'app_id_source'.
    tenant_id = log_data.get("tenant_id_source", "unknown_tenant")
    application_id = log_data.get("app_id_source", "unknown_app")

    # Map Okta event type 'login' to a more generic 'login' or 'auth_failure'
    event_type = "login" # Default
    if log_data.get("event", "").lower() == "login" and log_data.get("status", "").lower() == "failure":
        event_type = "auth_failure"
    elif log_data.get("event", "").lower() == "login":
        event_type = "login"
    else:
        event_type = log_data.get("event", "unknown_event")


    return {
        "tenant_id": tenant_id,
        "timestamp": log_data.get("time"), # Assumes 'time' is already ISO8601
        "user_id": log_data.get("user"),
        "event_type": event_type,
        "event_status": log_data.get("status", "").lower(), # Ensure lowercase
        "source_ip": log_data.get("ip"),
        "application_id": application_id,
        "details": log_data.get("details", {})
    }

def transform_azure_ad_log(log_data):
    """Transforms a single Azure AD log to the standardized schema."""
    tenant_id = log_data.get("tenantContextId", "unknown_tenant")
    application_id = log_data.get("applicationContextId", "unknown_app")

    # Map Azure 'action' and 'result' to standardized 'event_type' and 'event_status'
    event_type = "login" # Default
    azure_action = log_data.get("action", "").lower()
    azure_result = log_data.get("result", "").lower()

    if azure_action == "auth" and azure_result == "fail":
        event_type = "auth_failure"
    elif azure_action == "auth":
        event_type = "login"
    else:
        event_type = azure_action # or map other actions as needed

    # Map Azure 'fail' to 'failure' for event_status
    event_status = "failure" if azure_result == "fail" else azure_result

    return {
        "tenant_id": tenant_id,
        "timestamp": log_data.get("timestamp"), # Assumes 'timestamp' is already ISO8601
        "user_id": log_data.get("userId"),
        "event_type": event_type,
        "event_status": event_status,
        "source_ip": log_data.get("sourceIp"),
        "application_id": application_id,
        "details": log_data.get("properties", {}) # Azure uses 'properties' for extra details
    }

def lambda_handler(event, context):
    """
    AWS Lambda handler function.
    Assumes 'event' is the input from Kinesis Data Streams or direct invocation.
    For Kinesis, logs are typically Base64 encoded and arrive in a list.
    """
    output_records = []

    # Determine if the event is from Kinesis
    if 'Records' in event and event['Records'] and 'kinesis' in event['Records'][0]:
        # Process Kinesis records
        for record in event['Records']:
            try:
                # Kinesis data is base64 encoded
                payload_decoded = base64.b64decode(record['kinesis']['data']).decode('utf-8')
                log_entry = json.loads(payload_decoded)

                # The log generator wraps logs with a 'provider' key
                provider = log_entry.get("provider", "").lower()
                actual_log_data = log_entry.get("log", {})

                if not actual_log_data:
                    print(f"Skipping record with missing log data: {log_entry}")
                    continue

                transformed_log = None
                if provider == "okta":
                    transformed_log = transform_okta_log(actual_log_data)
                elif provider == "azure_ad":
                    transformed_log = transform_azure_ad_log(actual_log_data)
                else:
                    print(f"Unknown log provider: {provider}. Log: {actual_log_data}")
                    # Optionally, handle unknown logs, e.g., store them in a dead-letter queue
                    continue

                if transformed_log:
                    # Clean out any None values from the transformed log
                    cleaned_log = {k: v for k, v in transformed_log.items() if v is not None}
                    output_records.append({
                        'recordId': record['eventID'], # Kinesis specific
                        'result': 'Ok',
                        'data': base64.b64encode(json.dumps(cleaned_log).encode('utf-8')).decode('utf-8')
                    })
            except Exception as e:
                print(f"Error processing record: {record.get('eventID', 'N/A')}, Error: {e}")
                output_records.append({
                    'recordId': record.get('eventID', 'N/A'),
                    'result': 'ProcessingFailed',
                    'data': record['kinesis']['data'] # Return original data on failure
                })
        return {'records': output_records} # Required format for Kinesis Firehose Lambda blueprint

    else: # Handle direct invocation or other event sources (e.g. for testing)
        # For direct invocation, 'event' might be a single log or a list of logs.
        # The sample_log_generator produces a list where each item has "provider" and "log".
        # This part is more for local testing of the transformation logic.
        # In a real Kinesis setup, the 'Records' path is the primary one.

        processed_logs = []
        logs_to_process = event if isinstance(event, list) else [event]

        for log_entry in logs_to_process:
            try:
                provider = log_entry.get("provider", "").lower()
                actual_log_data = log_entry.get("log", {})

                if not actual_log_data:
                    print(f"Skipping entry with missing log data: {log_entry}")
                    continue

                transformed_log = None
                if provider == "okta":
                    transformed_log = transform_okta_log(actual_log_data)
                elif provider == "azure_ad":
                    transformed_log = transform_azure_ad_log(actual_log_data)
                else:
                    print(f"Unknown log provider: {provider}. Log: {actual_log_data}")
                    continue

                if transformed_log:
                    cleaned_log = {k: v for k, v in transformed_log.items() if v is not None}
                    processed_logs.append(cleaned_log)
            except Exception as e:
                print(f"Error processing direct invocation log: {log_entry}, Error: {e}")

        return {
            'statusCode': 200,
            'body': json.dumps(processed_logs)
        }

# Example usage for local testing (simulating direct invocation)
if __name__ == '__main__':
    # Sample logs as if coming from the generator
    sample_okta_from_generator = {
        "provider": "okta",
        "log": {
            "event_id": "sample-okta-123",
            "tenant_id_source": "tenant-alpha",
            "app_id_source": "app-crm",
            "user": "alpha_user1",
            "event": "login",
            "status": "failure",
            "ip": "192.168.1.10",
            "time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "details": {"device": "Windows", "browser": "Chrome"}
        }
    }
    sample_azure_from_generator = {
        "provider": "azure_ad",
        "log": {
            "log_id": "sample-azure-456",
            "tenantContextId": "tenant-beta",
            "applicationContextId": "app-hr",
            "userId": "beta_user2",
            "action": "auth",
            "result": "fail",
            "sourceIp": "10.0.0.5",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "properties": {"authenticationMethod": "Password"}
        }
    }

    # Test with a list of logs, similar to how the generator might output if used directly
    test_event_direct_invocation = [sample_okta_from_generator, sample_azure_from_generator]

    print("--- Testing Direct Invocation ---")
    result_direct = lambda_handler(test_event_direct_invocation, None)
    print(json.dumps(json.loads(result_direct['body']), indent=2))

    # Simulate a Kinesis event (structure for Kinesis Data Firehose Lambda)
    def kinesis_record(log_with_provider):
        return {
            'eventID': 'shardId-000000000000:00000000000000000000000000000000000000000000000000000000',
            'kinesis': {
                'data': base64.b64encode(json.dumps(log_with_provider).encode('utf-8')).decode('utf-8')
            }
        }

    test_event_kinesis = {
        'Records': [
            kinesis_record(sample_okta_from_generator),
            kinesis_record(sample_azure_from_generator)
        ]
    }
    print("\n--- Testing Kinesis Event ---")
    result_kinesis = lambda_handler(test_event_kinesis, None)
    # Print decoded Kinesis results for readability
    decoded_kinesis_results = []
    for record in result_kinesis.get('records', []):
        if record['result'] == 'Ok':
            decoded_data = json.loads(base64.b64decode(record['data']).decode('utf-8'))
            decoded_kinesis_results.append(decoded_data)
        else:
            decoded_kinesis_results.append({"error": "ProcessingFailed", "original_data_b64": record['data']})
    print(json.dumps(decoded_kinesis_results, indent=2))

    # Test a log with missing provider
    sample_unknown_provider_log = {
        "provider": "unknown_provider", # <--- Unknown
        "log": {
            "some_field": "some_value",
            "timestamp_val": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    }
    test_event_unknown_provider_kinesis = {'Records': [kinesis_record(sample_unknown_provider_log)]}
    print("\n--- Testing Kinesis Event with Unknown Provider ---")
    result_unknown_kinesis = lambda_handler(test_event_unknown_provider_kinesis, None)
    print(json.dumps(result_unknown_kinesis, indent=2)) # Should show ProcessingFailed or skip

    # Test a log with missing actual log data inside "log"
    sample_missing_log_data = {
        "provider": "okta"
        # "log": {} # Missing "log" key or it's empty
    }
    test_event_missing_log_data_kinesis = {'Records': [kinesis_record(sample_missing_log_data)]}
    print("\n--- Testing Kinesis Event with Missing Log Data ---")
    result_missing_log_data_kinesis = lambda_handler(test_event_missing_log_data_kinesis, None)
    print(json.dumps(result_missing_log_data_kinesis, indent=2))
```
