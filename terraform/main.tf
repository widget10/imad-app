locals {
  # Common tags to be applied to all resources
  common_tags = {
    Project   = var.project_name
    Terraform = "true"
    PoC       = "SIEM-Lake-Identity"
  }

  # Resource naming convention: project_name-resource_type-name_suffix
  # Suffixes can be defined in variables or kept static here if not configurable
  kinesis_stream_name         = "${var.project_name}-raw-logs-stream"
  lambda_function_name        = "${var.project_name}-transformer-lambda"
  firehose_s3_bucket_name     = "${var.project_name}-firehose-backups-${data.aws_caller_identity.current.account_id}" # Ensure bucket name uniqueness
  firehose_delivery_stream_name = "${var.project_name}-delivery-stream"
  opensearch_domain_name      = var.opensearch_domain_name # This one might not need project_name prefix if globally unique is desired or set by user

  lambda_role_name            = "${var.project_name}-lambda-transformer-role"
  firehose_role_name          = "${var.project_name}-firehose-delivery-role"

  lambda_code_path            = "${path.module}/lambda_code"
  lambda_zip_path             = "${path.module}/lambda_code_payload.zip"
  lambda_source_file          = "${local.lambda_code_path}/transformation_lambda.py" # Source file to watch for changes

}

# Data source to get current AWS account ID (e.g. for globally unique S3 bucket names)
data "aws_caller_identity" "current" {}

# Data source to get current AWS region (can be useful if not explicitly set elsewhere)
data "aws_region" "current" {}
```
