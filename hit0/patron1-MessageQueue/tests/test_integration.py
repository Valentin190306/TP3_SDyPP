import sys
import os
import pytest
import pika

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import producer

RABBIT_HOST = os.getenv('RABBITMQ_HOST', 'localhost')


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def rabbitmq_available() -> bool:
    try:
        conn = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBIT_HOST, connection_attempts=1, retry_delay=0)
        )
        conn.close()
        return True
    except Exception:
        return False


requires_rabbit = pytest.mark.skipif(
    not rabbitmq_available(),
    reason="RabbitMQ no disponible",
)


# ---------------------------------------------------------------------------
# Tests de integración
# ---------------------------------------------------------------------------

@requires_rabbit
def test_producer_publica_10_mensajes_en_cola():
    conn = pika.BlockingConnection(pika.ConnectionParameters(host=RABBIT_HOST))
    channel = conn.channel()
    channel.queue_declare(queue='task_queue', durable=True)
    channel.queue_purge('task_queue')

    # Publisher confirms: basic_publish bloquea hasta que el broker confirma
    # cada mensaje. Sin esto hay race condition al leer message_count.
    channel.confirm_delivery()

    producer.send_messages(channel)

    result = channel.queue_declare(queue='task_queue', durable=True, passive=True)
    message_count = result.method.message_count
    conn.close()

    assert message_count == 10



@requires_rabbit
@pytest.mark.timeout(10)
def test_consumer_procesa_mensajes_correctamente():
    conn = pika.BlockingConnection(pika.ConnectionParameters(host=RABBIT_HOST))
    channel = conn.channel()
    channel.queue_declare(queue='task_queue', durable=True)
    channel.queue_purge('task_queue')

    for i in range(1, 4):
        channel.basic_publish(
            exchange='',
            routing_key='task_queue',
            body=f'Tarea {i}',
            properties=pika.BasicProperties(delivery_mode=2),
        )

    recibidos = []

    def callback(ch, method, properties, body):
        recibidos.append(body.decode())
        ch.basic_ack(delivery_tag=method.delivery_tag)
        if len(recibidos) == 3:
            ch.stop_consuming()

    channel.basic_consume(queue='task_queue', on_message_callback=callback)
    channel.start_consuming()
    conn.close()

    assert recibidos == ["Tarea 1", "Tarea 2", "Tarea 3"]


@requires_rabbit
def test_cola_es_durable():
    conn = pika.BlockingConnection(pika.ConnectionParameters(host=RABBIT_HOST))
    channel = conn.channel()
    try:
        channel.queue_declare(queue='task_queue', passive=True)
    except pika.exceptions.ChannelClosedByBroker:
        pytest.fail("La cola no existe o no es durable")
    finally:
        conn.close()
