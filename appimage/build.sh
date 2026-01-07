#!/bin/bash
set -e

echo "Building AppImage Builder Docker Image..."
# We run docker build from the parent directory so we can access process_library.py
# But we point to the Dockerfile in appimage/
cd "$(dirname "$0")/.."
podman build -f appimage/Dockerfile -t audible-appimage-builder .

echo "Running AppImage Builder..."
mkdir -p appimage/output

# Run container and name it, don't use --rm yet so we can copy out
# We don't mount /out anymore to avoid permission issues
podman run --name audible-builder-container audible-appimage-builder

echo "Copying AppImage from container..."
podman cp audible-builder-container:/build/vibe_audible_downloader.appimage appimage/output/vibe_audible_downloader.appimage

echo "Removing container..."
podman rm audible-builder-container

echo "AppImage created at appimage/output/vibe_audible_downloader.appimage"
ls -lh appimage/output/vibe_audible_downloader.appimage
chmod +x appimage/output/vibe_audible_downloader.appimage