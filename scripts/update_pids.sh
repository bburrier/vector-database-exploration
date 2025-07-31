#!/bin/bash

# Update PID files for running servers
BACKEND_PORT=8000
FRONTEND_PORT=3000
BACKEND_PID=.backend.pid
FRONTEND_PID=.frontend.pid

# Update backend PID
BACKEND_PROCESS=$(lsof -i:$BACKEND_PORT 2>/dev/null | grep LISTEN | awk '{print $2}' | head -1)
if [ ! -z "$BACKEND_PROCESS" ]; then
    echo $BACKEND_PROCESS > $BACKEND_PID
    echo "Backend PID updated: $BACKEND_PROCESS"
else
    echo "Backend PID not found"
fi

# Update frontend PID
FRONTEND_PROCESS=$(lsof -i:$FRONTEND_PORT 2>/dev/null | grep LISTEN | awk '{print $2}' | head -1)
if [ ! -z "$FRONTEND_PROCESS" ]; then
    echo $FRONTEND_PROCESS > $FRONTEND_PID
    echo "Frontend PID updated: $FRONTEND_PROCESS"
else
    echo "Frontend PID not found"
fi 