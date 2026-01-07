# Audible Downloader & Converter

A Dockerized tool to automatically download your Audible library and convert it to M4B format.

## Features
- **Smart Sync:** Skips books that already have an M4B file.
- **Auto-Cleanup:** Deletes the large AAX/AAXC source files after successful conversion.
- **Preference for AAX:** Automatically attempts to get AAX format, falling back to AAXC only if necessary.
- **Persistence:** Saves your login session and downloads to your local machine.
- **Error Handling:** Marks problematic books as `.notdownloadable` to skip them in future runs.

## Setup

### 1. Build the Image
```bash
podman build -t audible-downloader .
```

### 2. Run the Container
You must mount a local directory to `/data` to store your books and session.
```bash
podman run -it -v $(pwd)/audiobooks:/data audible-downloader
```

### 3. First-Time Login
When you run the container for the first time:
1. Enter a **Profile Name** (e.g., `max`).
2. Enter your **Country Code** (e.g., `us`).
3. Follow the link provided to log in via your browser.
4. After logging in, copy the resulting URL (even if the page shows an error) and paste it back into the terminal.

## File Structure
- `audiobooks/`: Your converted `.m4b` files.
- `audiobooks/.audible/`: Your config and session files (do not delete if you want to stay logged in).
- `audiobooks/library.json`: A cached list of your library. Delete this to refresh the list if you buy new books.
- `audiobooks/err_*.notdownloadable`: Markers for books that failed processing. Delete these to retry them.

## Requirements
- Podman (or Docker)
- FFmpeg (included in the image)
