#!/bin/sh
# Entrypoint script to fix volume permissions

# Fix ownership of data directory (must run as root)
if [ "$(id -u)" = "0" ]; then
    chown -R appuser:appuser /app/data
    # Switch to appuser and execute the command
    exec su appuser -s /bin/sh -c "exec $*"
else
    # Already running as appuser, just execute the command
    exec "$@"
fi
