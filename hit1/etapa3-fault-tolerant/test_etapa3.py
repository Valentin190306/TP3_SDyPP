import pytest
import numpy as np
import threading
import time
import os
from PIL import Image
from master import split_image, publish_chunks, assemble_image
from sobel_core import encode_chunk, decode_chunk

class MockChannel:
    """Mock básico para simular un canal de RabbitMQ y registrar publicaciones."""
    def __init__(self):
        self.published_messages = []

    def queue_declare(self, queue, durable):
        pass

    def queue_purge(self, queue):
        pass

    def basic_publish(self, exchange, routing_key, body, properties):
        self.published_messages.append((routing_key, body))


def test_publish_chunks_pending_tasks_tracking():
    """
    Prueba que la publicación de chunks registre correctamente los tiempos
    en el diccionario pending_tasks de manera thread-safe.
    """
    channel = MockChannel()
    chunks = [
        {'chunk_id': 0, 'data': 'foo'},
        {'chunk_id': 1, 'data': 'bar'}
    ]
    pending_tasks = {}
    lock = threading.Lock()

    publish_chunks(channel, chunks, pending_tasks, lock)

    # Verificamos que se hayan encolado los mensajes
    assert len(channel.published_messages) == 2
    
    # Verificamos que pending_tasks esté actualizado
    assert len(pending_tasks) == 2
    assert 0 in pending_tasks
    assert 1 in pending_tasks
    
    # El timestamp debe ser cercano al tiempo actual
    current_time = time.time()
    assert abs(pending_tasks[0] - current_time) < 2
    assert abs(pending_tasks[1] - current_time) < 2

def test_split_image_overlap(tmp_path):
    """
    Prueba que la división de la imagen incluya correctamente el overlap
    para el procesamiento en Etapa 3.
    """
    img_path = tmp_path / "dummy_e3.jpg"
    img = Image.fromarray(np.random.randint(0, 256, (40, 20), dtype=np.uint8))
    img.save(img_path)

    chunks = split_image(str(img_path), num_chunks=4)
    assert len(chunks) == 4
    
    for i, chunk in enumerate(chunks):
        assert chunk['chunk_id'] == i
        expected_top = 1 if i > 0 else 0
        expected_bottom = 1 if i < 3 else 0
        assert chunk['overlap_top'] == expected_top
        assert chunk['overlap_bottom'] == expected_bottom

def test_assemble_image_results(tmp_path):
    """
    Prueba el ensamblado final de los chunks de Etapa 3.
    """
    output_path = tmp_path / "output_e3.jpg"
    
    results = []
    for i in range(4):
        chunk_arr = np.ones((10, 20), dtype=np.uint8) * (i * 20)
        results.append({
            'chunk_id': i,
            'chunk_height': 10,
            'pixels': encode_chunk(chunk_arr)
        })
        
    assemble_image(results, original_width=20, original_height=40, output_path=str(output_path))
    
    assert os.path.exists(str(output_path))
    result_img = Image.open(str(output_path))
    assert result_img.size == (20, 40)
    
    res_array = np.array(result_img)
    assert res_array[5, 10] == 0
    assert res_array[15, 10] == 20
    assert res_array[25, 10] == 40
    assert res_array[35, 10] == 60
