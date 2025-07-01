resource "aws_kinesis_firehose_delivery_stream" "siem_delivery_stream" {
  name        = local.firehose_delivery_stream_name
  destination = "opensearch"

  kinesis_source_configuration {
    kinesis_stream_arn = aws_kinesis_stream.raw_logs_stream.arn
    role_arn           = aws_iam_role.firehose_delivery_role.arn
  }

  opensearch_configuration {
    role_arn           = aws_iam_role.firehose_delivery_role.arn
    domain_arn         = aws_opensearch_domain.siem_domain.arn
    index_name         = var.opensearch_domain_name # This is the prefix for indices
    type_name          = "_doc" # For OpenSearch, _doc is standard. For older ES, might be custom.
                               # With OpenSearch 2.x and removal of mapping types, this might be ignored or set to _doc.
    index_rotation_period = "OneDay" # Rotate index daily. Other options: OneHour, OneWeek, OneMonth, NoRotation
    retry_duration        = 300    # Seconds

    s3_backup_mode = "FailedDocumentsOnly" # Or "AllDocuments"
    s3_configuration {
      role_arn           = aws_iam_role.firehose_delivery_role.arn
      bucket_arn         = aws_s3_bucket.firehose_backup_bucket.arn
      prefix             = "failed_logs/" # Optional: prefix for S3 objects
      error_output_prefix = "error_logs/" # Optional: prefix for error logs if processing fails before S3 backup
      compression_format = "GZIP"
      # buffer_interval_in_seconds = 300 # Default: 300
      # buffer_size_in_mbs         = 5   # Default: 5
    }

    processing_configuration {
      enabled = "true"
      processors {
        type = "Lambda"
        parameters {
          parameter_name  = "LambdaArn"
          parameter_value = "${aws_lambda_function.transformer_lambda.arn}:$LATEST" # Use $LATEST or a specific version/alias
        }
      }
      # Optional: Increase buffer size/interval for Lambda invocation
      # parameters {
      #   parameter_name  = "BufferIntervalInSeconds"
      #   parameter_value = "60"
      # }
      # parameters {
      #   parameter_name  = "BufferSizeInMBs"
      #   parameter_value = "1"
      # }
    }

    # CloudWatch logging for Firehose (optional but recommended)
    # cloudwatch_logging_options {
    #   enabled         = true
    #   log_group_name  = "/aws/kinesisfirehose/${local.firehose_delivery_stream_name}"
    #   log_stream_name = "DestinationDelivery"
    # }
  }

  tags = merge(local.common_tags, {
    Name = local.firehose_delivery_stream_name
  })

  depends_on = [
    aws_iam_role.firehose_delivery_role,
    aws_opensearch_domain.siem_domain,
    aws_lambda_function.transformer_lambda,
    aws_kinesis_stream.raw_logs_stream
  ]
}
```
