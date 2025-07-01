terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.2.0"
    }
  }

  required_version = ">= 1.0"
}

provider "aws" {
  region = var.aws_region
  # Shared credentials file or environment variables will be used by default.
  # access_key = var.aws_access_key_id # Uncomment if using direct key/secret from vars (not recommended for production)
  # secret_key = var.aws_secret_access_key # Uncomment if using direct key/secret from vars (not recommended for production)
}
