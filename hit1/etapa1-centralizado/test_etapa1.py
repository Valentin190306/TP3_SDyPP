import numpy as np
import pytest
from sobel import implementar_sobel

def test_implementar_sobel_uniform_image():
    """
    Una imagen con todos los píxeles iguales no debería tener bordes, 
    por lo que el operador Sobel debería devolver 0 en los píxeles calculados.
    """
    img = np.ones((10, 10), dtype=np.float32) * 128
    res = implementar_sobel(img)
    
    # Verificamos los píxeles internos (Sobel no se calcula en el borde de 1px)
    assert np.all(res[1:-1, 1:-1] == 0)

def test_implementar_sobel_vertical_edge():
    """
    Prueba que detecte correctamente un borde vertical.
    """
    img = np.zeros((10, 10), dtype=np.float32)
    # Mitad izquierda blanca, mitad derecha negra
    img[:, :5] = 255
    res = implementar_sobel(img)
    
    # El borde está entre la columna 4 y 5
    # En la columna 4 (índice 4), Sobel detectará un borde fuerte
    assert np.all(res[1:-1, 4] == 255) # Clip a 255
    # En las columnas alejadas del borde debería ser 0
    assert np.all(res[1:-1, 2] == 0)
    assert np.all(res[1:-1, 7] == 0)

def test_implementar_sobel_horizontal_edge():
    """
    Prueba que detecte correctamente un borde horizontal.
    """
    img = np.zeros((10, 10), dtype=np.float32)
    # Mitad superior blanca, mitad inferior negra
    img[:5, :] = 255
    res = implementar_sobel(img)
    
    # El borde está entre la fila 4 y 5
    assert np.all(res[4, 1:-1] == 255)
    # En las filas alejadas del borde debería ser 0
    assert np.all(res[2, 1:-1] == 0)
    assert np.all(res[7, 1:-1] == 0)
