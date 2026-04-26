#!/bin/bash

echo "Starting Botnet Detection System..."

# 1. Start Kafka
echo "[1/4] Starting Kafka..."
docker compose up -d

# 2. Start Backend
echo "[2/4] Starting Backend API..."
# Running in background
./botnet_env/Scripts/python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 3. Start Consumer
echo "[3/4] Starting Detection Consumer..."
# Running in background
./botnet_env/Scripts/python.exe -m consumer.detection_consumer &
CONSUMER_PID=$!

# 4. Start Frontend
echo "[4/4] Starting React Dashboard..."
cd dashboard/frontend-app
npm run dev

# Cleanup background processes on exit
trap "kill $BACKEND_PID $CONSUMER_PID; exit" INT TERM EXIT
