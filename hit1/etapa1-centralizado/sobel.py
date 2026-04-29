import argparse
import time
import os
import logging
import numpy as np
from PIL import Image

def implementar_sobel(img_array: np.ndarray) -> np.ndarray:
    """
    Aplica el operador Sobel a una imagen.
    Recibe un array numpy de la imagen en escala de grises, dtype float32.
    """
    # Definir kernel Gx
    kernel_Gx = np.array([
        [-1, 0, 1],
        [-2, 0, 2],
        [-1, 0, 1]
    ], dtype=np.float32)
    
    # Definir kernel Gy
    kernel_Gy = np.array([
        [-1, -2, -1],
        [ 0,  0,  0],
        [ 1,  2,  1]
    ], dtype=np.float32)
    
    height, width = img_array.shape
    result = np.zeros_like(img_array)
    
    # Aplicar convolución 2D manualmente con doble loop sobre píxeles
    for i in range(1, height - 1):
        for j in range(1, width - 1):
            Gx_val = 0.0
            Gy_val = 0.0
            
            for di in [-1, 0, 1]:
                for dj in [-1, 0, 1]:
                    pixel_val = img_array[i+di, j+dj]
                    Gx_val += pixel_val * kernel_Gx[di+1, dj+1]
                    Gy_val += pixel_val * kernel_Gy[di+1, dj+1]
                    
            magnitud = np.sqrt(Gx_val**2 + Gy_val**2)
            result[i, j] = magnitud
            
    # Clip al rango [0, 255] y retornar como uint8
    return np.clip(result, 0, 255).astype(np.uint8)

def main():
    # Configurar logging básico a stdout
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | sobel-central | %(levelname)s | %(message)s'
    )
    
    parser = argparse.ArgumentParser(description="Operador de Sobel Centralizado")
    parser.add_argument('--input', type=str, default='images/input.jpg', help='Ruta a la imagen de entrada')
    parser.add_argument('--output', type=str, default='images/output.jpg', help='Ruta a la imagen de salida')
    args = parser.parse_args()
    
    # Registrar tiempo de inicio
    start_time = time.time()
    
    logging.info(f"Iniciando procesamiento de la imagen: {args.input}")
    
    try:
        # Abrir imagen con PIL.Image.open(), convertir a escala de grises ('L')
        img = Image.open(args.input).convert('L')
    except Exception as e:
        logging.error(f"Error al abrir la imagen {args.input}: {e}")
        return

    # Convertir a numpy array float32
    img_array = np.array(img, dtype=np.float32)
    
    # Loggear dimensiones: ancho, alto, tamaño en MB
    height, width = img_array.shape
    size_mb = img_array.nbytes / (1024 * 1024)
    logging.info(f"Dimensiones de la imagen: ancho={width}, alto={height}")
    logging.info(f"Tamaño en memoria: {size_mb:.2f} MB")
    
    # Llamar implementar_sobel()
    result_array = implementar_sobel(img_array)
    
    # Registrar tiempo de fin, calcular duración
    end_time = time.time()
    duration = end_time - start_time
    
    # Loggear tiempo de procesamiento en segundos con 3 decimales
    logging.info(f"Tiempo de procesamiento: {duration:.3f} segundos")
    
    # Guardar imagen resultado con PIL.Image.fromarray()
    result_img = Image.fromarray(result_array)
    
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    try:
        result_img.save(args.output)
        # Loggear ruta del archivo de salida
        logging.info(f"Imagen resultado guardada en: {args.output}")
    except Exception as e:
        logging.error(f"Error al guardar la imagen de salida {args.output}: {e}")

if __name__ == '__main__':
    main()
