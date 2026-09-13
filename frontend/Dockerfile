FROM node:20-alpine

WORKDIR /app

COPY frontend/package.json /app/package.json
COPY frontend /app

ENV HOST=0.0.0.0
ENV PORT=5500

EXPOSE 5500

CMD ["node", "dev-server.mjs", "--port", "5500"]
