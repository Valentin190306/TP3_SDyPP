/**
 * producer.js
 * Envía 10 mensajes a la cola principal (main_queue).
 * Al menos 3 mensajes tendrán { error: true } y serán enrutados al DLQ
 * después de que el consumidor primario los rechace.
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
      console.log(`[${timestamp()}] [Producer] Intentando conectar a RabbitMQ (intento ${attempt}/${MAX_RETRIES})...`);
      const conn = await amqp.connect(RABBITMQ_URL);
      console.log(`[${timestamp()}] [Producer] Conexión exitosa.`);
      return conn;
    } catch (err) {
      console.error(`[${timestamp()}] [Producer] Fallo al conectar: ${err.message}`);
      if (attempt < MAX_RETRIES) {
        console.log(`[${timestamp()}] [Producer] Reintentando en ${RETRY_DELAY_MS / 1000}s...`);
        await sleep(RETRY_DELAY_MS);
      } else {
        throw new Error("No se pudo conectar a RabbitMQ después de todos los intentos.");
      }
    }
  }
}

async function setupTopology(channel) {
  // Declarar exchange principal
  await channel.assertExchange(MAIN_EXCHANGE, "direct", { durable: true });

  // Declarar Dead Letter Exchange (DLX)
  await channel.assertExchange(DLX_EXCHANGE, "direct", { durable: true });

  // Declarar cola principal con argumentos de DLX
  await channel.assertQueue(MAIN_QUEUE, {
    durable: true,
    arguments: {
      "x-dead-letter-exchange": DLX_EXCHANGE,
      "x-dead-letter-routing-key": DLQ_ROUTING_KEY,
    },
  });

  // Declarar Dead Letter Queue
  await channel.assertQueue(DLQ, { durable: true });

  // Bind: main_queue -> main_exchange
  await channel.bindQueue(MAIN_QUEUE, MAIN_EXCHANGE, MAIN_ROUTING_KEY);

  // Bind: dead_letter_queue -> dlx (con routing key "dead")
  await channel.bindQueue(DLQ, DLX_EXCHANGE, DLQ_ROUTING_KEY);

  console.log(`[${timestamp()}] [Producer] Topología declarada correctamente.`);
}

async function main() {
  const conn = await connectWithRetry();

  conn.on("error", (err) => {
    console.error(`[${timestamp()}] [Producer] Error de conexión: ${err.message}`);
    process.exit(1);
  });

  const channel = await conn.createChannel();
  await setupTopology(channel);

  // 10 mensajes: indices 1,3,5 → error:true (3 mensajes con error), el resto → error:false
  const messages = Array.from({ length: 10 }, (_, i) => {
    const id = i + 1;
    const hasError = [1, 3, 5].includes(id); // exactamente 3 mensajes con error
    return {
      id,
      payload: `Mensaje de prueba #${id}`,
      error: hasError,
      sentAt: timestamp(),
    };
  });

  console.log(`[${timestamp()}] [Producer] Enviando ${messages.length} mensajes...`);

  for (const msg of messages) {
    const content = Buffer.from(JSON.stringify(msg));
    channel.publish(MAIN_EXCHANGE, MAIN_ROUTING_KEY, content, {
      persistent: true,
      contentType: "application/json",
    });
    console.log(
      `[${timestamp()}] [Producer] Enviado → id=${msg.id} | error=${msg.error} | payload="${msg.payload}"`
    );
    await sleep(200); // pequeña pausa para ordenar los logs
  }

  console.log(`[${timestamp()}] [Producer] Todos los mensajes enviados. Cerrando conexión.`);
  await channel.close();
  await conn.close();
}

main().catch((err) => {
  console.error(`[${timestamp()}] [Producer] Error fatal: ${err.message}`);
  process.exit(1);
});
