import os
import time
import pika

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "rabbitmq")
QUEUE_NAME = "task_queue"
MAX_RETRIES = 10


def connect_with_retry():
    for attempt in range(MAX_RETRIES):
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST)
            )
            print(f"[Producer] Conectado a RabbitMQ en '{RABBITMQ_HOST}'")
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            delay = 2 ** attempt
            print(f"[Producer] Intento {attempt + 1}/{MAX_RETRIES} fallido. Reintentando en {delay}s... ({e})")
            time.sleep(delay)
    raise RuntimeError(f"[Producer] No se pudo conectar a RabbitMQ tras {MAX_RETRIES} intentos.")


def main():
    connection = connect_with_retry()
    channel = connection.channel()

    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    for i in range(1, 11):
        message = f"Tarea {i}"
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=message,
            properties=pika.BasicProperties(
                delivery_mode=2,
            ),
        )
        print(f"[Producer] Enviado: {message}")

    connection.close()
    print("[Producer] Todos los mensajes enviados. Conexión cerrada.")


if __name__ == "__main__":
    main()
