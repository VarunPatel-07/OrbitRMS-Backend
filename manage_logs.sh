#!/bin/bash


set -e

# Load environment variables
if [ -f .env ]; then
  source .env
else
  echo ".env file not found"
  exit 1
fi

# Validate required variable
if [ -z "$PRODUCTION_LOGS_STORE_DIR" ]; then
  echo "PRODUCTION_LOGS_STORE_DIR not found"
  exit 1
fi
RUNTIME_LOGS="$LOGS_DIR/runtime"
FAILURES_LOGS="$LOGS_DIR/failures"
ARCHIVE_RUNTIME_LOGS="$ARCHIVE_LOGS_DIR/runtime"
ARCHIVE_FAILURES_LOGS="$ARCHIVE_LOGS_DIR/failures"
LOG_MANAGEMENT_FILE_PATH="$LOGS_DIR/log_management.log"


# Lets first define the two folder that exist and if not then we will make this function
mkdir -p "$ARCHIVE_RUNTIME_LOGS"
mkdir -p "$ARCHIVE_FAILURES_LOGS"

# Now we will move all the compressed run time logs into the runtime folder in the archive
find "$RUNTIME_LOGS" -name "*.gz" -type f -mtime +7 -exec mv {} "$ARCHIVE_RUNTIME_LOGS/" \;

#  Now We will move all the compressed run time logs into the failures folder in the archive
find "$FAILURES_LOGS" -name "*.gz" -type f -mtime +7 -exec mv {} "$ARCHIVE_FAILURES_LOGS/" \;

# Now We will Delete the logs in the archive/runtime folder that are older then the 30 days then we will delete this 
find "$ARCHIVE_RUNTIME_LOGS" -name "*.gz" -type f -mtime +30 -exec rm {} \;

# Now We will Delete the logs in the archive/failures folder that are older then the 30 days then we wll delete this 
find "$ARCHIVE_FAILURES_LOGS" -name "*.gz" -type f -mtime +30 -exec rm {} \;

# We will write the logs for this also 
echo "$(date): Log management completed." >> "$LOG_MANAGEMENT_FILE_PATH"