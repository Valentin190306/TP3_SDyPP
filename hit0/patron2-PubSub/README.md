# Patrón 2 - Pub/Sub Fan-out

## Descripción breve del patrón y diferencia con el patrón punto a punto

El patrón Publisher/Subscriber (Pub/Sub) usando un exchange de tipo Fan-out permite emitir mensajes a múltiples consumidores simultáneamente (broadcast). 

A diferencia del patrón punto a punto (Message Queue) donde cada mensaje se encola y es consumido por un único worker de forma competitiva, en el patrón Fan-out cada mensaje se replica y envía a todas las colas conectadas al exchange. Esto significa que cada consumidor (subscriber) obtiene una copia idéntica del mensaje, permitiendo reaccionar al mismo evento de forma independiente.

## Diagrama de arquitectura

```text
                                        +----------------+
                                   +--->| Nodo1 (Cola A) |
                                   |    +----------------+
+-----------+    +---------------+ |    +----------------+
| Publisher |--->| blocks_exchange |--->| Nodo2 (Cola B) |
+-----------+    +---------------+ |    +----------------+
                 (Exchange fanout) |    +----------------+
                                   +--->| Nodo3 (Cola C) |
                                        +----------------+
```

## Cómo ejecutar

1. **Levantar RabbitMQ y subscribers**: 
```bash
docker compose up --scale subscriber=3 -d
```

2. **Esperar healthcheck**: 
```bash
docker compose ps
```
(Verificar que rabbitmq esté `healthy`)

3. **Correr publisher**: 
```bash
docker compose run publisher
```

4. **Ver logs**: 
```bash
docker compose logs subscriber
```

5. **Bajar todo**: 
```bash
docker compose down
```

## Comportamiento observado

- **Con 3 subscribers:** Los 3 nodos reciben TODOS los mensajes. El sistema no reparte los mensajes, sino que los copia hacia cada cola conectada.
- **Diferencia fundamental con el Ejemplo 1:** En Message Queue cada mensaje va a UN consumer (distribución equitativa); en Fan-out cada mensaje va a TODOS los suscriptores activos, comportándose como un broadcast o notificación general.
- **¿Qué pasa si un subscriber se conecta después de que el publisher ya publicó?** No recibe los mensajes anteriores. Debido a que utiliza una cola exclusiva y temporal, solo recibe los eventos que llegan al exchange mientras su cola está unida y activa.

## Decisiones de diseño

- **Exchange fanout con durable=True:** El exchange sobrevive a reinicios del broker. Las colas creadas son temporales y se borran si el nodo se desconecta, pero el exchange principal se mantiene en el servidor de RabbitMQ.
- **Cola exclusiva y anónima por suscriptor:** Garantiza que cada nodo tenga su propia copia independiente de cada mensaje. La cola se nombra aleatoriamente y no se comparte entre nodos. `exclusive=True` asegura que se borre si el subscriptor se desconecta.
- **Sin prefetch_count:** En fan-out no hay competencia entre consumidores dado que cada uno tiene su propia cola, y por lo tanto, la configuración de fair dispatch (distribución equitativa con `basic_qos`) no aplica.
- **Profile "publisher" en compose:** Permite escalar los subscribers de forma independiente y que el contenedor del publisher solo se dispare manualmente, permitiendo observar el flujo de mensajes bajo demanda.
- **Payload JSON con uuid4 como hash:** Simula de forma realista un evento de bloque en una red blockchain, donde los datos de bloque, timestamp y hash se envían sin necesidad de implementar la criptografía real en la práctica.
