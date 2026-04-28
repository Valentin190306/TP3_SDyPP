import pika
import os
import time
import json
import socket
import logger

logger = logger.get_logger("subscriber")

def connect():
    host = os.getenv('RABBITMQ_HOST', 'rabbitmq')
    max_retries = 10
    for i in range(max_retries):
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
            return connection
        except pika.exceptions.AMQPConnectionError:
            delay = 2 ** i
            logger.error(f"Error connecting to RabbitMQ. Retrying in {delay} seconds...")
            time.sleep(delay)
    raise Exception("Could not connect to RabbitMQ after max retries.")

def callback(ch, method, properties, body):
    node_id = socket.gethostname()
    event = json.loads(body)
    
    block_number = event.get("block_number")
    block_hash = event.get("hash")
    timestamp = event.get("timestamp")
    
    logger.info(f"Nuevo bloque recibido - Bloque {block_number} | Hash: {block_hash} | Timestamp: {timestamp}")
    ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    connection = connect()
    channel = connection.channel()

    channel.exchange_declare(exchange='blocks_exchange', exchange_type='fanout', durable=True)

    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue

    channel.queue_bind(exchange='blocks_exchange', queue=queue_name)

    channel.basic_consume(
        queue=queue_name,
        on_message_callback=callback,
        auto_ack=False
    )

    node_id = socket.gethostname()
    logger.info(f"Waiting for blocks on node {node_id}. To exit press CTRL+C")
    channel.start_consuming()

if __name__ == '__main__':
    main()
