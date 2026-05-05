import numpy as np
import pytest
import os
from PIL import Image
from sobel_core import encode_chunk, decode_chunk, apply_sobel_to_chunk
from master import split_image, assemble_image

def test_encode_decode_chunk():
    """
    Prueba que la codificación a Base64 y posterior decodificación
    mantengan los datos de la imagen intactos.
    """
    img = np.random.randint(0, 256, (15, 20), dtype=np.uint8)
    b64_str = encode_chunk(img)
    
    assert isinstance(b64_str, str)
    
    decoded_img = decode_chunk(b64_str, width=20, height=15)
    assert np.array_equal(img, decoded_img)

def test_split_image(tmp_path):
    """
    Prueba la división de la imagen en chunks considerando el overlap 
    necesario para aplicar Sobel correctamente.
    """
    img_path = tmp_path / "dummy.jpg"
    # Crear imagen dummy de 40x20
    img = Image.fromarray(np.random.randint(0, 256, (40, 20), dtype=np.uint8))
    img.save(img_path)

    chunks = split_image(str(img_path), num_chunks=4)
    assert len(chunks) == 4
    
    for i, chunk in enumerate(chunks):
        assert chunk['chunk_id'] == i
        assert chunk['total_chunks'] == 4
        assert chunk['width'] == 20
        assert chunk['chunk_height'] == 10
        
        # El overlap_top debe ser 1 en todos los chunks excepto el primero
        assert chunk['overlap_top'] == (1 if i > 0 else 0)
        # El overlap_bottom debe ser 1 en todos los chunks excepto el último
        assert chunk['overlap_bottom'] == (1 if i < 3 else 0)
        
        expected_height = 10 + chunk['overlap_top'] + chunk['overlap_bottom']
        decoded_array = decode_chunk(chunk['pixels'], 20, expected_height)
        assert decoded_array.shape == (expected_height, 20)

def test_assemble_image(tmp_path):
    """
    Prueba el reensamblado de los chunks procesados.
    """
    output_path = tmp_path / "output.png"
    
    results = []
    # Simular chunks procesados
    for i in range(4):
        chunk_arr = np.ones((10, 20), dtype=np.uint8) * (i * 50)
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
    # Verificar valores por chunk
    assert res_array[5, 10] == 0
    assert res_array[15, 10] == 50
    assert res_array[25, 10] == 100
    assert res_array[35, 10] == 150
