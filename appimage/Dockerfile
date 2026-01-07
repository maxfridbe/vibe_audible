FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    software-properties-common \
    wget \
    curl \
    file \
    git \
    build-essential \
    libffi-dev \
    libssl-dev \
    zlib1g-dev \
    libncurses5-dev \
    libgdbm-dev \
    libnss3-dev \
    libreadline-dev \
    libsqlite3-dev \
    libbz2-dev \
    libfuse2 \
    && rm -rf /var/lib/apt/lists/*

# Install Python 3.11
RUN add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.11 python3.11-dev python3.11-venv python3.11-distutils

# Install pip for 3.11
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Install python-appimage
RUN python3.11 -m pip install python-appimage

# Ensure AppImages can run in container
ENV APPIMAGE_EXTRACT_AND_RUN=1

# Set up workdir
WORKDIR /build

# Download static FFmpeg
RUN wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar xf ffmpeg-release-amd64-static.tar.xz && \
    mv ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ && \
    mv ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ && \
    rm -rf ffmpeg-*

# Copy project files
COPY appimage/main.py /build/main.py
COPY appimage/AppRun /build/AppRun
COPY process_library.py /build/process_library.py

# Create the internal build script
RUN echo '#!/bin/bash' > /build/build_appimage.sh && \
    echo 'set -e' >> /build/build_appimage.sh && \
    echo 'mkdir -p AppDir/usr/bin' >> /build/build_appimage.sh && \
    echo 'mkdir -p AppDir/usr/share/applications' >> /build/build_appimage.sh && \
    echo 'mkdir -p AppDir/usr/share/icons/hicolor/scalable/apps' >> /build/build_appimage.sh && \
    echo '' >> /build/build_appimage.sh && \
    echo '# Use a pre-built python-appimage as base environment' >> /build/build_appimage.sh && \
    echo 'wget https://github.com/niess/python-appimage/releases/download/python3.11/python3.11.14-cp311-cp311-manylinux2014_x86_64.AppImage -O python.AppImage' >> /build/build_appimage.sh && \
    echo 'chmod +x python.AppImage' >> /build/build_appimage.sh && \
    echo './python.AppImage --appimage-extract' >> /build/build_appimage.sh && \
    echo 'cp -r squashfs-root/* AppDir/' >> /build/build_appimage.sh && \
    echo 'rm -rf squashfs-root' >> /build/build_appimage.sh && \
    echo '' >> /build/build_appimage.sh && \
    echo '# Install dependencies into AppDir' >> /build/build_appimage.sh && \
    echo './AppDir/AppRun -m pip install audible-cli tqdm' >> /build/build_appimage.sh && \
    echo '' >> /build/build_appimage.sh && \
    echo '# Copy FFmpeg' >> /build/build_appimage.sh && \
    echo 'cp /usr/local/bin/ffmpeg AppDir/usr/bin/' >> /build/build_appimage.sh && \
    echo 'cp /usr/local/bin/ffprobe AppDir/usr/bin/' >> /build/build_appimage.sh && \
    echo '' >> /build/build_appimage.sh && \
    echo '# Copy our code' >> /build/build_appimage.sh && \
    echo 'cp main.py AppDir/usr/bin/main.py' >> /build/build_appimage.sh && \
    echo 'cp process_library.py AppDir/usr/bin/process_library.py' >> /build/build_appimage.sh && \
    echo '' >> /build/build_appimage.sh && \
    echo '# Set AppRun to use our entry point' >> /build/build_appimage.sh && \
    echo 'rm AppDir/AppRun' >> /build/build_appimage.sh && \
    echo 'cp /build/AppRun AppDir/AppRun' >> /build/build_appimage.sh && \
    echo 'chmod +x AppDir/AppRun' >> /build/build_appimage.sh && \
    echo '' >> /build/build_appimage.sh && \
    echo '# Desktop file and Icon' >> /build/build_appimage.sh && \
    echo 'cat <<EOF > AppDir/vibe-audible-downloader.desktop' >> /build/build_appimage.sh && \
    echo '[Desktop Entry]' >> /build/build_appimage.sh && \
    echo 'Type=Application' >> /build/build_appimage.sh && \
    echo 'Name=Vibe Audible Downloader' >> /build/build_appimage.sh && \
    echo 'Exec=AppRun' >> /build/build_appimage.sh && \
    echo 'Icon=utilities-terminal' >> /build/build_appimage.sh && \
    echo 'Categories=Utility;' >> /build/build_appimage.sh && \
    echo 'Terminal=true' >> /build/build_appimage.sh && \
    echo 'EOF' >> /build/build_appimage.sh && \
    echo 'touch AppDir/usr/share/icons/hicolor/scalable/apps/utilities-terminal.svg' >> /build/build_appimage.sh && \
    echo '' >> /build/build_appimage.sh && \
    echo '# Download appimagetool to bundle it' >> /build/build_appimage.sh && \
    echo 'wget https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage -O appimagetool' >> /build/build_appimage.sh && \
    echo 'chmod +x appimagetool' >> /build/build_appimage.sh && \
    echo '# Build to internal location first, then move' >> /build/build_appimage.sh && \
    echo './appimagetool --appimage-extract-and-run AppDir /build/vibe_audible_downloader.appimage' >> /build/build_appimage.sh && \
    echo 'ls -lh /build/vibe_audible_downloader.appimage' >> /build/build_appimage.sh && \
    chmod +x /build/build_appimage.sh

CMD ["/build/build_appimage.sh"]
