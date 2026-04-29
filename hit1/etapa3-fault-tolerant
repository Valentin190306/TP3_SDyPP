import os
import time
import json
import socket
import pika
from logger import get_logger
from sobel_core import apply_sobel_to_chunk, encode_chunk, decode_chunk

RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'rabbitmq')
WORKER_ID = os.environ.get('WORKER_ID', socket.gethostname())

TASKS_QUEUE = 'sobel_tasks'
RESULTS_QUEUE = 'sobel_results'

logger = get_logger(f'worker_{WORKER_ID}')

def connect_rabbitmq() -> pika.BlockingConnection:
    # Mismo retry con exponential backoff
    max_retries = 10
    for i in range(max_retries):
        try:
            logger.info(f"Intentando conectar a RabbitMQ en {RABBITMQ_HOST} (intento {i+1}/{max_retries})...")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST, heartbeat=600)
            )
            logger.info("Conexión exitosa a RabbitMQ.")
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            logger.warning(f"Fallo al conectar: {e}")
            delay = 2 ** i
            logger.info(f"Reintentando en {delay} segundos...")
            time.sleep(delay)
    
    logger.error("No se pudo conectar a RabbitMQ después de múltiples intentos.")
    raise Exception("RabbitMQ connection failed")

def process_chunk(ch, method, properties, body):
    start_time = time.time()
    
    chunk_data = json.loads(body.decode('utf-8'))
    chunk_id = chunk_data['chunk_id']
    pixels_b64 = chunk_data['pixels']
    width = chunk_data['width']
    chunk_height = chunk_data['chunk_height']
    overlap_top = chunk_data['overlap_top']
    overlap_bottom = chunk_data['overlap_bottom']
    
    logger.info(f"[{WORKER_ID}] Iniciando procesamiento de chunk {chunk_id}")
    
    # Calcular altura total con overlap
    total_height = chunk_height + overlap_top + overlap_bottom
    
    # Aplicar Sobel (apply_sobel_to_chunk toma la imagen completa incluyendo el overlap)
    result_b64 = apply_sobel_to_chunk(pixels_b64, width, total_height)
    
    # Recortar el overlap del resultado
    result_array = decode_chunk(result_b64, width, total_height)
    
    row_start = 1 if overlap_top == 1 else 0
    row_end = total_height - (1 if overlap_bottom == 1 else 0)
    
    final_array = result_array[row_start:row_end, :]
    final_b64 = encode_chunk(final_array)
    
    # Preparar resultado
    result_data = {
        "chunk_id": chunk_id,
        "chunk_height": chunk_height,
        "width": width,
        "pixels": final_b64
    }
    
    # Publicar en resultados
    ch.basic_publish(
        exchange='',
        routing_key=RESULTS_QUEUE,
        body=json.dumps(result_data),
        properties=pika.BasicProperties(
            delivery_mode=2,
        )
    )
    
    # Confirmar mensaje procesado
    ch.basic_ack(delivery_tag=method.delivery_tag)
    
    end_time = time.time()
    duration = end_time - start_time
    logger.info(f"[{WORKER_ID}] Chunk {chunk_id} procesado y publicado en {duration:.3f} segundos.")

def main():
    logger.info(f"Iniciando Worker {WORKER_ID} conectando a {RABBITMQ_HOST}")
    
    connection = connect_rabbitmq()
    channel = connection.channel()
    
    channel.queue_declare(queue=TASKS_QUEUE, durable=True)
    channel.queue_declare(queue=RESULTS_QUEUE, durable=True)
    
    channel.basic_qos(prefetch_count=1)
    
    channel.basic_consume(queue=TASKS_QUEUE, on_message_callback=process_chunk)
    
    logger.info(f"[{WORKER_ID}] Esperando tareas en '{TASKS_QUEUE}'. Para salir presione CTRL+C")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Interrupción por teclado. Cerrando...")
        channel.stop_consuming()
    
    connection.close()

if __name__ == '__main__':
    main()
