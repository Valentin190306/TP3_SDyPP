#!/bin/bash
set -e
exec > /var/log/bootstrap.log 2>&1

echo "[$(date)] Iniciando bootstrap worker..."

apt-get update -y
apt-get install -y docker.io
systemctl start docker
systemctl enable docker

echo "[$(date)] Descargando imagen worker..."
docker pull ${worker_image}

echo "[$(date)] Iniciando worker..."
docker run -d \
  --name sobel-worker \
  --restart unless-stopped \
  -e RABBITMQ_HOST=${rabbitmq_host} \
  -e RABBITMQ_PORT=${rabbitmq_port} \
  -e RABBITMQ_USER=${rabbitmq_user} \
  -e RABBITMQ_PASS=${rabbitmq_pass} \
  -e WORKER_ID=$${HOSTNAME} \
  ${worker_image}

echo "[$(date)] Worker iniciado correctamente"
