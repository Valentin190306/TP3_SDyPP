# Patrón 4: Retry Exponential Backoff (RabbitMQ)

Este directorio contiene la implementación del patrón **Retry Exponential Backoff** utilizando RabbitMQ de forma nativa a través de **Time-To-Live (TTL)** y **Dead Letter Exchanges (DLX)**, sin necesidad de instalar plugins adicionales como `rabbitmq_delayed_message_exchange`.

## Flujo de Trabajo

1. El **Productor** (`producer.py`) envía 10 mensajes de prueba a `main_exchange` (ruteados a `main_queue`).
2. El **Consumidor** (`consumer.py`) lee de `main_queue`. Tiene un 50% de probabilidad de simular un fallo en el procesamiento.
3. Si el procesamiento es exitoso, se confirma el mensaje (`ack`).
4. Si falla:
   - Lee el encabezado `x-retry-count` (inicialmente 0).
   - Si los intentos son menores a 4, incrementa el contador y re-publica el mensaje en `retry_exchange` con una `routing_key` que determina la cola de espera (`1s`, `2s`, `4s`, `8s`).
   - El mensaje se queda en esa cola intermedia hasta que expira el TTL y luego RabbitMQ lo redirige automáticamente a `main_exchange` gracias a su DLX, volviendo a la cola principal.
5. Si falla 5 veces (supera los 4 reintentos), es enviado definitivamente al exchange `dlq_exchange` para quedar almacenado en `dlq_queue`.

---

## Ejecución Local (con Docker)

Puedes levantar un RabbitMQ en local y ejecutar los scripts directamente:

1. Iniciar RabbitMQ:
```bash
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```
2. Instalar dependencias en entorno virtual:
```bash
python3 -m venv venv
source venv/bin/activate  # En windows: venv\Scripts\activate
pip install -r requirements.txt
```
3. Iniciar el consumidor:
```bash
python3 consumer.py
```
4. En otra terminal, iniciar el productor:
```bash
python3 producer.py
```

Verás en los logs del consumidor los intentos de procesamiento y los reintentos espaciados en el tiempo.

5. Una vez finalizado el proceso, detén el contenedor de RabbitMQ:
```bash
docker stop rabbitmq
docker rm rabbitmq
```

---

## Despliegue en Kubernetes

Los manifiestos en la carpeta `k8s/` te permitirán desplegar todo en Minikube o cualquier cluster local.

1. Construir las imágenes Docker apuntando al daemon de Minikube (o Docker Desktop en Kubernetes mode):
```bash
# Si usas minikube: eval $(minikube docker-env)
docker build -t producer-ex4 -f Dockerfile.producer .
docker build -t consumer-ex4 -f Dockerfile.consumer .
```

2. Importar imágenes a K3s
```bash
docker save producer-ex4 | sudo k3s ctr images import -
docker save consumer-ex4 | sudo k3s ctr images import -
```

3. Aplicar manifiestos:
```bash
kubectl apply -f k8s/rabbitmq.yaml

# Esperar a que rabbitmq esté running
kubectl get pods -w

# Desplegar producer y consumer
kubectl apply -f k8s/deployment-producer.yaml
kubectl apply -f k8s/deployment-consumer.yaml
```

4. Revisar logs:
```bash
# Ver logs del productor (para ver los IDs generados)
kubectl logs -f deployment/producer

# Ver logs del consumidor (para ver los reintentos)
kubectl logs -f deployment/consumer
```

### Verificar la DLQ
Si entras a la UI de administración de RabbitMQ (port 15672, credenciales por defecto `guest`/`guest`) o verificas las colas usando la CLI dentro del pod de rabbitmq, podrás notar que luego de los 5 intentos, los mensajes que hayan fallado constantemente terminan en la cola `dlq_queue`.
