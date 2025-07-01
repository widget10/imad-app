resource "aws_opensearch_domain" "siem_domain" {
  domain_name    = var.opensearch_domain_name
  engine_version = var.opensearch_engine_version

  cluster_config {
    instance_type           = var.opensearch_instance_type
    instance_count          = var.opensearch_instance_count
    dedicated_master_enabled = var.opensearch_dedicated_master_enabled
    dedicated_master_count  = var.opensearch_dedicated_master_enabled ? var.opensearch_dedicated_master_count : null
    dedicated_master_type   = var.opensearch_dedicated_master_enabled ? var.opensearch_dedicated_master_type : null
    zone_awareness_enabled  = var.opensearch_instance_count > 1 # Enable if more than 1 instance for higher availability
    # warm_enabled = false # Optional: for UltraWarm nodes
  }

  ebs_options {
    ebs_enabled = true
    volume_size = var.opensearch_ebs_volume_size
    volume_type = "gp3" # General Purpose SSD gp3
  }

  node_to_node_encryption {
    enabled = true
  }

  encrypt_at_rest {
    enabled = true
    # kms_key_id = "arn:aws:kms:..." # Optional: specify a customer-managed KMS key
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07" # Recommended TLS policy
  }

  advanced_security_options {
    enabled                        = true
    internal_user_database_enabled = var.opensearch_master_user_name != null ? true : false # Enable if master user is to be created by TF
    master_user_options {
      master_user_name     = var.opensearch_master_user_name != null ? var.opensearch_master_user_name : null
      master_user_password = var.opensearch_master_user_name != null ? var.opensearch_master_user_password : null
    }
  }

  # For PoC, keeping it simple by not using VPC. For production, VPC is highly recommended.
  # vpc_options {
  #   subnet_ids         = ["subnet-xxxxxxxxxxxxxxxxx"]
  #   security_group_ids = ["sg-yyyyyyyyyyyyyyyyy"]
  # }

  # Access policy: Allows access from specified IPs and the Kinesis Firehose role
  # This policy is crucial for Firehose to write data and for users to access Dashboards.
  access_policies = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = {
          AWS = "*" # Allows FGAC to handle auth. Or specify specific IAM users/roles.
        },
        Action    = "es:*", # Or "aoss:*" for serverless. Use more granular permissions in production.
        Resource  = "${aws_opensearch_domain.siem_domain.arn}/*"
        # Condition to restrict by IP for dashboard access
        # Condition = {
        #   IpAddress = {
        #     "aws:SourceIp" = var.dashboard_access_ip_ranges
        #   }
        # }
      },
      # Statement to allow Kinesis Firehose to write to the domain
      {
        Effect = "Allow",
        Principal = {
          AWS = aws_iam_role.firehose_delivery_role.arn
        },
        Action = [
            "es:ESHttpHead",
            "es:ESHttpPost",
            "es:ESHttpPut",
            "es:DescribeDomain",
            "es:DescribeDomains",
            "es:DescribeDomainConfig"
            // Add other "es:*" or "aoss:*" permissions as needed by Firehose
        ],
        Resource = "${aws_opensearch_domain.siem_domain.arn}/*"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = var.opensearch_domain_name
  })

  # Depending on the size and configuration, OpenSearch domains can take a while to create.
  # timeouts {
  #   create = "60m"
  #   update = "120m" # Updates, especially those requiring blue/green, can take longer
  #   delete = "90m"
  # }
}

# Note: The OpenSearch Index Template (opensearch_index_template.json)
# needs to be applied manually via OpenSearch Dashboards Dev Tools or API after the domain is active.
# Terraform does not have a native resource for managing OpenSearch index templates directly.
# A local-exec provisioner could be used, but manual application is simpler for this PoC.
```
