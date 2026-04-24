import os
import socket
import time
import pika
from logger import get_logger

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "rabbitmq")
QUEUE_NAME = "task_queue"
MAX_RETRIES = 10
CONSUMER_ID = socket.gethostname()

logger = get_logger('consumer')


def connect_with_retry() -> pika.BlockingConnection:
    for attempt in range(MAX_RETRIES):
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST)
            )
            logger.info(f"[{CONSUMER_ID}] Conectado a RabbitMQ en '{RABBITMQ_HOST}'")
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            delay = 2 ** attempt
            logger.warning(
                f"[{CONSUMER_ID}] Intento {attempt + 1}/{MAX_RETRIES} fallido. "
                f"Reintentando en {delay}s... ({e})"
            )
            time.sleep(delay)
    logger.error(f"[{CONSUMER_ID}] No se pudo conectar a RabbitMQ tras {MAX_RETRIES} intentos.")
    raise RuntimeError(f"[{CONSUMER_ID}] No se pudo conectar a RabbitMQ tras {MAX_RETRIES} intentos.")


def callback(ch, method, properties, body):
    message = body.decode()
    logger.info(f"[{CONSUMER_ID}] Recibido: {message}")
    ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    connection = connect_with_retry()
    channel = connection.channel()

    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    logger.info(f"[{CONSUMER_ID}] Esperando mensajes en '{QUEUE_NAME}'. Presiona CTRL+C para salir.")
    channel.start_consuming()


if __name__ == "__main__":
    main()
