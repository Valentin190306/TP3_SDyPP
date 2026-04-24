import pika
import os
import time
import json
import uuid
from datetime import datetime, timezone

def connect():
    host = os.getenv('RABBITMQ_HOST', 'rabbitmq')
    max_retries = 10
    for i in range(max_retries):
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
            return connection
        except pika.exceptions.AMQPConnectionError:
            delay = 2 ** i
            print(f"[Publisher] Error connecting to RabbitMQ. Retrying in {delay} seconds...", flush=True)
            time.sleep(delay)
    raise Exception("[Publisher] Could not connect to RabbitMQ after max retries.")

def main():
    connection = connect()
    channel = connection.channel()

    channel.exchange_declare(exchange='blocks_exchange', exchange_type='fanout', durable=True)

    for n in range(1, 6):
        event = {
            "event": "new_block",
            "block_number": n,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hash": str(uuid.uuid4())
        }
        event_json = json.dumps(event)
        
        channel.basic_publish(
            exchange='blocks_exchange',
            routing_key='',
            body=event_json
        )
        print(f"[Publisher] Bloque {n} publicado: {event_json}", flush=True)
        time.sleep(1)

    connection.close()

if __name__ == '__main__':
    main()
