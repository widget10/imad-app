# IAM Role for Lambda Transformation Function
resource "aws_iam_role" "lambda_transformer_role" {
  name               = local.lambda_role_name
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

# Policy for Lambda to write to CloudWatch Logs
resource "aws_iam_policy" "lambda_logging_policy" {
  name        = "${var.project_name}-lambda-logging-policy"
  description = "Allows Lambda functions to write logs to CloudWatch."
  policy      = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Effect   = "Allow",
        Resource = "arn:aws:logs:*:*:*" # Restrict if possible, e.g., to specific log group prefix
      }
    ]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_logging_attachment" {
  role       = aws_iam_role.lambda_transformer_role.name
  policy_arn = aws_iam_policy.lambda_logging_policy.arn
}

# IAM Role for Kinesis Firehose Delivery Stream
resource "aws_iam_role" "firehose_delivery_role" {
  name               = local.firehose_role_name
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
      {
        # Allow Firehose to read from the Kinesis Data Stream
        Effect   = "Allow",
        Action   = [
          "kinesis:DescribeStream",
          "kinesis:GetShardIterator",
          "kinesis:GetRecords",
          "kinesis:ListShards"
        ],
        Resource = aws_kinesis_stream.raw_logs_stream.arn
      },
      {
        # Allow Firehose to invoke the Lambda transformation function
        Effect   = "Allow",
        Action   = "lambda:InvokeFunction",
        Resource = aws_lambda_function.transformer_lambda.arn
      },
      {
        # Allow Firehose to write to the OpenSearch domain
        Effect   = "Allow",
        Action   = [
          "es:ESHttpPost", // For older ES versions, OpenSearch uses "es:*" or specific "aoss:*"
          "es:ESHttpPut",
          "es:DescribeDomain", // General OpenSearch actions might use "es:DescribeDomain" or "aoss:DescribeDomain"
          "es:DescribeDomains",
          "es:DescribeDomainConfig",
           // For OpenSearch Serverless, permissions are different (e.g. aoss:BatchGetCollection)
           // For managed OpenSearch Service, these are typical for Firehose data ingestion
          "es:ESHttpHead", // May be needed for some versions
          "es:Put*"      // Broad, but often used. Consider more granular if possible.
        ],
        Resource = ["${aws_opensearch_domain.siem_domain.arn}/*", aws_opensearch_domain.siem_domain.arn] // Access to the domain and its sub-resources (indices)
      },
      {
         // Allow Firehose to write to S3 backup bucket
        Effect = "Allow",
        Action = [
          "s3:AbortMultipartUpload",
          "s3:GetBucketLocation",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:ListBucketMultipartUploads",
          "s3:PutObject"
        ],
        Resource = [
          aws_s3_bucket.firehose_backup_bucket.arn,
          "${aws_s3_bucket.firehose_backup_bucket.arn}/*" // Access to objects within the bucket
        ]
      },
      {
        # Allow Firehose to write to CloudWatch Logs for its own logging
        Effect   = "Allow",
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "arn:aws:logs:*:*:log-group:/aws/kinesisfirehose/${local.firehose_delivery_stream_name}:*"
      }
    ]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "firehose_delivery_attachment" {
  role       = aws_iam_role.firehose_delivery_role.name
  policy_arn = aws_iam_policy.firehose_delivery_policy.arn
}

# Note: The OpenSearch domain policy (resource-based) will also grant Firehose write access.
# This IAM role policy grants Firehose the *ability* to make those calls.
```
