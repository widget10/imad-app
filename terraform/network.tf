# --- VPC ---
resource "aws_vpc" "siem_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-vpc"
  })
}

# --- Subnets ---
# Create 2 private subnets for MSK and Lambda, and 2 public for NAT Gateways for HA
# For simplicity in PoC, we might only use 2 AZs. Production would typically use 3.
data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_subnet" "private_subnet_az1" {
  vpc_id            = aws_vpc.siem_vpc.id
  cidr_block        = var.private_subnet_cidrs[0]
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-private-subnet-az1"
    Tier = "Private"
  })
}

resource "aws_subnet" "private_subnet_az2" {
  vpc_id            = aws_vpc.siem_vpc.id
  cidr_block        = var.private_subnet_cidrs[1]
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-private-subnet-az2"
    Tier = "Private"
  })
}

resource "aws_subnet" "public_subnet_az1" {
  vpc_id                  = aws_vpc.siem_vpc.id
  cidr_block              = var.public_subnet_cidrs[0]
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true # For NAT Gateway

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-public-subnet-az1"
    Tier = "Public"
  })
}

resource "aws_subnet" "public_subnet_az2" {
  vpc_id                  = aws_vpc.siem_vpc.id
  cidr_block              = var.public_subnet_cidrs[1]
  availability_zone       = data.aws_availability_zones.available.names[1]
  map_public_ip_on_launch = true # For NAT Gateway

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-public-subnet-az2"
    Tier = "Public"
  })
}

# --- Internet Gateway ---
resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.siem_vpc.id

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-igw"
  })
}

# --- NAT Gateways & EIPs ---
resource "aws_eip" "nat_eip_az1" {
  domain      = "vpc" # Changed from 'vpc = true' for newer provider versions
  depends_on = [aws_internet_gateway.gw]
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-nat-eip-az1"
  })
}

resource "aws_nat_gateway" "nat_gw_az1" {
  allocation_id = aws_eip.nat_eip_az1.id
  subnet_id     = aws_subnet.public_subnet_az1.id
  depends_on    = [aws_internet_gateway.gw]

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-nat-gw-az1"
  })
}

resource "aws_eip" "nat_eip_az2" {
  domain      = "vpc"
  depends_on = [aws_internet_gateway.gw]
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-nat-eip-az2"
  })
}

resource "aws_nat_gateway" "nat_gw_az2" {
  allocation_id = aws_eip.nat_eip_az2.id
  subnet_id     = aws_subnet.public_subnet_az2.id
  depends_on    = [aws_internet_gateway.gw]

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-nat-gw-az2"
  })
}

# --- Route Tables ---
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.siem_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-public-rt"
  })
}

resource "aws_route_table_association" "public_assoc_az1" {
  subnet_id      = aws_subnet.public_subnet_az1.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_route_table_association" "public_assoc_az2" {
  subnet_id      = aws_subnet.public_subnet_az2.id
  route_table_id = aws_route_table.public_rt.id
}


resource "aws_route_table" "private_rt_az1" {
  vpc_id = aws_vpc.siem_vpc.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat_gw_az1.id
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-private-rt-az1"
  })
}

resource "aws_route_table_association" "private_assoc_az1" {
  subnet_id      = aws_subnet.private_subnet_az1.id
  route_table_id = aws_route_table.private_rt_az1.id
}

resource "aws_route_table" "private_rt_az2" {
  vpc_id = aws_vpc.siem_vpc.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat_gw_az2.id
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-private-rt-az2"
  })
}

resource "aws_route_table_association" "private_assoc_az2" {
  subnet_id      = aws_subnet.private_subnet_az2.id
  route_table_id = aws_route_table.private_rt_az2.id
}


# --- Security Groups ---
resource "aws_security_group" "msk_sg" {
  name        = "${var.project_name}-msk-sg"
  description = "Security group for MSK Cluster"
  vpc_id      = aws_vpc.siem_vpc.id

  # Ingress: Allow Kafka traffic from Lambda SG and other clients within VPC if needed
  # Kafka plaintext port 9092, TLS 9094. MSK default is TLS.
  # Using self here to allow broker-to-broker communication
  ingress {
    from_port   = 0 # All ports for self
    to_port     = 0
    protocol    = "-1" # All protocols for self
    self        = true
    description = "Allow MSK brokers to communicate with each other"
  }

  # Placeholder for Lambda SG. Will be updated once Lambda SG is defined or use source_security_group_id
  # ingress {
  #   from_port       = 9094 # Kafka TLS port
  #   to_port         = 9094
  #   protocol        = "tcp"
  #   security_groups = [aws_security_group.lambda_sg.id] # Reference Lambda SG
  #   description     = "Allow Kafka TLS traffic from Lambda"
  # }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-msk-sg"
  })
}

resource "aws_security_group" "lambda_sg" {
  name        = "${var.project_name}-lambda-msk-consumer-sg"
  description = "Security group for Lambda MSK consumer"
  vpc_id      = aws_vpc.siem_vpc.id

  # Ingress: Typically not needed if Lambda is only invoked by MSK event source mapping (not direct network calls to Lambda)
  # If it needs to receive traffic from other sources within VPC, add rules here.

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"] # Allows outbound to MSK, OpenSearch, internet (for AWS SDKs, etc.)
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-lambda-msk-consumer-sg"
  })
}

# Add specific rule to MSK SG to allow traffic from Lambda SG on Kafka ports
resource "aws_security_group_rule" "allow_lambda_to_msk_kafka_tls" {
  type                     = "ingress"
  from_port                = 9094 # Kafka TLS port (MSK default)
  to_port                  = 9094
  protocol                 = "tcp"
  security_group_id        = aws_security_group.msk_sg.id
  source_security_group_id = aws_security_group.lambda_sg.id
  description              = "Allow Kafka TLS from Lambda MSK Consumer SG"
}

resource "aws_security_group_rule" "allow_lambda_to_msk_kafka_plaintext" {
  type                     = "ingress"
  from_port                = 9092 # Kafka Plaintext port
  to_port                  = 9092
  protocol                 = "tcp"
  security_group_id        = aws_security_group.msk_sg.id
  source_security_group_id = aws_security_group.lambda_sg.id
  description              = "Allow Kafka Plaintext from Lambda MSK Consumer SG (if plaintext enabled on MSK)"
}

# Security group for OpenSearch if deployed in VPC
resource "aws_security_group" "opensearch_sg" {
  name        = "${var.project_name}-opensearch-sg"
  description = "Security group for OpenSearch Domain"
  vpc_id      = aws_vpc.siem_vpc.id

  ingress {
    from_port       = 443 # HTTPS for OpenSearch endpoint
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id] # Allow access from Lambda
    description     = "Allow HTTPS from Lambda MSK Consumer SG"
  }

  # Add other ingress rules as needed, e.g., from your VPN or specific Bastion host for Dashboards access.
  # For example, to allow access from a specific IP for Dashboards (if not using public endpoint + FGAC):
  # ingress {
  #   from_port   = 443
  #   to_port     = 443
  #   protocol    = "tcp"
  #   cidr_blocks = var.dashboard_access_ip_ranges # Use with caution if these are public IPs
  #   description = "Allow HTTPS for Dashboards from specified IPs"
  # }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-opensearch-sg"
  })
}
```
