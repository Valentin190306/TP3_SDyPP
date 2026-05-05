# Ejemplo 5 — Análisis Comparativo de Patrones de Mensajería con RabbitMQ

> **TP3 — Cloud Computing (Kubernetes + RabbitMQ)**  
> Licenciatura en Sistemas de Información

---

## Índice

1. [Patrón 1 — Message Queue (punto a punto)](#patrón-1--message-queue-punto-a-punto)
2. [Patrón 2 — Event Bus / Pub-Sub (fan-out)](#patrón-2--event-bus--pub-sub-fan-out)
3. [Patrón 3 — Dead Letter Queue (DLQ)](#patrón-3--dead-letter-queue-dlq)
4. [Patrón 4 — Retry con Exponential Backoff](#patrón-4--retry-con-exponential-backoff)
5. [Comparativa general](#comparativa-general)
6. [¿Cuándo usar cada patrón?](#cuándo-usar-cada-patrón)

---

## Patrón 1 — Message Queue (punto a punto)

### Descripción

Un productor coloca mensajes en una cola. Cada mensaje es consumido por **exactamente un consumidor**. Si hay múltiples consumidores, RabbitMQ distribuye los mensajes en **round-robin** entre ellos.

### Diagrama de arquitectura

```
┌───────────┐        ┌──────────────────────┐        ┌───────────────┐
│           │        │                      │        │               │
│ Productor │──msg──▶│   Queue: "tareas"    │──msg──▶│ Consumidor A  │
│           │        │                      │        │               │
└───────────┘        │  [msg1][msg2][msg3]  │        └───────────────┘
                     │                      │
                     │  (FIFO, durable)     │──msg──▶┌───────────────┐
                     │                      │        │               │
                     └──────────────────────┘        │ Consumidor B  │
                                                     │               │
                                                     └───────────────┘

  Con 2 consumidores activos:
  msg1 → Consumidor A
  msg2 → Consumidor B
  msg3 → Consumidor A   ← round-robin automático
  msg4 → Consumidor B
```

### Comportamiento observado con 2 consumidores

- RabbitMQ aplica **round-robin** estricto en el despacho de mensajes.
- Ningún mensaje es procesado por más de un consumidor.
- Si un consumidor cae, sus mensajes no confirmados (`unacked`) vuelven a la cola y se redistribuyen al consumidor vivo (siempre que se use `ack` manual).
- Con `prefetch_count=1`, se logra un balanceo más justo: el consumidor más lento no acumula mensajes.

> **Observación:** El round-robin nativo de RabbitMQ no considera la carga real de cada consumidor. Si un consumidor es más lento, sin `prefetch_count` recibirá la misma cantidad de mensajes que uno rápido, generando acumulación. Siempre configurar `basic.qos(prefetch_count=1)`.

---

## Patrón 2 — Event Bus / Pub-Sub (fan-out)

### Descripción

Un publicador envía mensajes a un **exchange de tipo `fanout`**. El exchange replica el mensaje a **todas las colas vinculadas** (bindings). Cada suscriptor tiene su propia cola y recibe una copia completa del mensaje, independientemente de los demás.

### Diagrama de arquitectura

```
                        ┌────────────────────────┐
                        │   Exchange: "bloques"  │
                        │      (type: fanout)    │
                        └───────────┬────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
   │  Queue: nodo_1   │  │  Queue: nodo_2   │  │  Queue: nodo_3   │
   └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
            │                     │                     │
            ▼                     ▼                     ▼
   ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
   │  Suscriptor 1  │   │  Suscriptor 2  │   │  Suscriptor 3  │
   │  (Nodo red)    │   │  (Nodo red)    │   │  (Nodo red)    │
   └────────────────┘   └────────────────┘   └────────────────┘

  Publicador ──▶ Exchange fanout ──▶ [copia] × 3 colas
```

### Comportamiento

- Los 3 suscriptores reciben **el mismo mensaje** de forma simultánea.
- Si un suscriptor no está activo y su cola es **durable**, el mensaje queda encolado hasta que el suscriptor vuelva.
- Si la cola es **exclusiva/auto-delete**, los mensajes emitidos sin suscriptor activo se pierden.

> **Observación:** A diferencia de Apache Kafka, RabbitMQ no persiste un log de eventos histórico. Una vez consumido el mensaje, desaparece. Si un suscriptor se conecta tarde, no recibe eventos anteriores. Para replay de eventos históricos, Kafka es más adecuado.

---

## Patrón 3 — Dead Letter Queue (DLQ)

### Descripción

Cuando un mensaje no puede ser procesado (rechazado con `nack` + `requeue=False`, o expirado por TTL), RabbitMQ lo redirige automáticamente a un **Dead Letter Exchange (DLX)**, que lo deposita en la **Dead Letter Queue (DLQ)**. Un consumidor separado monitorea la DLQ para registrar o re-procesar mensajes fallidos.

### Diagrama de arquitectura

```
┌───────────┐     ┌─────────────────────────────────────────────────┐
│           │     │              Queue: "principal"                  │
│ Productor │────▶│  x-dead-letter-exchange: "dlx"                  │
│           │     │  x-dead-letter-routing-key: "mensajes.muertos"  │
└───────────┘     └──────────────────────┬──────────────────────────┘
                                         │
                            ┌────────────▼────────────┐
                            │     Consumidor Normal    │
                            │                         │
                            │  Si msg["error"]==True:  │
                            │    → nack(requeue=False) │
                            └────────────┬────────────┘
                                         │ (rechazo)
                                         ▼
                            ┌────────────────────────┐
                            │   Exchange DLX (dlx)   │
                            └────────────┬───────────┘
                                         │
                            ┌────────────▼───────────┐
                            │   Queue: "dlq"          │
                            └────────────┬───────────┘
                                         │
                            ┌────────────▼───────────┐
                            │  Consumidor DLQ         │
                            │  (log / alerta / audit) │
                            └────────────────────────┘
```

### Comportamiento

- Los mensajes con `"error": true` son rechazados sin reencolar → van a la DLQ automáticamente.
- Los mensajes válidos son procesados normalmente y eliminados de la cola principal.
- El consumidor de la DLQ puede almacenar los mensajes fallidos en una base de datos, emitir alertas, o intentar reprocesarlos manualmente.

> **Observación:** Sin DLX configurado, un `nack(requeue=False)` simplemente **descarta el mensaje para siempre**. La DLQ es el seguro contra pérdida de datos. En producción, monitorear el tamaño de la DLQ es una señal de alerta temprana de problemas en el sistema.

---

## Patrón 4 — Retry con Exponential Backoff

### Descripción

Cuando un consumidor falla al procesar un mensaje, en lugar de rechazarlo inmediatamente o reintentar infinitamente, lo reencola con un **delay creciente** (1s → 2s → 4s → 8s). Después de N intentos fallidos, el mensaje va a la DLQ.

### Diagrama de arquitectura

```
┌───────────┐    ┌──────────────────────────┐
│ Productor │───▶│   Queue: "procesamiento" │
└───────────┘    └───────────┬──────────────┘
                             │
                 ┌───────────▼──────────────┐
                 │      Consumidor           │
                 │                          │
                 │  Intenta procesar...      │
                 │  ¿Éxito?                 │
                 │    Sí → ack ✓            │
                 │    No → revisar intento# │
                 └───────────┬──────────────┘
                             │ fallo
                             ▼
                 ┌───────────────────────────────────────────┐
                 │  intento < 4?                             │
                 │    Sí → publicar en delay exchange        │
                 │         con TTL = 2^intento segundos      │
                 │         (1s, 2s, 4s, 8s)                  │
                 │                                           │
                 │  intento >= 4?                            │
                 │    No → enviar a DLQ                      │
                 └────────┬─────────────────────────────────┘
                          │
              ┌───────────▼──────────────────┐
              │  Queue: "retry.delay"         │
              │  (x-message-ttl por mensaje)  │
              │  (x-dead-letter → procesamiento│
              │   al expirar el TTL)          │
              └───────────┬──────────────────┘
                          │ (tras TTL)
                          ▼
              ┌─────────────────────────────┐
              │   Queue: "procesamiento"    │ ◀── reingresa con intento+1
              └─────────────────────────────┘

              Tras 4 fallos:
              ┌───────────────────────────┐
              │   Queue: "dlq"            │
              │   (mensaje definitivamente│
              │    no procesable)         │
              └───────────────────────────┘
```

### Log de reintentos (ejemplo esperado)

```
[intento 1] Procesando msg_id=42... FALLO. Reencolar en 1s.
[intento 2] Procesando msg_id=42... FALLO. Reencolar en 2s.
[intento 3] Procesando msg_id=42... FALLO. Reencolar en 4s.
[intento 4] Procesando msg_id=42... FALLO. Reencolar en 8s.
[intento 5] Procesando msg_id=42... FALLO. Enviando a DLQ. ❌
```

> **Observación crítica:** El exponential backoff evita el **thundering herd problem**: si muchos consumidores fallan simultáneamente (ej: la DB está caída), sin backoff todos reintentarían al mismo instante amplificando la sobrecarga. El delay creciente da tiempo al servicio externo para recuperarse.

---

## Comparativa general

| Característica | Queue (P2P) | Pub-Sub (fanout) | DLQ | Retry + Backoff |
|---|---|---|---|---|
| **Receptores por mensaje** | 1 (exclusivo) | N (todos los suscriptores) | 1 (consumidor DLQ) | 1 (reintentado) |
| **Qué pasa si el consumidor falla** | Mensaje vuelve a la cola (con `nack`) | Depende de durabilidad de la cola | Mensaje queda en DLQ | Se reencola con delay |
| **Pérdida de mensajes** | No (si durable + ack manual) | Posible si cola auto-delete | No (DLQ los retiene) | No (hasta agotar reintentos) |
| **Orden garantizado** | Sí (FIFO por cola) | Por suscriptor (no global) | Sí (FIFO por DLQ) | No estricto (delay rompe orden) |
| **Escalabilidad horizontal** | Alta (más consumidores = más throughput) | Alta (más suscriptores sin afectar otros) | Baja (monitoreo) | Media (cuidado con tormentas de reintento) |
| **Complejidad de implementación** | Baja | Baja-Media | Media | Alta |
| **Overhead en RabbitMQ** | Bajo | Medio (N colas) | Bajo | Alto (colas intermedias de delay) |

---

## ¿Cuándo usar cada patrón?

### Message Queue (P2P)
**Usar cuando:** Se necesita distribuir trabajo entre workers en paralelo y cada tarea debe ejecutarse exactamente una vez.

**Ejemplos reales:**
- Procesamiento de imágenes subidas por usuarios (cada imagen → un worker).
- Envío de emails en background (cada email → un worker).
- Procesamiento de pagos (cada transacción → un worker).

**No usar cuando:** Múltiples sistemas necesitan reaccionar al mismo evento (usar Pub-Sub en su lugar).

---

### Pub-Sub / Event Bus (fanout)
**Usar cuando:** Un evento debe notificar a múltiples sistemas independientes, y cada uno debe procesarlo de forma autónoma.

**Ejemplos reales:**
- Notificar a múltiples nodos de una blockchain que se minó un bloque.
- Invalidar caché en múltiples servidores cuando un dato cambia.
- Registrar un evento en un sistema de logs, métricas y auditoría simultáneamente.

**No usar cuando:** Solo hay un receptor, o se necesita historial de eventos (usar Kafka).

---

### Dead Letter Queue (DLQ)
**Usar cuando:** Los mensajes pueden fallar en procesamiento y no deben perderse. Es el "seguro de vida" del sistema de mensajería.

**Ejemplos reales:**
- Órdenes de compra rechazadas por datos inválidos.
- Webhooks de terceros con formato inesperado.
- Cualquier cola de producción (la DLQ debería ser siempre el default).

**No usar cuando:** Los mensajes son efímeros y su pérdida no tiene consecuencias (ej: métricas de telemetría de baja importancia).

---

### Retry con Exponential Backoff
**Usar cuando:** Los fallos son **transitorios** — el sistema receptor puede estar temporalmente caído, con rate limit, o bajo alta carga.

**Ejemplos reales:**
- Llamadas a APIs externas con rate limiting (ej: Stripe, Twilio).
- Escrituras a una base de datos que está reiniciando.
- Procesamiento que depende de un servicio que puede tener picos de latencia.

**No usar cuando:** El fallo es **permanente** (datos inválidos, mensaje malformado). En ese caso, ir directo a la DLQ sin reintentos.

---

## Relación entre patrones en el TP

```
 Productor
     │
     ▼
 [Queue P2P] ─── distribuye trabajo ──▶ Workers
                                           │
                              ┌────────────┴────────────┐
                              │                         │
                        Fallo transitorio         Fallo permanente
                              │                         │
                              ▼                         ▼
                    [Retry + Backoff]              [DLQ directa]
                              │
                    (después de 4 intentos)
                              │
                              ▼
                           [DLQ]
                              │
                    [Pub-Sub fanout] ──▶ Notifica a sistemas de monitoreo
```

Los patrones no son excluyentes: en el TP Integrador, el procesamiento distribuido de imágenes probablemente combine **Queue P2P** (distribuir imágenes entre workers) + **Retry con Backoff** (si un worker falla) + **DLQ** (para imágenes que no pudieron procesarse) + **Pub-Sub** (para notificar al frontend que el procesamiento terminó).
