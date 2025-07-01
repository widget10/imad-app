resource "aws_s3_bucket" "firehose_backup_bucket" {
  bucket = local.firehose_s3_bucket_name

  tags = merge(local.common_tags, {
    Name = local.firehose_s3_bucket_name
  })
}

resource "aws_s3_bucket_server_side_encryption_configuration" "firehose_backup_bucket_sse" {
  bucket = aws_s3_bucket.firehose_backup_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "firehose_backup_bucket_access_block" {
  bucket = aws_s3_bucket.firehose_backup_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "firehose_backup_bucket_versioning" {
  bucket = aws_s3_bucket.firehose_backup_bucket.id
  versioning_configuration {
    status = "Enabled" # Optional: enable versioning for better data protection
  }
}

# Optional: Lifecycle rule to transition or expire old backups
resource "aws_s3_bucket_lifecycle_configuration" "firehose_backup_bucket_lifecycle" {
  depends_on = [aws_s3_bucket.firehose_backup_bucket]
  bucket     = aws_s3_bucket.firehose_backup_bucket.id

  rule {
    id      = "archiveOldBackups"
    status  = "Enabled"

    filter {} # Apply to all objects in the bucket

    transition {
      days          = 30
      storage_class = "STANDARD_IA" # Transition to Infrequent Access after 30 days
    }

    transition {
      days          = 90
      storage_class = "GLACIER_IR" # Transition to Glacier Instant Retrieval after 90 days
    }

    expiration {
      days = 365 # Expire objects after 1 year
    }
  }
}
