FROM node:18-alpine

WORKDIR /app

COPY package.json ./
RUN npm install --omit=dev

COPY dlq-consumer.js ./

CMD ["node", "dlq-consumer.js"]
