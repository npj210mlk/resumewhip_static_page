#!/bin/bash

# 🌺 ResumeWhip Local Dev Runner (FastAPI edition)
# Starts FastAPI + Stripe webhook listener in parallel, cleans up on Ctrl+C

# Your FastAPI app path — change if needed (e.g., "main:app" or "app.main:app")
APP_PATH="app:app"

# Port for FastAPI (must match your Stripe forward target)
PORT=4242

# Your webhook endpoint
WEBHOOK_ENDPOINT="webhook"

# Stripe listen command
STRIPE_CMD="stripe listen --forward-to localhost:$PORT/$WEBHOOK_ENDPOINT"

echo "🚀 Starting FastAPI app and Stripe webhook listener..."
echo "   FastAPI → http://localhost:$PORT"
echo "   Stripe → forwarding to /$WEBHOOK_ENDPOINT"
echo ""

# Trap Ctrl+C to stop both processes
trap 'echo "🧹 Stopping processes..."; kill $(jobs -p)' SIGINT

# Start FastAPI (Uvicorn) in background
uvicorn $APP_PATH --reload --port $PORT &

# Start Stripe listener in background
$STRIPE_CMD &

# Wait for both to finish
wait

