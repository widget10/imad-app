resource "aws_msk_cluster" "siem_msk_cluster" {
  cluster_name           = "${var.project_name}-msk-cluster"
  kafka_version          = var.msk_kafka_version
  number_of_broker_nodes = var.msk_number_of_broker_nodes

  broker_node_group_info {
    instance_type = var.msk_broker_instance_type
    ebs_volume_size = var.msk_broker_ebs_volume_size # In GiB
    client_subnets = [
      aws_subnet.private_subnet_az1.id,
      aws_subnet.private_subnet_az2.id
      # Add a third subnet if var.msk_number_of_broker_nodes >= 3 and you have 3 AZs/subnets
    ]
    security_groups = [aws_security_group.msk_sg.id]

    # Optional: Storage throughput for gp3 volumes
    # storage_info {
    #   ebs_storage_info {
    #     provisioned_throughput = 125 # MiB/s, only for gp3
    #     volume_size = var.msk_broker_ebs_volume_size
    #   }
    # }
  }

  # Encryption settings
  encryption_info {
    encryption_in_transit {
      client_broker = "TLS" # Enforce TLS for client-broker communication. Options: TLS, TLS_PLAINTEXT, PLAINTEXT
      in_cluster    = true  # Enable TLS for inter-broker communication
    }
    # Optional: Encryption at rest using KMS
    # encryption_at_rest_kms_key_arn = "arn:aws:kms:..."
  }

  # Client Authentication (SASL/SCRAM is recommended for production, IAM is also an option)
  # For PoC, we might start with TLS encryption and VPC security group controls.
  # client_authentication {
  #   sasl {
  #     iam            = false # Set to true to enable IAM Access Control
  #     scram          = false # Set to true to enable SASL/SCRAM
  #   }
  #   tls {
  #     certificate_authority_arns = [] # Optional: For mutual TLS client authentication
  #   }
  # }


  # Monitoring level (PER_BROKER, PER_TOPIC_PER_BROKER, PER_TOPIC_PER_PARTITION)
  enhanced_monitoring = "PER_TOPIC_PER_BROKER"

  # Logging (optional, can send broker logs to CloudWatch, S3, or Kinesis Firehose)
  # logging_info {
  #   broker_logs {
  #     cloudwatch_logs {
  #       enabled   = true
  #       log_group = "/aws/msk/${var.project_name}-cluster-logs"
  #     }
  #     # s3 {
  #     #   enabled = true
  #     #   bucket  = "your-msk-logs-bucket-name" # Replace with your bucket name
  #     #   prefix  = "msk-broker-logs/"
  #     # }
  #   }
  # }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-msk-cluster"
  })

  # MSK clusters can take 20-30 minutes or more to create.
  timeouts {
    create = "60m"
    update = "60m" # Some updates can also be lengthy
    delete = "30m"
  }
}

# (Optional) MSK Configuration resource if you need to customize Kafka settings
# resource "aws_msk_configuration" "siem_msk_config" {
#   name           = "${var.project_name}-msk-config"
#   kafka_versions = [var.msk_kafka_version]
#   server_properties = <<-EOT
#     auto.create.topics.enable=true
#     # Add other Kafka broker properties here
#   EOT
#   description = "Custom MSK configuration for SIEM PoC"
# }

# Output the MSK Topic (if auto-create is enabled or created elsewhere)
# Terraform cannot directly create topics within MSK using aws_msk_cluster.
# Topic creation is typically done via Kafka admin tools or an application after cluster creation,
# or by enabling `auto.create.topics.enable=true` in MSK configuration.
# For this PoC, we will assume the topic defined in `var.msk_topic_name` will be auto-created if enabled,
# or created manually by the user. The Lambda event source mapping will reference this topic name.

# Note: If using IAM control for MSK, you'd need to set up `aws_msk_cluster_policy`
# and potentially IAM policies for clients.
```
