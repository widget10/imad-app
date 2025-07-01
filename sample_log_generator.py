import json
import random
import datetime
import uuid

# Configuration
NUM_LOGS_PER_PROVIDER = 50
TENANT_IDS = ["tenant-alpha", "tenant-beta", "tenant-gamma"]
USER_IDS_PREFIX = {
    "tenant-alpha": "alpha_user",
    "tenant-beta": "beta_user",
    "tenant-gamma": "gamma_user"
}
APP_IDS = ["app-crm", "app-hr", "app-finance", "app-support"]
EVENT_TYPES_LOGIN = ["login", "auth"] # Okta 'login', Azure 'auth'
EVENT_STATUSES = ["success", "failure", "fail"] # Okta 'success'/'failure', Azure 'success'/'fail'
SOURCE_IPS = ["192.168.1.10", "10.0.0.5", "172.16.0.20", "203.0.113.45", "198.51.100.12"]

def generate_timestamp(days_ago_max=30):
    """Generates a random ISO8601 timestamp within the last `days_ago_max` days."""
    now = datetime.datetime.now(datetime.timezone.utc)
    delta_days = random.randint(0, days_ago_max)
    delta_seconds = random.randint(0, 86400) # seconds in a day
    event_time = now - datetime.timedelta(days=delta_days, seconds=delta_seconds)
    return event_time.isoformat()

def generate_okta_log(tenant_id, app_id):
    """Generates a single Okta-like log entry."""
    user_id_prefix = USER_IDS_PREFIX[tenant_id]
    user_id_suffix = random.randint(1, 10)
    user_id = f"{user_id_prefix}{user_id_suffix}"

    event_type = "login" # Focus on login for this PoC
    status_options = ["success", "failure"]
    # Ensure a good number of failures for dashboard testing
    status = random.choices(status_options, weights=[0.7, 0.3], k=1)[0]

    return {
        "event_id": str(uuid.uuid4()),
        "tenant_id_source": tenant_id, # To be mapped to standardized schema's tenant_id
        "app_id_source": app_id, # To be mapped to standardized schema's application_id
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

    action = "auth" # Focus on login for this PoC
    result_options = ["success", "fail"]
    # Ensure a good number of failures for dashboard testing
    result = random.choices(result_options, weights=[0.7, 0.3], k=1)[0]

    return {
        "log_id": str(uuid.uuid4()),
        "tenantContextId": tenant_id, # To be mapped to standardized schema's tenant_id
        "applicationContextId": app_id, # To be mapped to standardized schema's application_id
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

def main():
    """Generates and prints sample logs."""
    all_logs = []

    print(f"Generating {NUM_LOGS_PER_PROVIDER} Okta logs...")
    for i in range(NUM_LOGS_PER_PROVIDER):
        tenant = random.choice(TENANT_IDS)
        app = random.choice(APP_IDS)
        log_entry = generate_okta_log(tenant, app)
        all_logs.append({"provider": "okta", "log": log_entry})
        if i < 5: # Print a few samples
            print(json.dumps(log_entry, indent=2))

    print(f"\nGenerating {NUM_LOGS_PER_PROVIDER} Azure AD logs...")
    for i in range(NUM_LOGS_PER_PROVIDER):
        tenant = random.choice(TENANT_IDS)
        app = random.choice(APP_IDS)
        log_entry = generate_azure_ad_log(tenant, app)
        all_logs.append({"provider": "azure_ad", "log": log_entry})
        if i < 5: # Print a few samples
            print(json.dumps(log_entry, indent=2))

    # Optionally, save all logs to a file
    # with open("simulated_logs.json", "w") as f:
    #     json.dump(all_logs, f, indent=2)
    # print(f"\nGenerated a total of {len(all_logs)} logs.")
    # print("Sample logs also saved to simulated_logs.json if uncommented.")

if __name__ == "__main__":
    main()
```
