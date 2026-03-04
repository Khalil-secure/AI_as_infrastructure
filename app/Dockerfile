FROM python:3.11-slim

WORKDIR /app

RUN pip install flask prometheus-client --no-cache-dir

COPY app.py .

EXPOSE 5000

CMD ["python", "app.py"]