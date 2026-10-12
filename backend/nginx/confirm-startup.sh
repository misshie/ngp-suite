#!/bin/sh
set -e

# Add a small delay to ensure logs appear after other startup messages.
sleep 1

echo "==========================================================="
echo " API service is healthy. Nginx is starting."
echo " "
PORT="${NGPSUITE_PORT:-443}"
if [ "$PORT" = "443" ]; then URL="https://localhost"; else URL="https://localhost:$PORT"; fi
echo " Application should now be ready at: $URL"
echo " "
echo " If you have not changed the default credentials, see the"
echo " 'Authentication' section of README.md (see also: docker compose logs api)."
echo "==========================================================="

# This script will exit, and the main Nginx entrypoint will continue.
