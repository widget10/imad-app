# Placeholder for Lambda code - this will be created in a later step.
# For now, we can create a dummy zip file or use the existing transformation_lambda.py
# temporarily to allow Terraform to plan/apply the Lambda resource structure.

data "archive_file" "msk_consumer_lambda_zip" {
  type        = "zip"
  # Temporarily point to the old lambda code path or an empty directory with a dummy file
  # This will be updated when msk_consumer_lambda.py is created.
  source_dir  = local.lambda_code_path # This currently points to the dir with transformation_lambda.py
  output_path = "${path.module}/msk_consumer_lambda_payload.zip" # New zip file name
  # In a real scenario with dependencies, source_dir would point to a directory containing
  # msk_consumer_lambda.py AND its dependencies (e.g., kafka-python, opensearch-py).
}

resource "aws_lambda_function" "msk_consumer_lambda" {
  filename      = data.archive_file.msk_consumer_lambda_zip.output_path
  function_name = local.lambda_msk_consumer_function_name # New local variable needed in main.tf
  role          = aws_iam_role.lambda_msk_consumer_role.arn
  handler       = "msk_consumer_lambda.lambda_handler" # Assumes new handler file name
  runtime       = var.lambda_runtime                   # e.g., python3.9
  memory_size   = var.lambda_memory_size               # e.g., 256 or 512 MB for Kafka client
  timeout       = var.lambda_timeout                   # e.g., 300 seconds (5 minutes) for batch processing

  source_code_hash = data.archive_file.msk_consumer_lambda_zip.output_base64sha256

  # VPC Configuration - essential for Lambda to access MSK and OpenSearch in the VPC
  vpc_config {
    subnet_ids         = [aws_subnet.private_subnet_az1.id, aws_subnet.private_subnet_az2.id]
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      OPENSEARCH_ENDPOINT = aws_opensearch_domain.siem_domain.endpoint # Pass OpenSearch endpoint to Lambda
      MSK_TOPIC_NAME      = var.msk_topic_name
      # Add other necessary environment variables
    }
  }

  tags = merge(local.common_tags, {
    Name = local.lambda_msk_consumer_function_name
  })
}

resource "aws_lambda_event_source_mapping" "msk_trigger" {
  function_name = aws_lambda_function.msk_consumer_lambda.arn
  topics        = [var.msk_topic_name]
  # Starting position: LATEST or TRIM_HORIZON
  starting_position = "LATEST"

  # The event_source_arn for MSK is the cluster ARN.
  # For self-managed Kafka, it would include specific broker details.
  event_source_arn = aws_msk_cluster.siem_msk_cluster.arn

  batch_size = 100 # Number of records to read from the topic in each batch (default 100, max 10000)
  # maximum_batching_window_in_seconds = 60 # Optional: Max time to gather records before invoking Lambda

  # Optional: Configure what happens on function error
  # destination_config {
  #   on_failure {
  #     destination_arn = aws_sqs_queue.dead_letter_queue.arn # Example: send to SQS DLQ
  #   }
  # }

  enabled = true # Set to false to disable the trigger initially
}

# Optional: CloudWatch Log Group for the MSK Consumer Lambda function
resource "aws_cloudwatch_log_group" "msk_consumer_lambda_lg" {
  name              = "/aws/lambda/${local.lambda_msk_consumer_function_name}"
  retention_in_days = 14

  tags = merge(local.common_tags, {
    Name = "/aws/lambda/${local.lambda_msk_consumer_function_name}"
  })
}
```
