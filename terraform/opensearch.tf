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

  # Deploy OpenSearch within the VPC for enhanced security
  vpc_options {
    subnet_ids         = [aws_subnet.private_subnet_az1.id, aws_subnet.private_subnet_az2.id]
    security_group_ids = [aws_security_group.opensearch_sg.id]
  }

  # Access policy: Allows access for FGAC master user (if defined) and the Lambda MSK consumer role.
  # If dashboard_access_ip_ranges is set, it allows access from those IPs.
  access_policies = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        # Allows all actions from within the VPC or specific IPs if configured,
        # relying on Fine-Grained Access Control (FGAC) for actual user/role permissions.
        Effect    = "Allow",
        Principal = { AWS = "*" }, # Or specify specific IAM roles/users if not using open access + FGAC
        Action    = "es:*",    # Or more granular permissions
        Resource  = "${aws_opensearch_domain.siem_domain.arn}/*",
        Condition = {
          # This condition ensures that if dashboard_access_ip_ranges is empty (recommended for VPC-only access),
          # then this part of the policy effectively only applies if accessed via VPC endpoint.
          # If dashboard_access_ip_ranges is populated, it allows from those IPs.
          # For purely VPC internal access, this IP condition might be further restricted or combined with VPC endpoint conditions.
          # For now, if dashboard_access_ip_ranges is empty, this condition won't match for external IPs, implicitly restricting.
          # A more robust VPC-only setup might use `aws:SourceVpc`.
          "ForAnyValue:IpAddressIfExists" = {
            "aws:SourceIp" = var.dashboard_access_ip_ranges
          }
        } if length(var.dashboard_access_ip_ranges) > 0 # Apply condition only if IPs are specified
      },
      # Statement to allow the Lambda MSK consumer to write to the domain
      {
        Effect = "Allow",
        Principal = {
          AWS = aws_iam_role.lambda_msk_consumer_role.arn
        },
        Action = [
          "es:ESHttpHead", # Often used by clients to check domain status
          "es:ESHttpPost", # For bulk API, sending data
          "es:ESHttpPut"   # For creating/updating templates, documents
        ],
        Resource = "${aws_opensearch_domain.siem_domain.arn}/*" # Access to the domain and its sub-resources (indices)
      }
      # Add a statement for the master user if defined by Terraform, allowing it full access
      # This is often handled by FGAC internal users, but an explicit policy can be a fallback/bootstrap.
      # Note: If opensearch_master_user_name is null, this statement should ideally be omitted.
      # However, conditional statements in JSON policies are tricky. FGAC is primary for user access.
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
