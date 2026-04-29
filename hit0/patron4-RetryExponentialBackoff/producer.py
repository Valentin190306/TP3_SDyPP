import pika
import os
import time
import uuid
from logger import get_logger

logger = get_logger("producer")

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
MAIN_EXCHANGE = "main_exchange"
MAIN_QUEUE = "main_queue"

def main():
    logger.info(f"Conectando a RabbitMQ en {RABBITMQ_HOST}...")
    
    # Wait for RabbitMQ to be ready
    connection = None
    for _ in range(15):
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            break
        except pika.exceptions.AMQPConnectionError:
            logger.info("Esperando a que RabbitMQ inicie...")
            time.sleep(2)
            
    if not connection:
        logger.error("No se pudo conectar a RabbitMQ.")
        return

    channel = connection.channel()

    # Declarar Exchange y Cola Principal
    channel.exchange_declare(exchange=MAIN_EXCHANGE, exchange_type="direct", durable=True)
    channel.queue_declare(queue=MAIN_QUEUE, durable=True)
    channel.queue_bind(exchange=MAIN_EXCHANGE, queue=MAIN_QUEUE, routing_key="task")

    logger.info("Productor listo. Enviando mensajes...")
    for i in range(1, 11):
        message_id = str(uuid.uuid4())
        body = f"Mensaje de prueba #{i}"
        
        properties = pika.BasicProperties(
            message_id=message_id,
            delivery_mode=2, # Persistente
            headers={"x-retry-count": 0}
        )

        channel.basic_publish(
            exchange=MAIN_EXCHANGE,
            routing_key="task",
            body=body,
            properties=properties
        )
        logger.info(f"Publicado: {body} (ID: {message_id})")
        time.sleep(1)

    connection.close()
    logger.info("Productor finalizado.")

if __name__ == "__main__":
    main()
