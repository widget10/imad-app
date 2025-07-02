import json
import random
import datetime
import uuid
import argparse

# Attempt to import Boto3
try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

# Configuration
DEFAULT_NUM_LOGS_PER_PROVIDER = 50
TENANT_IDS = ["tenant-alpha", "tenant-beta", "tenant-gamma"]
USER_IDS_PREFIX = {
    "tenant-alpha": "alpha_user",
    "tenant-beta": "beta_user",
    "tenant-gamma": "gamma_user"
}
APP_IDS = ["app-crm", "app-hr", "app-finance", "app-support"]
EVENT_TYPES_LOGIN = ["login", "auth"]  # Okta 'login', Azure 'auth'
EVENT_STATUSES = ["success", "failure", "fail"]  # Okta 'success'/'failure', Azure 'success'/'fail'
SOURCE_IPS = ["192.168.1.10", "10.0.0.5", "172.16.0.20", "203.0.113.45", "198.51.100.12"]

def generate_timestamp(days_ago_max=30):
    """Generates a random ISO8601 timestamp within the last `days_ago_max` days."""
    now = datetime.datetime.now(datetime.timezone.utc)
    delta_days = random.randint(0, days_ago_max)
    delta_seconds = random.randint(0, 86400)  # seconds in a day
    event_time = now - datetime.timedelta(days=delta_days, seconds=delta_seconds)
    return event_time.isoformat()

def generate_okta_log(tenant_id, app_id):
    """Generates a single Okta-like log entry."""
    user_id_prefix = USER_IDS_PREFIX[tenant_id]
    user_id_suffix = random.randint(1, 10)
    user_id = f"{user_id_prefix}{user_id_suffix}"

    event_type = "login"  # Focus on login for this PoC
    status_options = ["success", "failure"]
    status = random.choices(status_options, weights=[0.7, 0.3], k=1)[0]

    return {
        "event_id": str(uuid.uuid4()),
        "tenant_id_source": tenant_id,
        "app_id_source": app_id,
        "user": user_id,
        "event": event_type,
        "status": status,
        "ip": random.choice(SOURCE_IPS),
        "time": generate_timestamp(),
        "details": {
            "device": random.choice(["Windows", "Mac OS", "Linux", "Mobile"]),
            "browser": random.choice(["Chrome", "Firefox", "Safari", "Edge"])
        }
    }

def generate_azure_ad_log(tenant_id, app_id):
    """Generates a single Azure AD-like log entry."""
    user_id_prefix = USER_IDS_PREFIX[tenant_id]
    user_id_suffix = random.randint(1, 10)
    user_id = f"{user_id_prefix}{user_id_suffix}"

    action = "auth"  # Focus on login for this PoC
    result_options = ["success", "fail"]
    result = random.choices(result_options, weights=[0.7, 0.3], k=1)[0]

    return {
        "log_id": str(uuid.uuid4()),
        "tenantContextId": tenant_id,
        "applicationContextId": app_id,
        "userId": user_id,
        "action": action,
        "result": result,
        "sourceIp": random.choice(SOURCE_IPS),
        "timestamp": generate_timestamp(),
        "properties": {
            "authenticationMethod": random.choice(["Password", "MFA", "Certificate"]),
            "clientApp": random.choice(["WebApp", "MobileApp", "DesktopClient"])
        }
    }

def send_to_kinesis(kinesis_client, stream_name, provider_log):
    """Sends a single log entry to Kinesis."""
    try:
        log_data_bytes = json.dumps(provider_log).encode('utf-8')
        # Determine partition key - using tenant_id is a good practice
        partition_key_value = "default_partition_key"
        log_content = provider_log.get("log", {})
        if "tenant_id_source" in log_content: # Okta
            partition_key_value = log_content["tenant_id_source"]
        elif "tenantContextId" in log_content: # Azure AD
            partition_key_value = log_content["tenantContextId"]

        kinesis_client.put_record(
            StreamName=stream_name,
            Data=log_data_bytes,
            PartitionKey=partition_key_value
        )
        print(f"Successfully sent log to Kinesis stream '{stream_name}' (PartitionKey: {partition_key_value})")
        return True
    except Exception as e:
        print(f"Error sending log to Kinesis stream '{stream_name}': {e}")
        print("Log data that failed to send:")
        print(json.dumps(provider_log, indent=2))
        return False

def main(args):
    """Generates and processes sample logs."""
    kinesis_client = None
    if args.kinesis_stream_name and BOTO3_AVAILABLE:
        print(f"Attempting to send logs to Kinesis stream: {args.kinesis_stream_name} in region {args.aws_region or 'default'}")
        try:
            kinesis_client = boto3.client('kinesis', region_name=args.aws_region)
        except Exception as e:
            print(f"Failed to create Kinesis client (is AWS CLI configured correctly for Boto3?): {e}")
            kinesis_client = None # Ensure it's None if initialization fails
    elif args.kinesis_stream_name and not BOTO3_AVAILABLE:
        print("Boto3 library not found. Logs will be printed to console instead of sending to Kinesis.")
        print("Please install Boto3 (`pip install boto3`) and configure AWS credentials if you want to send logs directly.")

    num_logs = args.num_logs_per_provider

    print(f"Generating {num_logs} Okta logs...")
    for i in range(num_logs):
        tenant = random.choice(TENANT_IDS)
        app = random.choice(APP_IDS)
        log_entry = generate_okta_log(tenant, app)
        provider_log = {"provider": "okta", "log": log_entry}
        if kinesis_client:
            send_to_kinesis(kinesis_client, args.kinesis_stream_name, provider_log)
        else:
            if i < 5 or num_logs <= 5: # Print a few samples or all if few
                print(json.dumps(provider_log, indent=2))
            elif i == 5 and num_logs > 5:
                print("... (further logs will not be printed to console unless Kinesis sending fails)")


    print(f"\nGenerating {num_logs} Azure AD logs...")
    for i in range(num_logs):
        tenant = random.choice(TENANT_IDS)
        app = random.choice(APP_IDS)
        log_entry = generate_azure_ad_log(tenant, app)
        provider_log = {"provider": "azure_ad", "log": log_entry}
        if kinesis_client:
            send_to_kinesis(kinesis_client, args.kinesis_stream_name, provider_log)
        else:
            if i < 5 or num_logs <= 5:
                print(json.dumps(provider_log, indent=2))
            elif i == 5 and num_logs > 5:
                print("... (further logs will not be printed to console unless Kinesis sending fails)")

    if not kinesis_client and args.kinesis_stream_name:
        print(f"\nReminder: Logs were printed to the console. To send them to Kinesis stream '{args.kinesis_stream_name}', you might need to pipe them manually, e.g.:")
        print(f"python sample_log_generator.py --num-logs 1 [other_args] | jq -c . | aws kinesis put-record --stream-name {args.kinesis_stream_name} --partition-key somekey --data file:///dev/stdin")
    elif not args.kinesis_stream_name:
         print(f"\nGenerated {num_logs*2} total logs (printed to console).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate sample identity logs and optionally send them to AWS Kinesis.")
    parser.add_argument(
        "--kinesis-stream-name",
        type=str,
        help="Name of the Kinesis Data Stream to send logs to. If not provided, logs are printed to console."
    )
    parser.add_argument(
        "--aws-region",
        type=str,
        help="AWS region for the Kinesis client. Uses default from AWS config if not provided."
    )
    parser.add_argument(
        "--num-logs-per-provider",
        type=int,
        default=DEFAULT_NUM_LOGS_PER_PROVIDER,
        help=f"Number of logs to generate for each provider (Okta, Azure AD). Default: {DEFAULT_NUM_LOGS_PER_PROVIDER}"
    )
    parsed_args = parser.parse_args()
    main(parsed_args)
```
