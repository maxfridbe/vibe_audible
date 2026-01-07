#!/bin/bash
set -e

# Detect container engine
if command -v podman &> /dev/null; then
    CONTAINER_ENGINE="podman"
elif command -v docker &> /dev/null; then
    CONTAINER_ENGINE="docker"
else
    echo "Error: Neither podman nor docker found."
    exit 1
fi

echo "Using container engine: $CONTAINER_ENGINE"

echo "Building AppImage Builder Docker Image..."
# We run docker build from the parent directory so we can access process_library.py
# But we point to the Dockerfile in appimage/
cd "$(dirname "$0")/.."
$CONTAINER_ENGINE build -f appimage/Dockerfile -t audible-appimage-builder .

echo "Running AppImage Builder..."
mkdir -p appimage/output

# Run container and name it, don't use --rm yet so we can copy out
# We don't mount /out anymore to avoid permission issues
$CONTAINER_ENGINE run --name audible-builder-container audible-appimage-builder

echo "Copying AppImage from container..."
$CONTAINER_ENGINE cp audible-builder-container:/build/vibe_audible_downloader.appimage appimage/output/vibe_audible_downloader.appimage

echo "Removing container..."
$CONTAINER_ENGINE rm audible-builder-container

echo "AppImage created at appimage/output/vibe_audible_downloader.appimage"
ls -lh appimage/output/vibe_audible_downloader.appimage
chmod +x appimage/output/vibe_audible_downloader.appimage
