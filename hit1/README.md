# HIT #1: Operador de Sobel (Centralizado, Distribuido y Fault Tolerant)

Este repositorio contiene la implementación del Trabajo Práctico sobre Computación Distribuida, específicamente el HIT #1 que consiste en el operador de Sobel en tres etapas:

## Estructura del Proyecto

- `etapa1-centralizado/`: Implementación standalone del operador de Sobel sin paralelismo.
- `etapa2-distribuido/`: Implementación distribuida usando Docker, Docker Compose y RabbitMQ con arquitectura Master/Worker.
- `etapa3-fault-tolerant/`: Implementación tolerante a fallos (en progreso).

## Etapa 1: Centralizado
Para ejecutar la versión centralizada:

```bash
cd etapa1-centralizado
pip install -r requirements.txt
python sobel.py --input images/input.jpg --output images/output.jpg
```

También disponible mediante Docker:
```bash
cd etapa1-centralizado
docker build -t sobel-central .
docker run -v $(pwd)/images:/app/images sobel-central \
  --input /app/images/input.jpg --output /app/images/output.jpg
```

## Etapa 2: Distribuido
Para ejecutar la versión distribuida con RabbitMQ y Workers:

```bash
cd etapa2-distribuido
docker-compose up --build
```
El master dividirá la imagen en partes, las enviará a RabbitMQ y los workers las procesarán. El resultado final se ensamblará en la carpeta `images/`.

## Tecnologías Utilizadas
- Python 3.11
- Pillow y NumPy (Procesamiento de imagen)
- RabbitMQ / pika (Mensajería)
- Docker & Docker Compose (Contenedores)
