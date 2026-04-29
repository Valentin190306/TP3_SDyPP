import logging
import os
import sys

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        os.makedirs('/app/logs', exist_ok=True)
        
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
        
        # StreamHandler
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(formatter)
        logger.addHandler(sh)
        
        # FileHandler
        try:
            fh = logging.FileHandler(f'/app/logs/{name}.log')
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        except Exception as e:
            # En caso de no poder escribir a archivo (ej. local sin permisos o sin carpeta logs), loggeamos error en stdout
            print(f"Error al crear FileHandler: {e}")
            
    return logger
