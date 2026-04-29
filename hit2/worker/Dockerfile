FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY sobel_core.py logger.py worker.py .
RUN mkdir -p /app/logs
CMD ["python", "worker.py"]
