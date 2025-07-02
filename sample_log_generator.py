import json
import random
import datetime
import uuid
import argparse

# Attempt to import Boto3
try:
    # For MSK, we'll use kafka-python
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
    KAFKA_PYTHON_AVAILABLE = True
except ImportError:
    KAFKA_PYTHON_AVAILABLE = False
    BOTO3_AVAILABLE = False # Ensure this is also false if primary kafka lib missing for clarity

# Configuration
DEFAULT_NUM_LOGS_PER_PROVIDER = 50
DEFAULT_MSK_TOPIC = "identity-logs"
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
    """Sends a single log entry to a Kafka topic."""
    try:
        log_data_bytes = json.dumps(provider_log).encode('utf-8')

        # Determine partition key from tenant_id for consistent partitioning if desired
        partition_key_value_bytes = None
        log_content = provider_log.get("log", {})
        if "tenant_id_source" in log_content: # Okta
            partition_key_value_bytes = log_content["tenant_id_source"].encode('utf-8')
        elif "tenantContextId" in log_content: # Azure AD
            partition_key_value_bytes = log_content["tenantContextId"].encode('utf-8')

        # Asynchronously send message
        future = kafka_producer.send(topic_name, value=log_data_bytes, key=partition_key_value_bytes)
        # Block for 'synchronous' sends, or handle callbacks for async. For PoC, synchronous is simpler.
        record_metadata = future.get(timeout=10)
        print(f"Successfully sent log to Kafka topic '{record_metadata.topic}' partition {record_metadata.partition} offset {record_metadata.offset} (Key: {partition_key_value_bytes})")
        return True
    except KafkaError as ke:
        print(f"KafkaError sending log to topic '{topic_name}': {ke}")
    except Exception as e:
        print(f"Error sending log to Kafka topic '{topic_name}': {e}")

    print("Log data that failed to send to Kafka:")
    print(json.dumps(provider_log, indent=2))
    return False

def main(args):
    """Generates and processes sample logs."""
    kafka_producer_client = None
    if args.bootstrap_servers and args.topic and KAFKA_PYTHON_AVAILABLE:
        print(f"Attempting to send logs to MSK Kafka topic: {args.topic} via brokers: {args.bootstrap_servers}")
        try:
            # For MSK with TLS encryption (default)
            # May need to configure SSL if using SASL/SCRAM or mTLS, but for IAM auth + TLS, this is often enough.
            # For IAM auth, ensure your environment (e.g. Lambda role, EC2 instance profile) has MSK permissions.
            # If running locally with IAM auth, AWS CLI credentials need to be configured.
            # MSK IAM auth is typically handled by the Kafka client library if it supports AWS MSK IAM authentication.
            # kafka-python itself does not directly support AWS IAM auth for MSK out-of-the-box.
            # A common pattern for local dev or non-Lambda is to use SASL/SCRAM or run client in VPC with SG allowing access.
            # For this PoC, we'll assume TLS connection and that network path/auth is handled.
            # If MSK is IAM controlled, specific SASL mechanisms like 'OAUTHBEARER' or AWS MSK IAM specific client setup would be needed.
            # For now, this setup is for TLS encrypted endpoints.
            kafka_producer_client = KafkaProducer(
                bootstrap_servers=args.bootstrap_servers.split(','),
                security_protocol='SSL' if 'SSL' in args.bootstrap_servers.upper() else 'PLAINTEXT', # Basic check based on common broker string patterns
                # For local testing against MSK with IAM, you might need a more complex setup or use a client that supports it.
                # E.g. for IAM:
                # security_protocol='SASL_SSL',
                # sasl_mechanism='OAUTHBEARER', # or AWS_MSK_IAM
                # sasl_oauth_token_provider=..., # Custom token provider for IAM
                # ssl_context=... # if needed
            )
            print("KafkaProducer initialized.")
        except Exception as e:
            print(f"Failed to create KafkaProducer: {e}")
            kafka_producer_client = None
    elif args.bootstrap_servers and args.topic and not KAFKA_PYTHON_AVAILABLE:
        print("kafka-python library not found. Logs will be printed to console instead of sending to Kafka.")
        print("Please install kafka-python (`pip install kafka-python`) if you want to send logs directly to MSK.")

    num_logs = args.num_logs

    print(f"Generating {num_logs} Okta logs...")
    for i in range(num_logs):
        tenant = random.choice(TENANT_IDS)
        app = random.choice(APP_IDS)
        log_entry = generate_okta_log(tenant, app)
        provider_log = {"provider": "okta", "log": log_entry}
        if kafka_producer_client:
            send_to_kafka(kafka_producer_client, args.topic, provider_log)
        else:
            if i < 5 or num_logs <= 5:
                print(json.dumps(provider_log, indent=2))
            elif i == 5 and num_logs > 5:
                print("... (further Okta logs will not be printed to console)")

    print(f"\nGenerating {num_logs} Azure AD logs...")
    for i in range(num_logs):
        tenant = random.choice(TENANT_IDS)
        app = random.choice(APP_IDS)
        log_entry = generate_azure_ad_log(tenant, app)
        provider_log = {"provider": "azure_ad", "log": log_entry}
        if kafka_producer_client:
            send_to_kafka(kafka_producer_client, args.topic, provider_log)
        else:
            if i < 5 or num_logs <= 5:
                print(json.dumps(provider_log, indent=2))
            elif i == 5 and num_logs > 5:
                print("... (further Azure AD logs will not be printed to console)")

    if kafka_producer_client:
        print("Flushing Kafka producer...")
        kafka_producer_client.flush()
        print("Closing Kafka producer.")
        kafka_producer_client.close()

    if not kafka_producer_client and args.bootstrap_servers and args.topic:
        print(f"\nReminder: Logs were printed to the console. To send them to Kafka topic '{args.topic}', ensure kafka-python is installed and configuration is correct.")
    elif not (args.bootstrap_servers and args.topic):
         print(f"\nGenerated {num_logs*2} total logs (printed to console). Provide --bootstrap-servers and --topic to send to MSK.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate sample identity logs and optionally send them to AWS MSK Kafka.")
    parser.add_argument(
        "--bootstrap-servers",
        type=str,
        help="Comma-separated list of MSK Kafka bootstrap broker_list:port (e.g., b-1.xxx.kafka.us-east-1.amazonaws.com:9094,b-2.xxx:9094). Required for sending to MSK."
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=DEFAULT_MSK_TOPIC,
        help=f"Kafka topic to send logs to. Default: {DEFAULT_MSK_TOPIC}. Required if --bootstrap-servers is provided."
    )
    # Boto3 related args removed/commented as Kinesis is replaced by MSK
    # parser.add_argument(
    #     "--aws-region",
    #     type=str,
    #     help="AWS region for the Kinesis client. Uses default from AWS config if not provided."
    # )
    parser.add_argument(
        "--num-logs", # Renamed from num_logs_per_provider for clarity as it's total per provider
        type=int,
        default=DEFAULT_NUM_LOGS_PER_PROVIDER, # Reusing constant, but arg name changed
        help=f"Number of logs to generate FOR EACH provider (Okta, Azure AD). Default: {DEFAULT_NUM_LOGS_PER_PROVIDER}"
    )
    parsed_args = parser.parse_args()

    if parsed_args.bootstrap_servers and not parsed_args.topic:
        parser.error("--topic is required when --bootstrap-servers is provided.")
    if not parsed_args.bootstrap_servers and parsed_args.topic != DEFAULT_MSK_TOPIC :
         print(f"Warning: --topic '{parsed_args.topic}' provided without --bootstrap-servers. Logs will be printed to console.")


    main(parsed_args)
```
