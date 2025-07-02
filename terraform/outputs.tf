output "aws_region" {
  description = "AWS region where the resources are deployed."
  value       = var.aws_region
}

output "project_name" {
  description = "Name of the project used for resource prefixing."
  value       = var.project_name
}

output "opensearch_domain_endpoint" {
  description = "Endpoint for the OpenSearch domain."
  value       = aws_opensearch_domain.siem_domain.endpoint
}

output "opensearch_domain_kibana_endpoint" {
  description = "Kibana (OpenSearch Dashboards) endpoint for the OpenSearch domain."
  value       = aws_opensearch_domain.siem_domain.dashboard_endpoint # For OpenSearch_1.0 or later. Use kibana_endpoint for older.
}

output "opensearch_domain_arn" {
  description = "ARN of the OpenSearch domain."
  value       = aws_opensearch_domain.siem_domain.arn
}

# --- MSK Outputs ---
output "msk_cluster_arn" {
  description = "ARN of the MSK cluster."
  value       = aws_msk_cluster.siem_msk_cluster.arn
}

output "msk_bootstrap_brokers_tls" {
  description = "Comma-separated list of bootstrap broker endpoints for TLS connections."
  value       = aws_msk_cluster.siem_msk_cluster.bootstrap_brokers_tls
}

output "msk_bootstrap_brokers_plaintext" {
  description = "Comma-separated list of bootstrap broker endpoints for plaintext connections (if enabled)."
  value       = aws_msk_cluster.siem_msk_cluster.bootstrap_brokers_plaintext
  sensitive   = true # Plaintext brokers might be sensitive depending on network setup
}

output "msk_zookeeper_connect_string" {
  description = "Zookeeper connection string for the MSK cluster (for Kafka versions < 3.x or non-KRaft mode)."
  value       = aws_msk_cluster.siem_msk_cluster.zookeeper_connect_string
  sensitive   = true
}

output "msk_topic_name_configured" {
  description = "The configured Kafka topic name for identity logs."
  value       = var.msk_topic_name
}


# --- Lambda MSK Consumer Outputs ---
output "lambda_msk_consumer_function_name" {
  description = "Name of the Lambda MSK consumer function."
  value       = aws_lambda_function.msk_consumer_lambda.function_name
}

output "lambda_msk_consumer_function_arn" {
  description = "ARN of the Lambda MSK consumer function."
  value       = aws_lambda_function.msk_consumer_lambda.arn
}

output "lambda_msk_consumer_role_arn" {
  description = "ARN of the IAM role for the Lambda MSK consumer function."
  value       = aws_iam_role.lambda_msk_consumer_role.arn
}


# --- S3 Bucket Outputs (if still used, e.g., for MSK broker logs or general purpose) ---
output "s3_backup_bucket_name" {
  description = "Name of the S3 bucket (previously for Firehose, potentially for MSK logs or other uses)."
  value       = aws_s3_bucket.firehose_backup_bucket.bucket # This resource might be renamed or removed if not used by MSK
}

output "s3_backup_bucket_arn" {
  description = "ARN of the S3 bucket."
  value       = aws_s3_bucket.firehose_backup_bucket.arn # This resource might be renamed or removed
}


# --- Removed Kinesis and Firehose Outputs ---
# output "kinesis_stream_name" { ... }
# output "kinesis_stream_arn" { ... }
# output "firehose_delivery_stream_name" { ... }
# output "firehose_delivery_stream_arn" { ... }
# output "lambda_transformer_role_arn" { ... } # Replaced by lambda_msk_consumer_role_arn
# output "firehose_delivery_role_arn" { ... }
}
```
