FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY manifest.json .
COPY app.py .

# State lives in the dnd_data volume mounted here (persisted, not in the image).
ENV DND_DATA_DIR=/data
EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
