variable "project_id" {
  description = "ID del proyecto GCP"
  type        = string
}

variable "region" {
  description = "Región GCP"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "Zona GCP"
  type        = string
  default     = "us-central1-a"
}

variable "num_workers" {
  description = "Número de VMs worker a crear"
  type        = number
  default     = 2
}

variable "worker_machine_type" {
  description = "Tipo de máquina para workers"
  type        = string
  default     = "e2-medium"
}

variable "rabbitmq_machine_type" {
  description = "Tipo de máquina para RabbitMQ"
  type        = string
  default     = "e2-small"
}

variable "worker_image" {
  description = "Imagen Docker del worker en Docker Hub"
  type        = string
  default     = "DOCKERHUB_USER/sobel-worker:latest"
}

variable "rabbitmq_user" {
  description = "Usuario RabbitMQ"
  type        = string
  default     = "admin"
}

variable "rabbitmq_pass" {
  description = "Password RabbitMQ"
  type        = string
  sensitive   = true
}

variable "os_image" {
  description = "Imagen del SO para las VMs"
  type        = string
  default     = "debian-cloud/debian-12"
}

variable "tfstate_bucket" {
  description = "Nombre del bucket GCS para el estado remoto de Terraform"
  type        = string
}
