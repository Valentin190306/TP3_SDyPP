import os
import time
import pika
from logger import get_logger

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "rabbitmq")
QUEUE_NAME = "task_queue"
MAX_RETRIES = 10

logger = get_logger('producer')


def connect() -> pika.BlockingConnection:
    for attempt in range(MAX_RETRIES):
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST)
            )
            logger.info(f"Conectado a RabbitMQ en '{RABBITMQ_HOST}'")
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            delay = 2 ** attempt
            logger.warning(
                f"Intento {attempt + 1}/{MAX_RETRIES} fallido. "
                f"Reintentando en {delay}s... ({e})"
            )
            time.sleep(delay)
    logger.error(f"No se pudo conectar a RabbitMQ tras {MAX_RETRIES} intentos.")
    raise RuntimeError(f"No se pudo conectar a RabbitMQ tras {MAX_RETRIES} intentos.")


def send_messages(channel) -> None:
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
        logger.info(f"Enviado: {message}")


if __name__ == "__main__":
    connection = connect()
    channel = connection.channel()
    send_messages(channel)
    connection.close()
    logger.info("Todos los mensajes enviados. Conexión cerrada.")
