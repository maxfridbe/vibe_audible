FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install audible-cli and tqdm for beautiful progress bars
RUN pip install --no-cache-dir audible-cli tqdm

# Set environment variables
ENV AUDIBLE_CONFIG_DIR=/data/.audible
ENV SUPPRESS_BOLTDB_WARNING=1

WORKDIR /data

COPY audible-walkthrough.sh /usr/local/bin/audible-walkthrough
COPY process_library.py /usr/local/bin/process_library.py
RUN chmod +x /usr/local/bin/audible-walkthrough

# Automatically start the walkthrough when the container runs
CMD ["/bin/bash", "-c", "audible-walkthrough; /bin/bash"]
