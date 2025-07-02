locals {
  # Common tags to be applied to all resources
  common_tags = {
    Project   = var.project_name
    Terraform = "true"
    PoC       = "SIEM-Lake-Identity"
  }

  # Resource naming convention: project_name-resource_type-name_suffix
  opensearch_domain_name            = var.opensearch_domain_name # User-defined, potentially global for easier reference
  msk_cluster_name                  = "${var.project_name}-msk-cluster"
  msk_topic_name                    = var.msk_topic_name # From variables.tf

  lambda_msk_consumer_function_name = "${var.project_name}-msk-consumer-lambda"
  lambda_msk_consumer_role_name     = "${var.project_name}-msk-consumer-lambda-role"

  # S3 bucket for general purpose or future use if needed (e.g. MSK logs, not Firehose specific anymore)
  # If the S3 bucket was ONLY for Firehose and Firehose is removed, this might be removed too,
  # unless MSK broker logs or other logs are intended to be stored here.
  # For now, let's assume it's repurposed or removed if not used by MSK logging.
  # If MSK broker logging to S3 is enabled, it would need a bucket.
  # The current iam.tf and s3.tf still define `firehose_backup_bucket` related names.
  # This needs to be reconciled. For now, I will comment out the s3 bucket name if it's not used.
  # firehose_s3_bucket_name     = "${var.project_name}-msk-logs-backup-${data.aws_caller_identity.current.account_id}"


  # Path for Lambda code (original transformation logic, might be reused or parts copied)
  # This path is now primarily for the msk_consumer_lambda.py
  lambda_code_path            = "${path.module}/lambda_code"
  # This specific zip path was for the old lambda, will be handled by msk_consumer_lambda_zip in lambda_msk_consumer.tf
  # lambda_zip_path             = "${path.module}/lambda_code_payload.zip"
  # lambda_source_file          = "${local.lambda_code_path}/transformation_lambda.py" # Old source file

  # New source file for MSK consumer
  msk_consumer_lambda_source_file = "${local.lambda_code_path}/msk_consumer_lambda.py"
}

# Data source to get current AWS account ID (e.g. for globally unique S3 bucket names if still needed)
data "aws_caller_identity" "current" {}

# Data source to get current AWS region
data "aws_region" "current" {}
```
