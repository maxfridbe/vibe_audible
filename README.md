# Audible Downloader & Converter

A tool to automatically download your Audible library and convert it to M4B format with organized naming. Available as a Docker container or a standalone AppImage.

## Features
- **Organized Naming:** Files use the schema: `Author_Series_Title_ASIN.m4b`.
- **Auto-Rename:** Automatically detects and renames existing M4B files in your library to match the new schema.
- **Smart Sync:** Skips books that already have a matching M4B file (by title or ASIN).
- **Multi-Part Support:** Correctly handles and converts multi-part audiobooks (e.g., Part 1, Part 2).
- **Atomic Conversions:** Uses temporary files (`_tmp.m4b`) to ensure no corrupt files are left if the process is interrupted.
- **High Quality:** Prefers AAX format, falling back to AAXC only if necessary.
- **Auto-Cleanup:** Deletes large AAX/AAXC source files and vouchers after successful conversion.
- **Error Tracking:** Marks problematic books with `.notdownloadable` markers to skip them in future runs.

---

## Option 1: Docker / Podman (Recommended)

Ideal for keeping your environment clean and running in a consistent container.

### 1. Build the Image
```bash
podman build -t audible-downloader .
```

### 2. Run the Container
Mount a local directory to `/data` to store your books and session.
```bash
podman run -it -v $(pwd)/audiobooks:/data audible-downloader
```

---

## Option 2: Standalone AppImage

Ideal for a portable executable that runs directly on your Linux system.

### 1. Build the AppImage
Requires Podman/Docker for the build process itself.
```bash
./appimage/build.sh
```
The executable is created at `appimage/output/vibe_audible_downloader.appimage`.

### 2. Run the AppImage
Move the `.appimage` file to the directory where you want to store your library and run it:
```bash
./vibe_audible_downloader.appimage
```
*Note: All config, library logs, and downloaded books will be created in the directory where the AppImage is launched.*

---

## First-Time Login
Whether using Docker or AppImage, the first run will require a login:
1. Enter a **Profile Name** (e.g., `mybooks`).
2. Enter your **Country Code** (e.g., `us`).
3. Follow the provided link to log in via your browser.
4. After logging in, copy the resulting URL (even if the page shows an error) and paste it back into the terminal.

## File Structure
- `*.m4b`: Your converted audiobooks.
- `.audible/`: Configuration and session files (do not delete to stay logged in).
- `library.json`: Cached library list. Delete to refresh if you buy new books.
- `err_*.notdownloadable`: Markers for failed books. Delete to retry them.

## Requirements
- **Docker** or **Podman** (for building or running Option 1)
- **Linux** (for AppImage)
- **FFmpeg** (included in both the Docker image and AppImage)
