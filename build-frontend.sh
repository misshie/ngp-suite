#!/bin/sh
set -e

echo "--- Building frontend ---"
cd frontend
npm run build

echo "--- Copying build artifacts to backend ---"
rm -rf ../backend/static/*
cp -r dist/* ../backend/static/

echo "--- Frontend build complete and copied ---"
