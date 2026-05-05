/**
 * dlq-consumer.js
 * Consumidor de la Dead Letter Queue (dead_letter_queue).
 * Imprime cada mensaje muerto con el prefijo [DLQ] y lo ack'ea.
 */

const amqp = require("amqplib");

const RABBITMQ_URL = process.env.RABBITMQ_URL || "amqp://guest:guest@localhost:5672";
const MAX_RETRIES = 10;
const RETRY_DELAY_MS = 3000;

const MAIN_EXCHANGE = "main_exchange";
const DLX_EXCHANGE = "dlx";
const MAIN_QUEUE = "main_queue";
const DLQ = "dead_letter_queue";
const DLQ_ROUTING_KEY = "dead";
const MAIN_ROUTING_KEY = "main";

function timestamp() {
  return new Date().toISOString();
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function connectWithRetry() {
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      console.log(`[${timestamp()}] [DLQ-Consumer] Intentando conectar a RabbitMQ (intento ${attempt}/${MAX_RETRIES})...`);
      const conn = await amqp.connect(RABBITMQ_URL);
      console.log(`[${timestamp()}] [DLQ-Consumer] Conexión exitosa.`);
      return conn;
    } catch (err) {
      console.error(`[${timestamp()}] [DLQ-Consumer] Fallo al conectar: ${err.message}`);
      if (attempt < MAX_RETRIES) {
        console.log(`[${timestamp()}] [DLQ-Consumer] Reintentando en ${RETRY_DELAY_MS / 1000}s...`);
        await sleep(RETRY_DELAY_MS);
      } else {
        throw new Error("No se pudo conectar a RabbitMQ después de todos los intentos.");
      }
    }
  }
}

async function setupTopology(channel) {
  // Declarar toda la topología de forma idempotente
  await channel.assertExchange(MAIN_EXCHANGE, "direct", { durable: true });
  await channel.assertExchange(DLX_EXCHANGE, "direct", { durable: true });

  await channel.assertQueue(MAIN_QUEUE, {
    durable: true,
    arguments: {
      "x-dead-letter-exchange": DLX_EXCHANGE,
      "x-dead-letter-routing-key": DLQ_ROUTING_KEY,
    },
  });

  await channel.assertQueue(DLQ, { durable: true });
  await channel.bindQueue(MAIN_QUEUE, MAIN_EXCHANGE, MAIN_ROUTING_KEY);
  await channel.bindQueue(DLQ, DLX_EXCHANGE, DLQ_ROUTING_KEY);

  console.log(`[${timestamp()}] [DLQ-Consumer] Topología declarada correctamente.`);
}

async function main() {
  const conn = await connectWithRetry();

  conn.on("error", (err) => {
    console.error(`[${timestamp()}] [DLQ-Consumer] Error de conexión: ${err.message}`);
    process.exit(1);
  });

  const channel = await conn.createChannel();
  await channel.prefetch(1);
  await setupTopology(channel);

  console.log(`[${timestamp()}] [DLQ-Consumer] Esperando mensajes en "${DLQ}"...`);

  channel.consume(DLQ, (msg) => {
    if (!msg) return;

    let parsed;
    try {
      parsed = JSON.parse(msg.content.toString());
    } catch (e) {
      console.error(`[${timestamp()}] [DLQ-Consumer] Error al parsear mensaje: ${e.message}. Haciendo ack de todas formas.`);
      channel.ack(msg);
      return;
    }

    // Extraer headers de dead-lettering para contexto adicional
    const headers = msg.properties.headers || {};
    const deathInfo = headers["x-death"] ? headers["x-death"][0] : null;
    const reason = deathInfo ? deathInfo.reason : "desconocido";
    const originQueue = deathInfo ? deathInfo.queue : "desconocido";

    console.log(
      `[${timestamp()}] [DLQ] ☠ Mensaje fallido recibido:\n` +
      `  → id:          ${parsed.id}\n` +
      `  → payload:     "${parsed.payload}"\n` +
      `  → error:       ${parsed.error}\n` +
      `  → sentAt:      ${parsed.sentAt}\n` +
      `  → razón DLQ:   ${reason}\n` +
      `  → cola origen: ${originQueue}`
    );

    channel.ack(msg);
    console.log(`[${timestamp()}] [DLQ] ACK → mensaje id=${parsed.id} confirmado en DLQ.`);
  });
}

main().catch((err) => {
  console.error(`[${timestamp()}] [DLQ-Consumer] Error fatal: ${err.message}`);
  process.exit(1);
});
