import pika
import os
import time
import random
from logger import get_logger

logger = get_logger("consumer")

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")

MAIN_EXCHANGE = "main_exchange"
MAIN_QUEUE = "main_queue"

RETRY_EXCHANGE = "retry_exchange"
DLQ_EXCHANGE = "dlq_exchange"
DLQ_QUEUE = "dlq_queue"

# Configuración de reintentos (Exponential Backoff en segundos)
RETRY_DELAYS = [1, 2, 4, 8]
MAX_RETRIES = len(RETRY_DELAYS)

def setup_queues(channel):
    # 1. Main Queue & Exchange
    channel.exchange_declare(exchange=MAIN_EXCHANGE, exchange_type="direct", durable=True)
    channel.queue_declare(queue=MAIN_QUEUE, durable=True)
    channel.queue_bind(exchange=MAIN_EXCHANGE, queue=MAIN_QUEUE, routing_key="task")

    # 2. DLQ
    channel.exchange_declare(exchange=DLQ_EXCHANGE, exchange_type="direct", durable=True)
    channel.queue_declare(queue=DLQ_QUEUE, durable=True)
    channel.queue_bind(exchange=DLQ_EXCHANGE, queue=DLQ_QUEUE, routing_key="dlq")

    # 3. Retry Exchange and Wait Queues
    channel.exchange_declare(exchange=RETRY_EXCHANGE, exchange_type="direct", durable=True)
    
    for delay in RETRY_DELAYS:
        queue_name = f"retry_wait_{delay}s"
        routing_key = f"delay.{delay}s"
        
        # Declarar cola con TTL. Al expirar, vuelve a main_exchange
        channel.queue_declare(
            queue=queue_name,
            durable=True,
            arguments={
                "x-message-ttl": delay * 1000,              # TTL en ms
                "x-dead-letter-exchange": MAIN_EXCHANGE,    # A dónde va al expirar
                "x-dead-letter-routing-key": "task"         # Routing key para main_queue
            }
        )
        channel.queue_bind(exchange=RETRY_EXCHANGE, queue=queue_name, routing_key=routing_key)

def callback(ch, method, properties, body):
    msg_id = properties.message_id or "N/A"
    headers = properties.headers or {}
    retry_count = headers.get("x-retry-count", 0)

    logger.info(f"Recibido mensaje {msg_id} - Intento actual: {retry_count}")

    # Simular procesamiento
    time.sleep(0.5)

    # 50% de probabilidad de fallo
    success = random.choice([True, False])

    if success:
        logger.info(f"✅ Procesamiento exitoso para {msg_id}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    else:
        if retry_count < MAX_RETRIES:
            delay_s = RETRY_DELAYS[retry_count]
            next_retry = retry_count + 1
            
            logger.warning(f"❌ Fallo al procesar {msg_id}. Reintentando (Intento {next_retry}/{MAX_RETRIES}). Esperando {delay_s}s...")
            
            # Actualizar cabeceras
            headers["x-retry-count"] = next_retry
            new_properties = pika.BasicProperties(
                message_id=properties.message_id,
                delivery_mode=2,
                headers=headers
            )
            
            # Publicar en exchange de reintentos
            ch.basic_publish(
                exchange=RETRY_EXCHANGE,
                routing_key=f"delay.{delay_s}s",
                body=body,
                properties=new_properties
            )
            
            # Ack al original
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            logger.error(f"💀 Límite de reintentos alcanzado para {msg_id}. Enviando a DLQ.")
            
            ch.basic_publish(
                exchange=DLQ_EXCHANGE,
                routing_key="dlq",
                body=body,
                properties=properties
            )
            
            ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    logger.info(f"Conectando a RabbitMQ en {RABBITMQ_HOST}...")
    
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
    
    setup_queues(channel)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=MAIN_QUEUE, on_message_callback=callback)

    logger.info("Consumidor listo. Esperando mensajes...")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Deteniendo consumidor...")
        channel.stop_consuming()
    finally:
        connection.close()

if __name__ == "__main__":
    main()
