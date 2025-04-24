#!/bin/bash

echo "Starting Python + Valkary + MySQL services..."
docker compose -f docker-compose.python.yml up --build
