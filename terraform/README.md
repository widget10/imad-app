# Terraform Configuration for SIEM Lake PoC on AWS

This directory contains Terraform configurations to deploy the infrastructure for the SIEM Lake Proof of Concept on AWS. This setup will provision:

*   An AWS OpenSearch Service domain.
*   An AWS Kinesis Data Stream for ingesting raw logs.
*   An AWS Lambda function for transforming logs.
*   An AWS Kinesis Data Firehose delivery stream to batch, transform, and deliver logs to OpenSearch.
*   An AWS S3 bucket for Kinesis Data Firehose backups.
*   Necessary IAM Roles and Policies for the services to interact.

## Prerequisites

1.  **Terraform CLI**: Install Terraform (version >= 1.0).
2.  **AWS CLI**: Install and configure the AWS CLI with credentials that have permissions to create the resources defined in this configuration. Ensure your AWS CLI profile is correctly set up or that your environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` (if applicable), `AWS_REGION`) are configured.
3.  **Python 3.x**: For running the `sample_log_generator.py` script (located in the parent directory) to test the pipeline.
4.  **jq (optional)**: Useful for parsing JSON output from AWS CLI commands.
5.  **Log Transformation Code**: The `transformation_lambda.py` script is expected to be in the `lambda_code/` subdirectory within this Terraform project. This is handled by the plan.

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
    *   `TF_VAR_opensearch_master_user_name` and `TF_VAR_opensearch_master_user_password`: If you want Terraform to create a master user for OpenSearch Fine-Grained Access Control (FGAC). **Ensure the password is strong.** If you leave these commented out or `null`, a master user will not be created by these Terraform scripts (you might need to configure it manually or it might be auto-created by AWS with temporary credentials you retrieve from the console).
    *   Other `TF_VAR_*` variables can be adjusted as needed.

    **Important:** The `.env` file is listed in `.gitignore` and should **never** be committed to version control if it contains sensitive information.

### 3. Load Environment Variables

For Terraform to pick up the variables defined in your `.env` file (prefixed with `TF_VAR_`), you need to load them into your shell session before running Terraform commands.

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

## Terraform Commands

Ensure you are in the `terraform` directory for all commands.

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
*   `opensearch_domain_endpoint`: The endpoint for your OpenSearch domain.
*   `opensearch_domain_kibana_endpoint`: The URL for OpenSearch Dashboards.
*   `kinesis_stream_name`: The name of your Kinesis Data Stream.

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
    *   You'll need to send the output of this script to the Kinesis Data Stream. The easiest way is to modify `sample_log_generator.py` to use AWS SDK (Boto3) to put records into the stream.
    *   Alternatively, use the AWS CLI. First, get your Kinesis stream name from Terraform output:
        ```bash
        STREAM_NAME=$(terraform output -raw kinesis_stream_name)
        ```
    *   Then, run the generator and pipe one log to AWS CLI (example for one log):
        ```bash
        # Example: Generate one Okta log and send it
        python ../sample_log_generator.py --provider okta --count 1 | jq -c . | xargs -I {} aws kinesis put-record --stream-name $STREAM_NAME --partition-key "test-pk" --data {}
        ```
        (Note: `sample_log_generator.py` would need modification to output single JSON objects per line and accept arguments for provider/count for this one-liner to work directly. The current generator prints multiple logs and descriptive text).

        A more robust way is to modify `sample_log_generator.py` as shown in the main PoC README to directly send logs to Kinesis using Boto3. Ensure the `provider` and `log` structure is maintained for the Lambda transformer.

2.  **Verify Data:**
    *   Check CloudWatch Logs for the Lambda function and Kinesis Data Firehose for any errors.
    *   Query data in OpenSearch Dashboards (Dev Tools or Discover tab) to see if transformed logs are arriving in the `siem-identity-logs-*` indices.
    *   Check your dashboard visualizations.

## File Structure Overview

```
terraform/
├── .env.example            # Example environment variables
├── .gitignore              # Files to ignore for Git
├── main.tf                 # Main configuration, locals
├── providers.tf            # Provider configurations
├── variables.tf            # Input variables
├── outputs.tf              # Output values
├── iam.tf                  # IAM roles and policies
├── s3.tf                   # S3 bucket for Firehose backups
├── kinesis_stream.tf       # Kinesis Data Stream
├── lambda.tf               # Lambda function and related resources
├── lambda_code/            # Directory for Lambda source code
│   └── transformation_lambda.py # Copied Lambda transformation script
├── opensearch.tf           # OpenSearch domain
├── firehose.tf             # Kinesis Data Firehose delivery stream
└── README.md               # This file
```

## Cleanup

Remember to run `terraform destroy` when you no longer need the resources to avoid ongoing AWS charges.
```
