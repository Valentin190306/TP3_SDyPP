#!/bin/bash
set -e
exec > /var/log/bootstrap.log 2>&1

echo "[$(date)] Iniciando bootstrap de RabbitMQ..."

# Actualizar e instalar Docker
apt-get update -y
apt-get install -y docker.io curl
systemctl start docker
systemctl enable docker

# Levantar RabbitMQ con management plugin
docker run -d \
  --name rabbitmq \
  --restart unless-stopped \
  -p 5672:5672 \
  -p 15672:15672 \
  -e RABBITMQ_DEFAULT_USER=${rabbitmq_user} \
  -e RABBITMQ_DEFAULT_PASS=${rabbitmq_pass} \
  rabbitmq:management

echo "[$(date)] RabbitMQ iniciado correctamente"

# Esperar a que RabbitMQ esté listo
until docker exec rabbitmq rabbitmq-diagnostics ping 2>/dev/null; do
  echo "[$(date)] Esperando RabbitMQ..."
  sleep 5
done

echo "[$(date)] Bootstrap completo"
