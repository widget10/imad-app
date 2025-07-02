# --- IAM Role and Policies for Lambda MSK Consumer ---
resource "aws_iam_role" "lambda_msk_consumer_role" {
  name               = local.lambda_msk_consumer_role_name # New local variable needed in main.tf
  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Action    = "sts:AssumeRole",
        Effect    = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  tags = local.common_tags
}

# Managed policy for MSK access (provides necessary Kafka client permissions)
resource "aws_iam_role_policy_attachment" "lambda_msk_execution_role_attachment" {
  role       = aws_iam_role.lambda_msk_consumer_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaMSKExecutionRole"
}

# Managed policy for VPC access (to connect to MSK and OpenSearch in VPC)
resource "aws_iam_role_policy_attachment" "lambda_vpc_access_attachment" {
  role       = aws_iam_role.lambda_msk_consumer_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Inline policy for CloudWatch Logs and OpenSearch Write Access
resource "aws_iam_policy" "lambda_msk_consumer_custom_policy" {
  name        = "${var.project_name}-lambda-msk-consumer-custom-policy"
  description = "Custom policy for MSK Consumer Lambda: CloudWatch Logs and OpenSearch write."
  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Effect   = "Allow",
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.lambda_msk_consumer_function_name}:*"
      },
      {
        # Allow Lambda to write to the OpenSearch domain
        Effect   = "Allow",
        Action   = [
          "es:ESHttpPost",
          "es:ESHttpPut"
          # Add "es:ESHttpHead" if your client library uses it for health checks
        ],
        # Ensure this ARN matches your OpenSearch domain ARN and allows access to indices
        Resource = "${aws_opensearch_domain.siem_domain.arn}/*"
      }
    ]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_msk_consumer_custom_attachment" {
  role       = aws_iam_role.lambda_msk_consumer_role.name
  policy_arn = aws_iam_policy.lambda_msk_consumer_custom_policy.arn
}


# --- (Commented Out/Removed) Kinesis Firehose Related IAM Resources ---
/*
# IAM Role for Kinesis Firehose Delivery Stream
resource "aws_iam_role" "firehose_delivery_role" {
  name               = local.firehose_role_name # Ensure local.firehose_role_name is defined or remove
  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Action    = "sts:AssumeRole",
        Effect    = "Allow",
        Principal = {
          Service = "firehose.amazonaws.com"
        }
      }
    ]
  })
  tags = local.common_tags
}

# Policy for Kinesis Firehose
resource "aws_iam_policy" "firehose_delivery_policy" {
  name        = "${var.project_name}-firehose-delivery-policy"
  description = "Policy for Kinesis Firehose to access necessary resources."
  policy      = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      // ... statements for Kinesis Stream read, old Lambda invoke, OpenSearch write, S3 write ...
    ]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "firehose_delivery_attachment" {
  role       = aws_iam_role.firehose_delivery_role.name
  policy_arn = aws_iam_policy.firehose_delivery_policy.arn
}
*/

# Note: The original lambda_transformer_role and its logging policy might still be relevant
# if the transformation logic is complex and kept in a separate Lambda invoked by the MSK consumer.
# For this refactor, we are assuming the MSK consumer Lambda handles transformation directly.
# If that's not the case, uncomment and adjust as needed.
# The old "lambda_transformer_role" and "lambda_logging_policy" are implicitly removed if
# local.lambda_role_name is no longer defined or used.
# Ensure local variables for old resources are removed from main.tf if they are fully deprecated.
```
