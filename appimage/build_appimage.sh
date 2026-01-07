#!/bin/bash
set -e

# Initialize AppDir structure
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/share/icons
mkdir -p AppDir/usr/share/applications

# Create desktop file
cat <<EOF > AppDir/usr/share/applications/audible-downloader.desktop
[Desktop Entry]
Type=Application
Name=AudibleDownloader
Exec=main
Icon=utilities-terminal
Categories=Utility;
Terminal=true
EOF

# Dummy icon
touch AppDir/usr/share/icons/utilities-terminal.svg

# Copy FFmpeg binaries
cp /usr/local/bin/ffmpeg AppDir/usr/bin/
cp /usr/local/bin/ffprobe AppDir/usr/bin/

# Configure Python plugin via environment variables
export PIP_INSTALL="audible-cli tqdm"
export PYTHON_VERSION=3.11

# Run linuxdeploy with python plugin
linuxdeploy --appdir AppDir \
    --plugin python \
    --executable /usr/bin/python3.11 \
    --desktop-file AppDir/usr/share/applications/audible-downloader.desktop \
    --icon-file AppDir/usr/share/icons/utilities-terminal.svg

# Copy our application code into the bundled python environment
cp /build/main.py AppDir/usr/bin/main.py
cp /build/process_library.py AppDir/usr/bin/process_library.py

# Create the entry point wrapper
# In the AppImage, usr/bin is in the PATH
cat <<EOF > AppDir/usr/bin/main
#!/bin/bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$DIR:$PATH"
# Use the bundled python
exec "$DIR/python3.11" "$DIR/main.py" "$@"
EOF
chmod +x AppDir/usr/bin/main

# Final bundle
# We use --output appimage to trigger the appimage creation
linuxdeploy --appdir AppDir --output appimage

# Move to output volume
mv AudibleDownloader*.AppImage /out/vibe_audible_downloader.appimage
