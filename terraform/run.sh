#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
ENV_FILE=".env"
PLAN_FILE="tfplan"
TERRAFORM_DIR_NAME=$(basename "$PWD")

# --- Helper Functions ---
info() {
  echo "[INFO] $1"
}

error() {
  echo "[ERROR] $1" >&2
  exit 1
}

confirm() {
  while true; do
    read -r -p "$1 [y/N]: " response
    case "$response" in
      [yY][eE][sS]|[yY])
        return 0
        ;;
      [nN][oO]|[nN]|"")
        return 1
        ;;
      *)
        echo "Invalid input. Please answer yes or no."
        ;;
    esac
  done
}

# --- Pre-flight Checks ---

# 1. Ensure script is run from the terraform directory
if [ "$TERRAFORM_DIR_NAME" != "terraform" ]; then
  error "This script must be run from within the 'terraform' directory."
fi
info "Running in correct directory: $PWD"

# 2. Check for .env file
if [ ! -f "$ENV_FILE" ]; then
  error "$ENV_FILE not found. Please copy $ENV_FILE.example to $ENV_FILE and fill in your values."
fi
info "$ENV_FILE found."

# 3. Source environment variables
info "Sourcing environment variables from $ENV_FILE..."
# Ensure TF_VAR_ variables are exported so Terraform can see them
set -a # Automatically export all variables subsequently defined or modified
# shellcheck source=.env
source "$ENV_FILE"
set +a # Stop automatically exporting variables
info "Environment variables sourced."

# 4. Check for AWS CLI and credentials
info "Checking AWS CLI configuration and credentials..."
if ! command -v aws &> /dev/null; then
  error "AWS CLI could not be found. Please install and configure it."
fi

if ! aws sts get-caller-identity --query Arn --output text &> /dev/null; then
  error "AWS credentials are not configured or are invalid. Please run 'aws configure' or ensure your environment/profile is set up correctly."
fi
AWS_USER_ARN=$(aws sts get-caller-identity --query Arn --output text)
info "AWS CLI is configured. Current user ARN: $AWS_USER_ARN"


# --- Main Actions ---

# Handle 'destroy' argument
if [ "$1" == "destroy" ]; then
  info "--- Terraform Destroy ---"
  if confirm "Are you sure you want to DESTROY all resources defined in this Terraform configuration?"; then
    info "Initializing Terraform for destroy..."
    terraform init -input=false
    info "Proceeding with destroy operation..."
    terraform destroy -auto-approve # Using auto-approve after explicit script confirmation
    info "Terraform destroy completed."
  else
    info "Destroy operation cancelled."
  fi
  exit 0
fi

# Default action: apply
info "--- Terraform Apply ---"

# 1. Initialize Terraform
info "Initializing Terraform..."
terraform init -input=false
info "Terraform initialized."

# 2. Validate configuration
info "Validating Terraform configuration..."
terraform validate
info "Terraform configuration is valid."

# 3. Plan deployment
info "Creating Terraform execution plan..."
terraform plan -input=false -out="$PLAN_FILE"
info "Terraform plan saved to $PLAN_FILE"
echo "------------------------------------------------------------------------"
echo "Please review the plan file '$PLAN_FILE' carefully before applying."
echo "You can inspect the plan using: terraform show $PLAN_FILE"
echo "------------------------------------------------------------------------"

# 4. Confirm and Apply
if confirm "Do you want to apply this Terraform plan?"; then
  info "Applying Terraform plan..."
  terraform apply -input=false "$PLAN_FILE"
  info "Terraform apply completed."

  echo ""
  info "--- Post-Deployment Reminders ---"
  echo "1. Apply OpenSearch Index Template: The OpenSearch Index Template ('opensearch_index_template.json' in the parent directory) needs to be applied manually. Refer to terraform/README.md for instructions."
  echo "2. Configure OpenSearch Dashboards: Set up dashboards as described in 'dashboard_configuration.md' (in the parent directory)."
  echo "3. View Outputs: Run 'terraform output' to see important endpoints and resource names."
else
  info "Terraform apply cancelled by user."
fi

exit 0
```
