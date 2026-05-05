FROM node:18-alpine

WORKDIR /app

# Copiar dependencias primero para aprovechar cache de capas
COPY package.json ./
RUN npm install --omit=dev

# Copiar código fuente
COPY producer.js ./

CMD ["node", "producer.js"]
