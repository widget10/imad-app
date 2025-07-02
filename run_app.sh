#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Script Configuration ---
TERRAFORM_SUBDIR="terraform"
TERRAFORM_RUN_SCRIPT="${TERRAFORM_SUBDIR}/run.sh"
LOG_GENERATOR_SCRIPT="sample_log_generator.py"
PYTHON_CMD="python3" # Or just "python" if python3 is not standard alias

# --- Helper Functions ---
info() {
  echo "[INFO] $(date +'%Y-%m-%d %H:%M:%S') - $1"
}

error() {
  echo "[ERROR] $(date +'%Y-%m-%d %H:%M:%S') - $1" >&2
  exit 1
}

warn() {
  echo "[WARN] $(date +'%Y-%m-%d %H:%M:%S') - $1" >&2
}

# --- Pre-flight Checks ---
info "Performing pre-flight checks..."

if [ ! -d "$TERRAFORM_SUBDIR" ]; then
  error "Terraform subdirectory '$TERRAFORM_SUBDIR' not found. Ensure you are in the project root."
fi

if [ ! -f "$TERRAFORM_RUN_SCRIPT" ]; then
  error "Terraform run script '$TERRAFORM_RUN_SCRIPT' not found."
fi
if [ ! -x "$TERRAFORM_RUN_SCRIPT" ]; then
  warn "'$TERRAFORM_RUN_SCRIPT' is not executable. Attempting to make it executable..."
  chmod +x "$TERRAFORM_RUN_SCRIPT" || error "Failed to make '$TERRAFORM_RUN_SCRIPT' executable. Please do it manually."
fi

if [ ! -f "$LOG_GENERATOR_SCRIPT" ]; then
  error "Log generator script '$LOG_GENERATOR_SCRIPT' not found in project root."
fi

if ! command -v $PYTHON_CMD &> /dev/null; then
  error "$PYTHON_CMD command not found. Please ensure Python 3 is installed and in your PATH."
fi
PY_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
info "Found Python version: $PY_VERSION"

if ! command -v aws &> /dev/null; then
  warn "AWS CLI could not be found. Terraform deployment might fail if credentials are not sourced via environment variables."
fi
info "Pre-flight checks complete."

# --- Main Actions ---

# Handle 'destroy' argument
if [ "$1" == "destroy" ]; then
  info "--- Destroying Infrastructure ---"
  info "Navigating to $TERRAFORM_SUBDIR..."
  cd "$TERRAFORM_SUBDIR"
  ./"$TERRAFORM_RUN_SCRIPT" destroy
  cd ..
  info "Infrastructure destruction process initiated via terraform/run.sh."
  exit 0
fi

# Default action: deploy and run
info "--- Starting End-to-End SIEM PoC Flow ---"

# 1. Deploy Infrastructure
info "--- Deploying Infrastructure using Terraform ---"
info "Navigating to $TERRAFORM_SUBDIR..."
cd "$TERRAFORM_SUBDIR"

# The terraform/run.sh script handles its own .env sourcing and confirmations
if ! ./"$TERRAFORM_RUN_SCRIPT"; then
  error "Terraform deployment failed. Check output from terraform/run.sh."
fi
info "Terraform deployment process completed."

# Retrieve outputs (MSK Bootstrap Servers, Topic Name, Dashboard URL, AWS Region)
info "Retrieving Terraform outputs..."
MSK_BOOTSTRAP_SERVERS_TLS=$(terraform output -raw msk_bootstrap_brokers_tls 2>/dev/null)
MSK_TOPIC_NAME=$(terraform output -raw msk_topic_name_configured 2>/dev/null) # Using the configured topic name
OS_DASHBOARD_URL=$(terraform output -raw opensearch_domain_kibana_endpoint 2>/dev/null)
AWS_REGION_FROM_TF_OUTPUT=$(terraform output -raw aws_region 2>/dev/null)

# Check if outputs were retrieved successfully
if [ -z "$MSK_BOOTSTRAP_SERVERS_TLS" ]; then
  warn "Could not retrieve MSK Bootstrap Servers (TLS) from Terraform outputs. Log generation cannot send to MSK directly."
  MSK_BOOTSTRAP_SERVERS_TLS=""
fi
if [ -z "$MSK_TOPIC_NAME" ]; then
  warn "Could not retrieve MSK Topic Name from Terraform outputs. Using default from log generator if available."
  MSK_TOPIC_NAME="identity-logs" # Fallback to a common default, matches variable.tf
fi
if [ -z "$OS_DASHBOARD_URL" ]; then
  warn "Could not retrieve OpenSearch Dashboard URL from Terraform outputs."
  OS_DASHBOARD_URL="<Check Terraform Outputs Manually>"
fi
if [ -z "$AWS_REGION_FROM_TF_OUTPUT" ]; then
    warn "Could not retrieve AWS region from Terraform outputs. Will rely on AWS CLI default or Boto3 default if log generator uses it."
    # Attempt to get region from terraform/.env as another fallback
    if [ -f "${TERRAFORM_SUBDIR}/.env" ]; then
        AWS_REGION_FROM_ENV=$(grep TF_VAR_aws_region "${TERRAFORM_SUBDIR}/.env" | cut -d '=' -f2 | tr -d '"')
        AWS_REGION_FROM_TF_OUTPUT=${AWS_REGION_FROM_ENV:-"us-east-1"}
    else
        AWS_REGION_FROM_TF_OUTPUT="us-east-1" # Ultimate fallback
    fi
fi

info "MSK Bootstrap Servers (TLS): $MSK_BOOTSTRAP_SERVERS_TLS"
info "MSK Topic Name: $MSK_TOPIC_NAME"
info "OpenSearch Dashboard URL: $OS_DASHBOARD_URL"
info "AWS Region (from TF): $AWS_REGION_FROM_TF_OUTPUT"

info "Navigating back to project root..."
cd ..

# 2. Generate & Ingest Logs
info "--- Generating and Ingesting Logs ---"
if [ -n "$MSK_BOOTSTRAP_SERVERS_TLS" ] && [ -n "$MSK_TOPIC_NAME" ]; then
  info "Executing log generator to send logs to MSK Topic '$MSK_TOPIC_NAME' via brokers '$MSK_BOOTSTRAP_SERVERS_TLS'..."
  # The log generator now handles kafka-python import and usage.
  # It does not need AWS region directly for Kafka client, but good to have for consistency if other AWS SDK calls were made.
  $PYTHON_CMD "$LOG_GENERATOR_SCRIPT" --bootstrap-servers "$MSK_BOOTSTRAP_SERVERS_TLS" --topic "$MSK_TOPIC_NAME" --num-logs 20 # Generate fewer logs for quick test
  info "Log generation and attempt to send to MSK complete. Check script output for details."
  echo "If kafka-python was not available or there were issues, logs might have been printed to console instead."
  echo "You might need to wait a few minutes for logs to be consumed by Lambda and appear in OpenSearch."
else
  warn "MSK Bootstrap Servers or Topic Name not available. Running log generator to print to console."
  $PYTHON_CMD "$LOG_GENERATOR_SCRIPT" --num-logs 10
  echo "Logs printed to console. You would need to manually configure a Kafka producer to send them."
fi

# 3. Dashboard Reminder
info "--- Next Steps & Dashboard Reminder ---"
echo "Infrastructure is deployed and log generation has been attempted."
echo "OpenSearch Dashboard URL: $OS_DASHBOARD_URL"
echo ""
echo "Important Manual Steps:"
echo "1. Apply OpenSearch Index Template: If not already done, navigate to your OpenSearch Dashboard (Dev Tools or Index Management) and apply the template from 'opensearch_index_template.json'. See 'terraform/README.md' for details."
echo "2. Create Index Pattern in Dashboards: In OpenSearch Dashboards, go to Stack Management > Index Patterns and create an index pattern (e.g., '${OPENSEARCH_INDEX_PREFIX}-*' or 'siem-identity-logs-*') using the 'timestamp' field."
echo "3. Configure Dashboards: Follow 'dashboard_configuration.md' to set up your visualizations."
echo "4. Check Data: Allow a few minutes for data to flow from MSK, through the Lambda consumer, and into OpenSearch. Then check your dashboards or the Discover tab in OpenSearch Dashboards."

info "--- SIEM PoC Flow Script Finished (MSK Version) ---"
exit 0

```
