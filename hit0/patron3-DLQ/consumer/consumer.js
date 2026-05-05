/**
 * consumer.js
 * Consumidor primario de main_queue.
 * - Si message.error === true  → nack sin reencolar → RabbitMQ lo envía al DLQ vía DLX
 * - Si message.error === false → procesa y ack
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
      console.log(`[${timestamp()}] [Consumer] Intentando conectar a RabbitMQ (intento ${attempt}/${MAX_RETRIES})...`);
      const conn = await amqp.connect(RABBITMQ_URL);
      console.log(`[${timestamp()}] [Consumer] Conexión exitosa.`);
      return conn;
    } catch (err) {
      console.error(`[${timestamp()}] [Consumer] Fallo al conectar: ${err.message}`);
      if (attempt < MAX_RETRIES) {
        console.log(`[${timestamp()}] [Consumer] Reintentando en ${RETRY_DELAY_MS / 1000}s...`);
        await sleep(RETRY_DELAY_MS);
      } else {
        throw new Error("No se pudo conectar a RabbitMQ después de todos los intentos.");
      }
    }
  }
}

async function setupTopology(channel) {
  // Ambos consumidores declaran la topología completa para garantizar idempotencia
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

  console.log(`[${timestamp()}] [Consumer] Topología declarada correctamente.`);
}

async function main() {
  const conn = await connectWithRetry();

  conn.on("error", (err) => {
    console.error(`[${timestamp()}] [Consumer] Error de conexión: ${err.message}`);
    process.exit(1);
  });

  const channel = await conn.createChannel();
  await channel.prefetch(1);
  await setupTopology(channel);

  console.log(`[${timestamp()}] [Consumer] Esperando mensajes en "${MAIN_QUEUE}"...`);

  channel.consume(MAIN_QUEUE, (msg) => {
    if (!msg) return;

    let parsed;
    try {
      parsed = JSON.parse(msg.content.toString());
    } catch (e) {
      console.error(`[${timestamp()}] [Consumer] Error al parsear mensaje: ${e.message}. Haciendo nack.`);
      channel.nack(msg, false, false);
      return;
    }

    const { id, payload, error } = parsed;
    console.log(`[${timestamp()}] [Consumer] Recibido → id=${id} | error=${error} | payload="${payload}"`);

    if (error === true) {
      console.log(`[${timestamp()}] [Consumer] ✗ NACK (sin reencolar) → id=${id} será enviado al DLQ.`);
      channel.nack(msg, false, false); // (msg, allUpTo=false, requeue=false)
    } else {
      console.log(`[${timestamp()}] [Consumer] ✓ ACK → id=${id} procesado exitosamente.`);
      channel.ack(msg);
    }
  });
}

main().catch((err) => {
  console.error(`[${timestamp()}] [Consumer] Error fatal: ${err.message}`);
  process.exit(1);
});
