FROM python:3.11-alpine

WORKDIR /app

COPY frontend /app

EXPOSE 5500

CMD ["python", "-m", "http.server", "5500", "--bind", "0.0.0.0"]
