#!/bin/bash

echo "Starting Python + Valkary + MySQL services..."
docker compose -f docker-compose.docker-run.yml up --build
