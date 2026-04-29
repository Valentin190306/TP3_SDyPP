import os
import time
import json
import pika
import numpy as np
from PIL import Image
from logger import get_logger
from sobel_core import encode_chunk, decode_chunk

# Constantes leídas desde variables de entorno
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'rabbitmq')
NUM_CHUNKS = int(os.environ.get('NUM_CHUNKS', '4'))
INPUT_IMAGE = os.environ.get('INPUT_IMAGE', '/app/images/input.jpg')
OUTPUT_IMAGE = os.environ.get('OUTPUT_IMAGE', '/app/images/output.jpg')

# Nombres de colas
TASKS_QUEUE = 'sobel_tasks'
RESULTS_QUEUE = 'sobel_results'

logger = get_logger('master')

def connect_rabbitmq() -> pika.BlockingConnection:
    # Retry con exponential backoff (hasta 10 intentos, 2^i delay)
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

def split_image(img_path: str, num_chunks: int) -> list[dict]:
    # Abrir imagen con PIL, convertir a escala de grises ('L')
    img = Image.open(img_path).convert('L')
    img_array = np.array(img, dtype=np.uint8)
    
    total_height, img_width = img_array.shape
    chunk_height = total_height // num_chunks
    
    chunks = []
    
    for i in range(num_chunks):
        row_start = i * chunk_height
        # El último chunk absorbe los píxeles restantes
        row_end = (i + 1) * chunk_height if i < num_chunks - 1 else total_height
        
        chunk_height_sin_overlap = row_end - row_start
        
        # Agregar 1 fila de overlap arriba
        overlap_top = 1 if i > 0 else 0
        overlap_top_row = row_start - overlap_top
        
        # Agregar 1 fila de overlap abajo
        overlap_bottom = 1 if i < num_chunks - 1 else 0
        overlap_bottom_row = row_end + overlap_bottom
        
        # Extraer subarray con el overlap incluido
        subarray = img_array[overlap_top_row:overlap_bottom_row, :]
        
        chunk_dict = {
            "chunk_id": i,
            "total_chunks": num_chunks,
            "width": img_width,
            "chunk_height": chunk_height_sin_overlap,
            "overlap_top": overlap_top,
            "overlap_bottom": overlap_bottom,
            "pixels": encode_chunk(subarray)
        }
        chunks.append(chunk_dict)
        
    return chunks

def publish_chunks(channel, chunks: list[dict]):
    # Declarar colas
    channel.queue_declare(queue=TASKS_QUEUE, durable=True)
    channel.queue_declare(queue=RESULTS_QUEUE, durable=True)
    
    # Purgar results
    channel.queue_purge(queue=RESULTS_QUEUE)
    
    for chunk in chunks:
        body_json = json.dumps(chunk)
        channel.basic_publish(
            exchange='',
            routing_key=TASKS_QUEUE,
            body=body_json,
            properties=pika.BasicProperties(
                delivery_mode=2,  # hacer el mensaje persistente
            )
        )
        logger.info(f"Chunk {chunk['chunk_id']} publicado en {TASKS_QUEUE}.")

def collect_results(channel, num_chunks: int) -> list[dict]:
    resultados = []
    
    logger.info(f"Esperando {num_chunks} resultados en {RESULTS_QUEUE}...")
    
    while len(resultados) < num_chunks:
        method_frame, header_frame, body = channel.basic_get(queue=RESULTS_QUEUE, auto_ack=False)
        if method_frame:
            result_dict = json.loads(body.decode('utf-8'))
            chunk_id = result_dict.get('chunk_id')
            logger.info(f"Resultado recibido para chunk {chunk_id}.")
            
            resultados.append(result_dict)
            channel.basic_ack(delivery_tag=method_frame.delivery_tag)
        else:
            # Usar polling con sleep
            time.sleep(0.1)
            
    return sorted(resultados, key=lambda x: x['chunk_id'])

def assemble_image(results: list[dict], original_width: int, original_height: int, output_path: str):
    # Ordenar results por chunk_id
    results_sorted = sorted(results, key=lambda x: x['chunk_id'])
    
    # Crear array numpy vacío de shape (original_height, original_width) uint8
    final_array = np.zeros((original_height, original_width), dtype=np.uint8)
    
    current_row = 0
    for res in results_sorted:
        chunk_height = res['chunk_height']
        pixels_b64 = res['pixels']
        
        chunk_array = decode_chunk(pixels_b64, original_width, chunk_height)
        
        row_end = current_row + chunk_height
        final_array[current_row:row_end, :] = chunk_array
        current_row = row_end
        
    # Guardar con PIL.Image.fromarray()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    result_img = Image.fromarray(final_array)
    result_img.save(output_path)
    logger.info(f"Imagen final ensamblada y guardada en: {output_path}")

def main():
    logger.info(f"Iniciando Master. Parámetros: HOST={RABBITMQ_HOST}, CHUNKS={NUM_CHUNKS}")
    
    start_time = time.time()
    
    connection = connect_rabbitmq()
    channel = connection.channel()
    
    # Abrir imagen para obtener dimensiones originales
    try:
        img = Image.open(INPUT_IMAGE)
    except Exception as e:
        logger.error(f"Error al abrir la imagen {INPUT_IMAGE}: {e}")
        connection.close()
        return
        
    original_width, original_height = img.size
    logger.info(f"Imagen original: ancho={original_width}, alto={original_height}")
    
    chunks = split_image(INPUT_IMAGE, NUM_CHUNKS)
    logger.info(f"Imagen dividida en {NUM_CHUNKS} chunks.")
    
    publish_chunks(channel, chunks)
    logger.info("Todos los chunks fueron publicados. Esperando resultados...")
    
    results = collect_results(channel, NUM_CHUNKS)
    
    assemble_image(results, original_width, original_height, OUTPUT_IMAGE)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Tamaño de imagen en MB
    size_mb = (original_width * original_height) / (1024 * 1024)
    
    logger.info("=== MÉTRICAS ===")
    logger.info(f"Tiempo total de procesamiento distribuido: {total_time:.3f} segundos")
    logger.info(f"Número de chunks: {NUM_CHUNKS}")
    logger.info(f"Tamaño de imagen: {size_mb:.2f} MB")
    
    connection.close()

if __name__ == '__main__':
    main()
