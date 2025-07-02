# Terraform Configuration for SIEM Lake PoC on AWS

This directory contains Terraform configurations to deploy the infrastructure for the SIEM Lake Proof of Concept on AWS, **using Amazon MSK as the streaming platform.** This setup will provision:

*   A Virtual Private Cloud (VPC) with public and private subnets, NAT Gateways, and route tables.
*   An Amazon MSK (Managed Streaming for Apache Kafka) cluster.
*   An AWS Lambda function (`msk_consumer_lambda`) to consume messages from an MSK topic, transform them, and ingest them into OpenSearch.
*   An AWS OpenSearch Service domain (deployed within the VPC).
*   An AWS S3 bucket (potentially for MSK broker logs or general use, previously for Firehose backups).
*   Necessary IAM Roles and Policies and Security Groups for the services to interact securely.

## Prerequisites

1.  **Terraform CLI**: Install Terraform (version >= 1.0).
2.  **AWS CLI**: Install and configure the AWS CLI with credentials that have permissions to create the resources defined in this configuration.
3.  **Python Libraries for Lambda Packaging (Manual Step for User)**:
    The `msk_consumer_lambda.py` requires `opensearch-py` and `boto3`. The current Terraform setup for the Lambda (`lambda_msk_consumer.tf`) uses `archive_file` to zip only the `msk_consumer_lambda.py` script itself from the `lambda_code` directory. **For this Lambda to work correctly when deployed, you must manually create a deployment package (ZIP file) that includes these libraries and the script, then update `data.archive_file.msk_consumer_lambda_zip.source_dir` or `output_path` in `lambda_msk_consumer.tf` accordingly, or use a Lambda Layer.**
    *   Example of creating a package:
        ```bash
        # In terraform/lambda_code/
        pip install opensearch-py boto3 -t ./package
        cp msk_consumer_lambda.py ./package/
        cd package
        zip -r ../msk_consumer_lambda_payload.zip .
        cd ..
        # Then ensure terraform/lambda_msk_consumer.tf points to this zip.
        # (e.g., by setting output_path of archive_file to this pre-built zip, or removing archive_file and using filename directly)
        ```
    This manual packaging step is a simplification for this PoC's Terraform. Production setups would use more robust build and packaging automation.
4.  **Python 3.x and `kafka-python`**: For running the `sample_log_generator.py` script (located in the parent directory) to send logs to MSK. Install `kafka-python` via `pip install kafka-python`.

## Setup Instructions

### 1. Clone the Repository (if applicable)

If you haven't already, clone the main project repository that contains this `terraform` directory.

### 2. Configure Environment Variables

Terraform variables are used to customize the deployment. Some sensitive variables or environment-specific configurations can be managed using a `.env` file.

1.  **Navigate to the `terraform` directory:**
    ```bash
    cd path/to/your/project/terraform
    ```

2.  **Create a `.env` file from the example:**
    ```bash
    cp .env.example .env
    ```

3.  **Edit the `.env` file:**
    Open the `.env` file and fill in the required values.
    *   `TF_VAR_aws_region`: Set your desired AWS region.
    *   `TF_VAR_project_name`: A prefix for your resources.
    *   `TF_VAR_opensearch_domain_name`: Desired OpenSearch domain name.
    *   `TF_VAR_opensearch_master_user_name` and `TF_VAR_opensearch_master_user_password`: For OpenSearch FGAC master user.
    *   `TF_VAR_vpc_cidr`, `TF_VAR_public_subnet_cidrs`, `TF_VAR_private_subnet_cidrs`: For VPC networking.
    *   `TF_VAR_msk_broker_instance_type`, `TF_VAR_msk_kafka_version`, `TF_VAR_msk_number_of_broker_nodes`, `TF_VAR_msk_topic_name`: For MSK cluster configuration.
    *   Other `TF_VAR_*` variables as defined in `variables.tf`.

    **Important:** The `.env` file is listed in `.gitignore` and should **never** be committed to version control if it contains sensitive information.

### 3. Prepare Lambda Deployment Package (Manual Step)

As mentioned in Prerequisites, ensure the `msk_consumer_lambda_payload.zip` (or the directory referenced by `data.archive_file.msk_consumer_lambda_zip`) in `lambda_msk_consumer.tf` contains `msk_consumer_lambda.py` **and its dependencies (`opensearch-py`, `boto3`)**. If you created a zip manually, you might need to adjust `lambda_msk_consumer.tf` to use `filename = "lambda_code/msk_consumer_lambda_payload.zip"` directly on the `aws_lambda_function` resource instead of using the `archive_file` data source.

### 4. Load Environment Variables

**Option A: Using `source` (for Bash/Zsh)**
```bash
source .env
```
Or, more robustly to export all `TF_VAR_` prefixed variables:
```bash
export $(grep -v '^#' .env | grep 'TF_VAR_' | xargs)
```

**Option B: Using `direnv`**
If you use `direnv`, you can create a `.envrc` file in the `terraform` directory with the content `source .env` or `dotenv`. Then run `direnv allow`.

**Option C: Manual Export**
Manually export each variable:
```bash
export TF_VAR_aws_region="us-east-1"
export TF_VAR_project_name="siem-poc"
# ... and so on for all variables in your .env file
```

Terraform will automatically use environment variables prefixed with `TF_VAR_` to populate its input variables.

## Using the `run.sh` Script (Recommended)

A helper script `run.sh` is provided in this directory to streamline the deployment and destruction process.

**Ensure you are in the `terraform` directory before running the script.**

Make sure the script is executable:
```bash
chmod +x run.sh
```

### To Deploy or Update Infrastructure:

```bash
./run.sh
```
The script will:
1.  Check if `.env` exists and source it.
2.  Verify AWS CLI and credentials.
3.  Run `terraform init`.
4.  Run `terraform validate`.
5.  Run `terraform plan -out=tfplan`.
6.  Prompt you to review the `tfplan` file and confirm before applying.
7.  If confirmed, run `terraform apply tfplan`.
8.  Remind you of post-deployment manual steps.

### To Destroy Infrastructure:

```bash
./run.sh destroy
```
The script will:
1.  Prompt for confirmation before running `terraform destroy`.

Using `run.sh` is recommended as it includes pre-flight checks and standardizes the workflow.

## Manual Terraform Commands (Alternative)

If you prefer to run Terraform commands manually, ensure you are in the `terraform` directory for all commands. Remember to load your environment variables from `.env` first.

### 1. Initialize Terraform

This command initializes the working directory, downloading provider plugins.
```bash
terraform init
```

### 2. Plan Deployment

This command creates an execution plan, showing you what Terraform will do. Review this carefully.
```bash
terraform plan
```
You can also save the plan to a file:
```bash
terraform plan -out=tfplan
```

### 3. Apply Configuration

This command applies the changes required to reach the desired state of the configuration.
```bash
terraform apply
```
If you saved a plan file:
```bash
terraform apply tfplan
```
Terraform will ask for confirmation before proceeding. Type `yes` to approve.

### 4. View Outputs

After a successful apply, Terraform will print the defined outputs. You can also view them anytime with:
```bash
terraform output
```
Key outputs include:
*   `opensearch_domain_endpoint` and `opensearch_domain_kibana_endpoint`.
*   `msk_cluster_arn`, `msk_bootstrap_brokers_tls`, `msk_topic_name_configured`.
*   `lambda_msk_consumer_function_name`.

### 5. Destroy Infrastructure

To tear down all resources created by this Terraform configuration:
```bash
terraform destroy
```
Terraform will ask for confirmation. Type `yes` to approve. **This is irreversible.**

## Post-Deployment Steps

### 1. Apply OpenSearch Index Template

The OpenSearch Index Template (`opensearch_index_template.json`, located in the parent directory of this Terraform project) needs to be applied manually after the OpenSearch domain is active.

1.  Access your OpenSearch Dashboards using the `opensearch_domain_kibana_endpoint` output.
2.  Log in (e.g., with the master user credentials if you configured them, or as per your FGAC setup).
3.  Navigate to **Stack Management > Index Management > Index Templates** (or **Dev Tools**).
4.  **Using Dev Tools:**
    Paste the following, replacing the content of the template with the actual JSON from `opensearch_index_template.json`:
    ```opensearch-query
    PUT _index_template/siem_identity_logs_template
    {
      "index_patterns": ["siem-identity-logs-*"], // Ensure this matches your Firehose index prefix
      "template": {
        "settings": {
          "number_of_shards": 1,
          "number_of_replicas": 1,
          "index.lifecycle.name": "siem_logs_policy",
          "index.lifecycle.rollover_alias": "siem-identity-logs"
        },
        "mappings": {
          "properties": {
            "tenant_id": {"type": "keyword"},
            "timestamp": {"type": "date", "format": "strict_date_optional_time||epoch_millis"},
            "user_id": {"type": "keyword"},
            "event_type": {"type": "keyword"},
            "event_status": {"type": "keyword"},
            "source_ip": {"type": "ip"},
            "application_id": {"type": "keyword"},
            "details": {"type": "object", "enabled": false}
          }
        }
      },
      "priority": 200,
      "version": 1,
      "_meta": {
        "description": "Index template for SIEM identity logs"
      }
    }
    ```
    Run the command.
5.  **Using UI (Index Templates):**
    *   Click **Create template**.
    *   Follow the UI steps, providing a name (e.g., `siem_identity_logs_template`), an index pattern (e.g., `siem-identity-logs-*` which should match your Firehose index prefix, e.g. `var.opensearch_domain_name` + `*`).
    *   Paste the mappings and settings from `opensearch_index_template.json` into the respective sections.

### 2. Configure OpenSearch Dashboards

Follow the instructions in `dashboard_configuration.md` (located in the parent directory) to:
1.  Create an index pattern in OpenSearch Dashboards (e.g., `siem-identity-logs-*` or `your-opensearch-domain-name-*`).
2.  Create visualizations and assemble the dashboard.

## Testing the Pipeline

1.  **Generate and Send Logs:**
    *   Navigate to the parent directory where `sample_log_generator.py` is located.
    *   Retrieve MSK bootstrap servers and topic name from Terraform outputs:
        ```bash
        BOOTSTRAP_SERVERS=$(terraform output -raw msk_bootstrap_brokers_tls)
        TOPIC_NAME=$(terraform output -raw msk_topic_name_configured)
        ```
    *   Run the `sample_log_generator.py` script, providing these details:
        ```bash
        python ../sample_log_generator.py --bootstrap-servers "$BOOTSTRAP_SERVERS" --topic "$TOPIC_NAME" --num-logs 20
        ```
        This requires `kafka-python` to be installed in your Python environment. If not, the script will print logs to the console.

2.  **Verify Data:**
    *   Check CloudWatch Logs for the `msk_consumer_lambda` function for processing details or errors.
    *   Check MSK CloudWatch metrics if needed.
    *   Query data in OpenSearch Dashboards (Dev Tools or Discover tab) to see if transformed logs are arriving in the `siem-identity-logs-*` indices (or your configured index prefix).
    *   Check your dashboard visualizations.

## File Structure Overview (MSK Version)

```
terraform/
├── .env.example            # Example environment variables
├── .gitignore              # Files to ignore for Git
├── main.tf                 # Main configuration, locals
├── providers.tf            # Provider configurations
├── variables.tf            # Input variables (updated for MSK)
├── outputs.tf              # Output values (updated for MSK)
├── network.tf              # VPC, Subnets, Security Groups, NAT, IGW, Route Tables
├── iam.tf                  # IAM roles and policies (updated for MSK consumer Lambda)
├── s3.tf                   # S3 bucket (may be repurposed or for MSK logs)
├── msk.tf                  # MSK Cluster definition
├── lambda_msk_consumer.tf  # MSK Consumer Lambda function and event source mapping
├── lambda_code/
│   └── msk_consumer_lambda.py # Python code for MSK consumer
│   └── transformation_lambda.py # Original transformation logic (may be removed if fully integrated)
├── opensearch.tf           # OpenSearch domain (updated for VPC and new Lambda access)
└── README.md               # This file (updated for MSK)
```
(Note: `kinesis_stream.tf` and `firehose.tf` would be deleted in this MSK version.)

## Cleanup

Remember to run `terraform destroy` when you no longer need the resources to avoid ongoing AWS charges.
```
