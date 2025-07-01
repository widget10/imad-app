resource "aws_kinesis_stream" "raw_logs_stream" {
  name        = local.kinesis_stream_name
  shard_count = var.kinesis_stream_shard_count

  # Optional: Define retention period (default is 24 hours, max is 365 days or 8760 hours)
  # retention_period = 48 # hours

  # Optional: Enable server-side encryption for the stream
  # stream_mode_details {
  #   stream_mode = "PROVISIONED" # Default, can also be ON_DEMAND
  # }
  # encryption_type = "KMS" # or "NONE"
  # kms_key_id = "alias/aws/kinesis" # Example: Use AWS managed KMS key for Kinesis

  tags = merge(local.common_tags, {
    Name = local.kinesis_stream_name
  })
}
