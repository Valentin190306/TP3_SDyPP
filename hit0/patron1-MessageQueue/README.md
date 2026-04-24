# Patrón 1 - Message Queue (Punto a Punto)

## Descripción

El patrón **Message Queue punto a punto** desacopla productores y consumidores mediante una cola persistente. El producer publica tareas en la cola `task_queue` y uno o más consumers las procesan de forma competitiva: cada mensaje es entregado a **exactamente un** consumer. Con `prefetch_count=1` y múltiples consumers activos, RabbitMQ distribuye los mensajes en **round-robin justo**, evitando que un consumer lento acumule trabajo.

---

## Cómo ejecutar

### 0. Dirigirse al directorio del patrón

```bash y powershell
cd hit0/patron1-MessageQueue
```

### 1. Levantar RabbitMQ y consumers (escalar a '<NUM_INSTANCES>' instancias)

```bash y powershell
docker compose up --scale consumer='<NUM_INSTANCES>' -d
```

### 2. Verificar que RabbitMQ esté healthy

```bash y powershell
docker compose ps
```

Esperar hasta que el campo `STATUS` de `rabbitmq` muestre `healthy`.

### 3. Correr el producer

```bash y powershell
docker compose run producer
```

### 4. Ver los logs de los consumers

```bash y powershell
docker compose logs consumer
```

### 5. Bajar todo

```bash y powershell
docker compose down
```

---

## Pruebas y Logging

### Ejecutar pruebas unitarias

> No requieren RabbitMQ corriendo.

```bash y powershell
pip install -r requirements-dev.txt
pytest tests/test_producer.py -v
```

### Ejecutar pruebas de integración

> Requieren RabbitMQ corriendo. Se saltan automáticamente si no hay broker disponible.

```bash y powershell
docker compose up rabbitmq -d
pytest tests/test_integration.py -v
```

### Ejecutar todas las pruebas

```bash y powershell
pytest tests/ -v
```

### Logs

Los logs se generan en `./logs/` en el host (montado como volumen Docker).

| Archivo        | Contenido                                                   |
| -------------- | ----------------------------------------------------------- |
| `producer.log` | Actividad del producer (mensajes enviados, reintentos)      |
| `consumer.log` | Actividad de cada consumer (mensajes recibidos, reintentos) |

Formato de cada línea:

```
timestamp | nombre | nivel | mensaje
```

### Archivos ignorados

El directorio `./logs/` y todos los archivos `*.log` están en `.gitignore` y no se commitean al repositorio.

---

## Comportamiento observado

### Con 1 consumer

Todos los mensajes (`Tarea 1` a `Tarea 10`) son procesados por el único consumer disponible. El output muestra un solo `CONSUMER_ID` repetido diez veces.

### Con 2 consumers (round-robin)

Los mensajes se alternan entre ambos consumers:

```
consumer-1  | [abc123] Recibido: Tarea 1
consumer-2  | [def456] Recibido: Tarea 2
consumer-1  | [abc123] Recibido: Tarea 3
consumer-2  | [def456] Recibido: Tarea 4
...
```

### Con 4 consumers (round-robin)

Los mensajes se alternan entre ambos consumers:

```
consumer-1 | [abc123] Recibido: Tarea 1
consumer-2 | [def456] Recibido: Tarea 2
consumer-3 | [abc123] Recibido: Tarea 3
consumer-4 | [def456] Recibido: Tarea 4
...
```

### Por qué `prefetch_count=1` importa

Sin `prefetch_count=1`, RabbitMQ pre-despacha múltiples mensajes a cada consumer de forma especulativa. Si un consumer es más rápido, puede terminar acaparando la mayoría de los mensajes antes de que el otro esté listo. Con `prefetch_count=1` cada consumer solo tiene **un mensaje en vuelo** a la vez: cuando termina y hace `ack`, recién entonces recibe el siguiente. Esto garantiza un reparto equitativo (**fair dispatch**).
