import base64
import numpy as np

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

def encode_chunk(img_array: np.ndarray) -> str:
    """
    Recibe array 2D numpy uint8
    Retorna base64 de los bytes raw (array.tobytes())
    """
    return base64.b64encode(img_array.tobytes()).decode('utf-8')

def decode_chunk(b64_str: str, width: int, height: int) -> np.ndarray:
    """
    Inversa de encode_chunk
    Retorna array 2D uint8 de shape (height, width)
    """
    pixels_bytes = base64.b64decode(b64_str)
    return np.frombuffer(pixels_bytes, dtype=np.uint8).reshape((height, width))

def apply_sobel_to_chunk(pixels_b64: str, width: int, height: int) -> str:
    # Decodificar pixels_b64 desde base64 a bytes y reconstruir numpy array
    img_array = decode_chunk(pixels_b64, width, height)
    # Convertir a float32
    img_array_float = img_array.astype(np.float32)
    # Llamar implementar_sobel()
    result_array = implementar_sobel(img_array_float)
    # Codificar resultado a base64 y retornar como string
    return encode_chunk(result_array)
