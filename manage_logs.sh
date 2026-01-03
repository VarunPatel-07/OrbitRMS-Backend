#!/bin/bash

# Lets first Define the Path  for the logs and then we will define two logs path like archive and then we will define the logs for the Archive logs
LOGS_DIR="/Users/varunpatel/Downloads/varun/web-app-development/VarunPatel-RMS-(OrbitRMS)/ObitRMS-Backend/logs"
ARCHIVE_LOGS_DIR="$LOGS_DIR/archive"

# Lets first define the two folder that exist and if not then we will make this function
mkdir -p "$ARCHIVE_LOGS_DIR/runtime"
mkdir -p "$ARCHIVE_LOGS_DIR/failures"

# Now we will move all the compressed run time logs into the runtime folder in the archive
find "$LOGS_DIR/runtime" -name "*.gz" -type f -mtime +7 -exec mv {} "$ARCHIVE_LOGS_DIR/runtime/" \;

#  Now We will move all the compressed run time logs into the failures folder in the archive
find "$LOGS_DIR/failures" -name "*.gz" -type f -mtime +7 -exec mv {} "$ARCHIVE_LOGS_DIR/failures/" \;

# Now We will Delete the logs in the archive/runtime folder that are older then the 30 days then we will delete this 
find "$ARCHIVE_LOGS_DIR/runtime" -name "*.gz" -type f -mtime +30 -exec rm {} \;

# Now We will Delete the logs in the archive/failures folder that are older then the 30 days then we wll delete this 
find "$ARCHIVE_LOGS_DIR/failures" -name "*.gz" -type f -mtime +30 -exec rm {} \;

# We will write the logs for this also 
echo "$(date): Log management completed." >> "$LOGS_DIR/log_management.log"