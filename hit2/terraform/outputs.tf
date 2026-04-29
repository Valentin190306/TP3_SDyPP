output "rabbitmq_public_ip" {
  description = "IP pública de la VM RabbitMQ"
  value       = google_compute_instance.rabbitmq_vm.network_interface[0].access_config[0].nat_ip
}

output "rabbitmq_internal_ip" {
  description = "IP interna de la VM RabbitMQ"
  value       = google_compute_instance.rabbitmq_vm.network_interface[0].network_ip
}

output "worker_public_ips" {
  description = "IPs públicas de los workers"
  value       = [for vm in google_compute_instance.worker_vms : vm.network_interface[0].access_config[0].nat_ip]
}

output "rabbitmq_amqp_url" {
  description = "URL AMQP para conectar el master local a RabbitMQ"
  value       = "amqp://${var.rabbitmq_user}:***@${google_compute_instance.rabbitmq_vm.network_interface[0].access_config[0].nat_ip}:5672"
  sensitive   = false
}
