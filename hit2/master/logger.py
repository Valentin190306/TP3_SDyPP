import logging
import os
import sys

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        log_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
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
            log_file = os.path.join(log_dir, f'{name}.log')
            fh = logging.FileHandler(log_file)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        except Exception as e:
            # En caso de no poder escribir a archivo (ej. local sin permisos o sin carpeta logs), loggeamos error en stdout
            print(f"Error al crear FileHandler: {e}")
            
    return logger
