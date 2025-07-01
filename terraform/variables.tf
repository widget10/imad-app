variable "aws_region" {
  description = "AWS region where resources will be deployed."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "A name for the project, used to prefix resource names for uniqueness and grouping."
  type        = string
  default     = "siem-poc"
}

variable "opensearch_domain_name" {
  description = "Name for the AWS OpenSearch domain."
  type        = string
  default     = "siem-identity-logs"
}

variable "opensearch_engine_version" {
  description = "Version of OpenSearch to deploy (e.g., OpenSearch_2.11)."
  type        = string
  default     = "OpenSearch_2.11" # Check AWS console for latest supported versions
}

variable "opensearch_instance_type" {
  description = "Instance type for OpenSearch data nodes."
  type        = string
  default     = "t3.small.search" # Suitable for PoC, consider larger for production
}

variable "opensearch_instance_count" {
  description = "Number of data nodes in the OpenSearch cluster."
  type        = number
  default     = 1 # For PoC, 1 or 2. Production needs at least 3 for HA.
}

variable "opensearch_dedicated_master_enabled" {
  description = "Enable dedicated master nodes for OpenSearch."
  type        = bool
  default     = false # For PoC. Production with >10 nodes should use dedicated masters.
}

variable "opensearch_dedicated_master_count" {
  description = "Number of dedicated master nodes (if enabled)."
  type        = number
  default     = 3 # Ignored if dedicated_master_enabled is false.
}

variable "opensearch_dedicated_master_type" {
  description = "Instance type for dedicated master nodes (if enabled)."
  type        = string
  default     = "t3.small.search" # Ignored if dedicated_master_enabled is false.
}

variable "opensearch_ebs_volume_size" {
  description = "Size of the EBS volume for each OpenSearch data node in GB."
  type        = number
  default     = 10 # Minimum for t3.small.search
}

variable "opensearch_master_user_name" {
  description = "Username for the OpenSearch master user (fine-grained access control). If not provided, no master user is created by Terraform."
  type        = string
  default     = null # Set to a specific username if you want Terraform to manage it.
  nullable    = true
}

variable "opensearch_master_user_password" {
  description = "Password for the OpenSearch master user. Required if master_user_name is set. HIGHLY SENSITIVE."
  type        = string
  default     = null # Must be provided if master_user_name is set.
  sensitive   = true
  nullable    = true
}

variable "dashboard_access_ip_ranges" {
  description = "List of CIDR blocks allowed to access the OpenSearch domain endpoint (for Dashboards). Use with caution. For production, restrict to specific IPs/VPNs or use VPC access."
  type        = list(string)
  default     = ["0.0.0.0/0"] # WARNING: Makes Dashboards publicly accessible. Secure with FGAC.
}

variable "kinesis_stream_shard_count" {
  description = "Number of shards for the Kinesis Data Stream."
  type        = number
  default     = 1
}

variable "lambda_runtime" {
  description = "Lambda function runtime."
  type        = string
  default     = "python3.9"
}

variable "lambda_handler_name" {
  description = "Lambda function handler name."
  type        = string
  default     = "transformation_lambda.lambda_handler"
}

variable "lambda_memory_size" {
  description = "Memory size in MB for the Lambda function."
  type        = number
  default     = 256
}

variable "lambda_timeout" {
  description = "Timeout in seconds for the Lambda function."
  type        = number
  default     = 60 # Kinesis Firehose default timeout for Lambda is 3 minutes.
}

# Note: AWS credentials (access key, secret key) are typically handled by the AWS provider
# through environment variables, shared credentials file (~/.aws/credentials), or IAM roles.
# Defining them as Terraform variables is generally discouraged for security reasons,
# but placeholders can be put in .env.example if users prefer that for local dev.
```
