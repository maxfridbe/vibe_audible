# Audible Downloader & Converter

A Dockerized tool to automatically download your Audible library and convert it to M4B format with organized naming.

## Features
- **Automated Workflow:** Sync starts automatically when the container is launched.
- **Organized Naming:** Files are named using the schema: `Author_Series_Title_ASIN.m4b`.
- **Auto-Rename:** Automatically renames your existing M4B library to the new naming schema.
- **Smart Sync:** Skips books that already have a matching M4B file.
- **Multi-Part Support:** Correctly handles and converts multi-part audiobooks (e.g., Part 1, Part 2).
- **Atomic Conversions:** Uses temporary files (`_tmp.m4b`) to ensure no corrupt files are left if interrupted.
- **Preference for AAX:** Automatically attempts to get high-quality AAX format, falling back to AAXC only if necessary.
- **Auto-Cleanup:** Deletes the large AAX/AAXC source files after successful conversion.
- **Error Handling:** Marks problematic books as `.notdownloadable` to skip them in future runs.

## Setup

### 1. Build the Image
```bash
podman build -t audible-downloader .
```

### 2. Run the Container
Mount your local directory to `/data` to store your books and session.
```bash
podman run -it -v $(pwd)/audiobooks:/data audible-downloader
```

### 3. First-Time Login
The sync starts automatically. If no profile is found:
1. Enter a **Profile Name** (e.g., `max`).
2. Enter your **Country Code** (e.g., `us`).
3. Follow the link provided to log in via your browser.
4. After logging in, copy the resulting URL (even if the page shows an error) and paste it back into the terminal.

## File Structure
- `audiobooks/`: Your converted `.m4b` files, named `Author_Series_Title_ASIN.m4b`.
- `audiobooks/.audible/`: Your config and session files (do not delete if you want to stay logged in).
- `audiobooks/library.json`: A cached list of your library. Delete this to refresh the list if you buy new books.
- `audiobooks/err_*.notdownloadable`: Markers for books that failed processing. Delete these to retry them.

## Requirements
- Podman (or Docker)
- FFmpeg (included in the image)