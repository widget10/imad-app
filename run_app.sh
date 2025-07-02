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

# Retrieve outputs (Kinesis stream name and Dashboard URL)
info "Retrieving Terraform outputs..."
KINESIS_STREAM_NAME=$(terraform output -raw kinesis_stream_name 2>/dev/null)
OS_DASHBOARD_URL=$(terraform output -raw opensearch_domain_kibana_endpoint 2>/dev/null) # Using kibana_endpoint as per TF output
AWS_REGION_FROM_TF_OUTPUT=$(terraform output -raw aws_region 2>/dev/null) # Get region from TF output as fallback

# Check if outputs were retrieved successfully
if [ -z "$KINESIS_STREAM_NAME" ]; then
  warn "Could not retrieve Kinesis stream name from Terraform outputs. Log generation might not be able to send to Kinesis directly."
  KINESIS_STREAM_NAME="" # Ensure it's empty if not found
fi
if [ -z "$OS_DASHBOARD_URL" ]; then
  warn "Could not retrieve OpenSearch Dashboard URL from Terraform outputs."
  OS_DASHBOARD_URL="<Check Terraform Outputs Manually>"
fi
if [ -z "$AWS_REGION_FROM_TF_OUTPUT" ]; then
    warn "Could not retrieve AWS region from Terraform outputs. Will rely on AWS CLI default or Boto3 default."
    # Attempt to get region from .env as another fallback
    if [ -f ".env" ]; then
        AWS_REGION_FROM_ENV=$(grep TF_VAR_aws_region .env | cut -d '=' -f2 | tr -d '"')
        AWS_REGION_FROM_TF_OUTPUT=${AWS_REGION_FROM_ENV:-"us-east-1"} # Default if still not found
    else
        AWS_REGION_FROM_TF_OUTPUT="us-east-1" # Ultimate fallback
    fi
fi

info "Kinesis Stream Name: $KINESIS_STREAM_NAME"
info "OpenSearch Dashboard URL: $OS_DASHBOARD_URL"
info "AWS Region for Kinesis: $AWS_REGION_FROM_TF_OUTPUT"

info "Navigating back to project root..."
cd ..

# 2. Generate & Ingest Logs
info "--- Generating and Ingesting Logs ---"
if [ -n "$KINESIS_STREAM_NAME" ]; then
  info "Executing log generator to send logs to Kinesis stream '$KINESIS_STREAM_NAME' in region '$AWS_REGION_FROM_TF_OUTPUT'..."
  $PYTHON_CMD "$LOG_GENERATOR_SCRIPT" --kinesis-stream-name "$KINESIS_STREAM_NAME" --aws-region "$AWS_REGION_FROM_TF_OUTPUT" --num-logs-per-provider 20 # Generate fewer logs for quick test
  info "Log generation and attempt to send to Kinesis complete. Check script output for details."
  echo "If Boto3 was not available or there were issues, logs might have been printed to console instead."
  echo "You might need to wait a few minutes for logs to be processed by Firehose and appear in OpenSearch."
else
  warn "Kinesis stream name not available. Running log generator to print to console."
  $PYTHON_CMD "$LOG_GENERATOR_SCRIPT" --num-logs-per-provider 10
  echo "Logs printed to console. You would need to manually pipe them to a Kinesis stream if desired."
fi

# 3. Dashboard Reminder
info "--- Next Steps & Dashboard Reminder ---"
echo "Infrastructure is deployed and log generation has been attempted."
echo "OpenSearch Dashboard URL: $OS_DASHBOARD_URL"
echo ""
echo "Important Manual Steps:"
echo "1. Apply OpenSearch Index Template: If not already done, navigate to your OpenSearch Dashboard (Dev Tools or Index Management) and apply the template from 'opensearch_index_template.json'. See 'terraform/README.md' for details."
echo "2. Create Index Pattern in Dashboards: In OpenSearch Dashboards, go to Stack Management > Index Patterns and create an index pattern (e.g., '${KINESIS_STREAM_NAME}-*' or 'siem-identity-logs-*' depending on your Firehose config) using the 'timestamp' field."
echo "3. Configure Dashboards: Follow 'dashboard_configuration.md' to set up your visualizations."
echo "4. Check Data: Allow a few minutes for data to flow through Kinesis, Firehose, Lambda, and into OpenSearch. Then check your dashboards or the Discover tab in OpenSearch Dashboards."

info "--- SIEM PoC Flow Script Finished ---"
exit 0

```
