terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    prefix = "hit2/state"
    # bucket se pasa via: terraform init -backend-config="bucket=NOMBRE"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
