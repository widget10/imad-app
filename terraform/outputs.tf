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
  value       = aws_opensearch_domain.siem_domain.kibana_endpoint # For older versions, this might be dashboard_endpoint
                                                                 # aws_opensearch_domain.siem_domain.dashboard_endpoint is for OpenSearch_1.0 or later
}

output "opensearch_domain_arn" {
  description = "ARN of the OpenSearch domain."
  value       = aws_opensearch_domain.siem_domain.arn
}

output "kinesis_stream_name" {
  description = "Name of the Kinesis Data Stream."
  value       = aws_kinesis_stream.raw_logs_stream.name
}

output "kinesis_stream_arn" {
  description = "ARN of the Kinesis Data Stream."
  value       = aws_kinesis_stream.raw_logs_stream.arn
}

output "lambda_function_name" {
  description = "Name of the Lambda transformation function."
  value       = aws_lambda_function.transformer_lambda.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda transformation function."
  value       = aws_lambda_function.transformer_lambda.arn
}

output "firehose_delivery_stream_name" {
  description = "Name of the Kinesis Firehose delivery stream."
  value       = aws_kinesis_firehose_delivery_stream.siem_delivery_stream.name
}

output "firehose_delivery_stream_arn" {
  description = "ARN of the Kinesis Firehose delivery stream."
  value       = aws_kinesis_firehose_delivery_stream.siem_delivery_stream.arn
}

output "firehose_backup_s3_bucket_name" {
  description = "Name of the S3 bucket for Firehose backups."
  value       = aws_s3_bucket.firehose_backup_bucket.bucket
}

output "firehose_backup_s3_bucket_arn" {
  description = "ARN of the S3 bucket for Firehose backups."
  value       = aws_s3_bucket.firehose_backup_bucket.arn
}

output "lambda_transformer_role_arn" {
  description = "ARN of the IAM role for the Lambda transformation function."
  value       = aws_iam_role.lambda_transformer_role.arn
}

output "firehose_delivery_role_arn" {
  description = "ARN of the IAM role for the Kinesis Firehose delivery stream."
  value       = aws_iam_role.firehose_delivery_role.arn
}
```
