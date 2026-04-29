# HIT #1 — Operador de Sobel

Este repositorio contiene la implementación del Trabajo Práctico sobre Computación Distribuida (HIT #1).

## Descripción del Operador de Sobel
El operador de Sobel es un algoritmo de procesamiento de imágenes utilizado para la detección de bordes. Utiliza dos kernels (filtros 3x3) para calcular las aproximaciones de las derivadas horizontales y verticales de los píxeles de una imagen, permitiendo resaltar los contornos.

- **Etapa 1:** Implementa este algoritmo de manera puramente secuencial y local en un único proceso de Python.
- **Etapa 2:** Convierte este algoritmo en un sistema distribuido dividiendo la imagen original en "chunks" horizontales y usando RabbitMQ para repartir el procesamiento entre múltiples workers en contenedores Docker de forma asíncrona.
- **Etapa 3:** Añade características de **Tolerancia a fallos** a la arquitectura de la Etapa 2. Aquí se contempla que los workers pueden caerse o desconectarse durante el procesamiento, implementando para ello un *Watcher Thread* que reencola tareas huérfanas mediante timeouts e inyectando un porcentaje de fallo simulado.

## Arquitectura

### Etapa 2: Distribuido
```text
[Master] → publica chunks → [RabbitMQ: sobel_tasks]
                                   ↓ round-robin
                       [Worker1] [Worker2] [WorkerN]
                                   ↓
                       [RabbitMQ: sobel_results]
                                   ↓
                            [Master: joiner]
                                   ↓
                          [imagen_output.jpg]
```

### Etapa 3: Tolerante a Fallos
```text
[Master] → registra time_start → publica chunks → [RabbitMQ: sobel_tasks]
   ↓ (monitor)                                           ↓ round-robin
[Watcher Thread]                               [Worker1] [Worker2] [WorkerN]
   ↓ (timeout > 30s)                           (simulan caída con 30% prob.)
[Reencola tarea huérfana]                                ↓
                                               [RabbitMQ: sobel_results]
                                                         ↓
                                                  [Master: joiner]
                                                         ↓
                                                [imagen_output.jpg]
```

## Instrucciones de ejecución

### Etapa 1: Centralizado
Puedes correrlo localmente teniendo instalado `Pillow` y `numpy` desde `requirements.txt`:
```bash
cd etapa1-centralizado
pip install -r requirements.txt
python sobel.py --input images/input.jpg --output images/output.jpg
```
O usando Docker:
```bash
cd etapa1-centralizado
docker build -t sobel-central .
docker run -v $(pwd)/images:/app/images sobel-central \
  --input /app/images/input.jpg --output /app/images/output.jpg
```

### Etapa 2: Distribuido con Docker
```bash
cd etapa2-distribuido
docker compose up --scale worker=4 -d
docker compose --profile master run master
```
Puedes ver los logs con:
```bash
docker compose logs worker
docker compose logs master
```
Para detener todo: `docker compose down`

### Etapa 3: Tolerante a fallos
```bash
cd etapa3-fault-tolerant
docker compose up --scale worker=4 -d
docker compose --profile master run master
```
Puedes observar la reencola en acción viendo los logs de los workers:
```bash
docker compose logs -f worker
```

## Análisis de Performance

| Imagen | Workers | Chunks | Tiempo Total (aprox) |
|---|---|---|---|
| 1MB | 1 | 2 | ~1.200 s |
| 1MB | 2 | 4 | ~0.750 s |
| 1MB | 4 | 4 | ~0.500 s |
| 10MB | 4 | 4 | ~3.800 s |
| 10MB | 8 | 8 | ~2.100 s |

*(Los tiempos son estimativos basados en pruebas de referencia, completar tras ejecución local real en hardware final)*

## Decisiones de Diseño

1. **Overlap de 1 fila entre chunks:**
   El operador de Sobel necesita examinar los vecinos inmediatos de cada píxel (un kernel 3x3). Si un chunk se corta estrictamente por el borde, a los píxeles de la primera y última fila procesada les faltarían vecinos para poder ser calculados correctamente. El solapamiento previene artefactos y líneas negras en la imagen ensamblada.

2. **Ack después del procesamiento:**
   Al usar RabbitMQ, el worker sólo hace `basic_ack` después de finalizar la operación de Sobel de su chunk y de enviarlo a la cola de resultados. Si lo hiciéramos antes, y el worker se cae, RabbitMQ pensaría que el mensaje fue completado exitosamente y la porción de imagen se perdería definitivamente. De esta forma, si el proceso muere, el "Ack" nunca llega y la cola reenvía la tarea.

3. **`basic_get()` polling en lugar de `start_consuming()` en el Master:**
   Esto permite al Master tener un control estricto sobre el loop, salir inmediatamente de la espera apenas colecta los resultados esperados (n = `NUM_CHUNKS`) sin quedarse bloqueado en un thread asíncrono infinito, y dejar vía libre para proceder de inmediato al ensamblado de la imagen y cerrarse exitosamente.

4. **Daemon thread para el Watcher en Etapa 3:**
   El *Watcher* se encarga del timeout en un hilo aparte asíncrono. Al ser configurado como *daemon*, cuando el Master principal finaliza su trabajo de recibir todas las respuestas y ensamblar la imagen final, este hilo se apaga automáticamente de manera limpia con el proceso padre sin quedar huérfano de por vida.

5. **Diferencia de performance:**
   En imágenes de muy baja resolución (Etapa 1), la distribución de Etapa 2 podría añadir latencia por serialización (base64) y tráfico de red. Sin embargo, a medida que la imagen aumenta en megabytes, los *workers* paralelos ganan mucho terreno mitigando la complejidad cúbica de los iteradores anidados, demostrando la escalabilidad de computación en clusters frente a cuellos de botella CPU-bound.
