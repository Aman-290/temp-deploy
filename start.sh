#!/bin/bash

# Exit on error
set -e

# Use PORT environment variable from Cloud Run, default to 8000
PORT=${PORT:-8000}

echo "Starting Jarvis Backend on port $PORT"

# Start OAuth server in background
echo "Starting OAuth server..."
python run_server.py &
SERVER_PID=$!

# Wait a moment for server to start
sleep 2

# Start LiveKit agent
echo "Starting LiveKit agent..."
python run_agent.py dev &
AGENT_PID=$!

# Function to handle shutdown
cleanup() {
    echo "Shutting down gracefully..."
    kill $SERVER_PID $AGENT_PID 2>/dev/null
    wait $SERVER_PID $AGENT_PID 2>/dev/null
    exit 0
}

# Trap signals
trap cleanup SIGTERM SIGINT

# Wait for both processes
wait $SERVER_PID $AGENT_PID
