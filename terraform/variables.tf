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
  description = "List of CIDR blocks allowed to access the OpenSearch domain endpoint (for Dashboards) if OpenSearch is not in VPC or needs specific external access. Use with caution."
  type        = list(string)
  default     = [] # Default to empty, encouraging VPC access or more specific IPs. ["0.0.0.0/0"] is too permissive.
}

# variable "kinesis_stream_shard_count" {
#   description = "Number of shards for the Kinesis Data Stream."
#   type        = number
#   default     = 1
# }

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
  default     = 60 # Default timeout. For MSK consumer, this might need to be higher depending on batch size and processing.
}

# --- VPC and Networking Variables ---
variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "List of CIDR blocks for public subnets (at least 2 for HA NAT Gateways)."
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "List of CIDR blocks for private subnets (at least 2 for MSK/Lambda in different AZs)."
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24"]
}

# --- MSK Specific Variables ---
variable "msk_broker_instance_type" {
  description = "EC2 instance type for MSK brokers."
  type        = string
  default     = "kafka.t3.small" # Smallest available, for PoC.
}

variable "msk_kafka_version" {
  description = "Apache Kafka version for MSK cluster."
  type        = string
  default     = "2.8.1" # Check AWS documentation for currently supported versions.
}

variable "msk_number_of_broker_nodes" {
  description = "Number of broker nodes in the MSK cluster. Must be a multiple of the number of AZs used (e.g., 2 if using 2 AZs)."
  type        = number
  default     = 2 # Minimum 2 for 2 AZs. For production, 3+ is recommended.
}

variable "msk_broker_ebs_volume_size" {
  description = "EBS volume size in GiB for each MSK broker."
  type        = number
  default     = 20 # Minimum can be 1GiB, but practical minimum depends on usage.
}

variable "msk_topic_name" {
  description = "Name of the Kafka topic to be used for identity logs."
  type        = string
  default     = "identity-logs"
}


# Note: AWS credentials (access key, secret key) are typically handled by the AWS provider
# through environment variables, shared credentials file (~/.aws/credentials), or IAM roles.
# Defining them as Terraform variables is generally discouraged for security reasons,
# but placeholders can be put in .env.example if users prefer that for local dev.
```
