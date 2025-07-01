data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = local.lambda_code_path
  output_path = local.lambda_zip_path

  # Re-package if the content of the Python file changes
  # This uses the filemd5 function to detect changes in the specified file.
  # Note: If you have multiple source files or dependencies, you might need a more robust way
  # to track changes, e.g., hashing all files in source_dir or using a build script.
  # For a single file, filemd5 is straightforward.
  # However, source_dir already triggers re-packaging if any file in it changes.
  # Adding an explicit filemd5 can be an extra measure if needed or for clarity.
  # For simplicity with source_dir, an explicit file hash isn't strictly necessary here
  # as archive_file monitors the source_dir content.
}

resource "aws_lambda_function" "transformer_lambda" {
  filename      = data.archive_file.lambda_zip.output_path
  function_name = local.lambda_function_name
  role          = aws_iam_role.lambda_transformer_role.arn
  handler       = var.lambda_handler_name
  runtime       = var.lambda_runtime
  memory_size   = var.lambda_memory_size
  timeout       = var.lambda_timeout

  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      # Add any environment variables your Lambda function might need
      # EXAMPLE_VAR = "example_value"
    }
  }

  tags = merge(local.common_tags, {
    Name = local.lambda_function_name
  })

  # If using VPC, configure vpc_config here
  # vpc_config {
  #   subnet_ids         = ["subnet-xxxxxxxxxxxxxxxxx", "subnet-yyyyyyyyyyyyyyyyy"]
  #   security_group_ids = ["sg-zzzzzzzzzzzzzzzzz"]
  # }
}

resource "aws_lambda_permission" "allow_firehose_invocation" {
  statement_id  = "AllowExecutionFromKinesisFirehose"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.transformer_lambda.function_name
  principal     = "firehose.amazonaws.com"
  # Source ARN for Firehose will be dynamic, so we need to construct it carefully
  # It should be the ARN of the Firehose delivery stream that will invoke this Lambda
  # This creates a slight dependency challenge if Firehose ARN is not known yet,
  # or if Firehose references Lambda and Lambda references Firehose (circular).
  # Typically, Firehose config references Lambda, so Lambda permission is on Lambda.
  # The source_arn should be the ARN of the specific Firehose delivery stream.
  source_arn    = "arn:aws:firehose:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:deliverystream/${local.firehose_delivery_stream_name}"
  # Ensure this matches the name of the Firehose stream defined in firehose.tf
  # This implies that firehose_delivery_stream_name local variable must be accurate.
}

# Optional: CloudWatch Log Group for the Lambda function
# AWS Lambda creates one automatically, but you can define it explicitly for more control (e.g., retention)
resource "aws_cloudwatch_log_group" "transformer_lambda_lg" {
  name              = "/aws/lambda/${local.lambda_function_name}"
  retention_in_days = 14 # Optional: set retention period

  tags = merge(local.common_tags, {
    Name = "/aws/lambda/${local.lambda_function_name}"
  })
}
```
