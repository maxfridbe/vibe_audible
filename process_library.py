import json
import os
import subprocess
import re
import sys
import glob

def sanitize_for_glob(name):
    # Remove characters that might interfere with globbing or are sanitized by audible-cli
    return re.sub(r'[^a-zA-Z0-9]', '_', name)

def normalize_string(s):
    # Remove all non-alphanumeric characters and lowercase
    return re.sub(r'[^a-z0-9]', '', s.lower())

def mark_failed(clean_title, reason):
    filename = f"err_{clean_title}.notdownloadable"
    try:
        with open(filename, "w") as f:
            f.write(reason)
        print(f"  Marked as failed: {filename}")
    except OSError as e:
        print(f"  Error writing failure marker: {e}")

def process_books(profile_name):
    try:
        with open("library.json", "r") as f:
            books = json.load(f)
    except FileNotFoundError:
        print("Error: library.json not found.")
        sys.exit(1)

    print(f"Found {len(books)} books in library.")

    # Get all M4B files once to avoid hitting disk repeatedly
    all_m4b_files = glob.glob("*.m4b")

    for book in books:
        asin = book.get('asin')
        title = book.get('title')
        
        if not asin or not title:
            continue
        
        # Prepare tracking names
        clean_prefix = sanitize_for_glob(title)
        err_filename = f"err_{clean_prefix}.notdownloadable"

        # 1. Check if previously marked as failed
        if os.path.exists(err_filename):
            print(f"Skipping '{title}' - Previously marked as not downloadable.")
            continue

        # 2. Check for existing M4B
        normalized_title = normalize_string(title)
        existing_m4b = None
        
        for m4b in all_m4b_files:
            if normalize_string(m4b).startswith(normalized_title):
                existing_m4b = m4b
                break
        
        if existing_m4b:
            print(f"Skipping '{title}' - M4B already exists ({existing_m4b})")
            continue

        print(f"\nProcessing: {title} (ASIN: {asin})")

        # 3. Check for existing AAX/AAXC source file
        source_file = None
        all_source_files = glob.glob("*.aax") + glob.glob("*.aaxc")
        
        # Strategy A: ASIN in filename
        for f in all_source_files:
            if asin.lower() in f.lower():
                source_file = f
                break
        
        # Strategy B: Title prefix in filename
        if not source_file:
            for f in all_source_files:
                if clean_prefix in f:
                    source_file = f
                    break

        if source_file:
             if source_file.endswith(".aaxc"):
                 print(f"  Found AAXC file ({source_file}). Deleting to attempt AAX download...")
                 try:
                     os.remove(source_file)
                     voucher = source_file.rsplit('.', 1)[0] + ".voucher"
                     if os.path.exists(voucher):
                         os.remove(voucher)
                     source_file = None # Force re-download
                 except OSError as e:
                     print(f"  Warning: Could not delete AAXC file: {e}")
             else:
                 print(f"  Found existing source file: {source_file}")

        # 4. Download if needed
        if not source_file:
            print(f"  No existing AAX file matched ASIN '{asin}' or prefix '{clean_prefix}'")
            print(f"  Downloading (Attempting AAX)...")
            
            before_files = set(glob.glob("*.aax") + glob.glob("*.aaxc"))

            # Attempt 1: Force AAX
            cmd = [
                "audible", "-P", profile_name, "download",
                "-a", asin, "--aax", "-y"
            ]
            result = subprocess.run(cmd)

            if result.returncode != 0:
                print(f"  AAX download failed. Falling back to standard download (likely AAXC only)...")
                cmd_fallback = [
                    "audible", "-P", profile_name, "download",
                    "-a", asin, "--aax-fallback", "-y"
                ]
                subprocess.run(cmd_fallback)

            # Find the new file
            after_files = set(glob.glob("*.aax") + glob.glob("*.aaxc"))
            new_files = after_files - before_files
            
            if not new_files:
                # Fallback scan
                all_source_files_now = glob.glob("*.aax") + glob.glob("*.aaxc")
                for f in all_source_files_now:
                     if asin.lower() in f.lower():
                         source_file = f
                         break
                
                if source_file:
                    print(f"  Found file after download: {source_file}")
                else:
                    reason = f"Error: Download failed or file not found for {title} (ASIN: {asin})"
                    print(f"  {reason}")
                    mark_failed(clean_prefix, reason)
                    continue
            else:
                source_file = list(new_files)[0]
                print(f"  Downloaded: {source_file}")

        # 5. Get Activation Bytes
        auth_cmd = ["audible", "-P", profile_name, "activation-bytes"]
        auth_res = subprocess.run(auth_cmd, capture_output=True, text=True)
        match = re.search(r'[a-fA-F0-9]{8}', auth_res.stdout)
        if not match:
            reason = "Error: Could not determine activation bytes."
            print(f"  {reason}")
            mark_failed(clean_prefix, reason)
            continue
        activation_bytes = match.group(0)

        # 6. Convert
        target_m4b = source_file.rsplit('.', 1)[0] + ".m4b"
        print(f"  Converting to {target_m4b}...")
        
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-hide_banner",
            "-activation_bytes", activation_bytes,
            "-i", source_file,
            "-c", "copy",
            target_m4b
        ]
        
        conv_result = subprocess.run(ffmpeg_cmd)
        
        if conv_result.returncode == 0:
            print("  Conversion successful.")
            try:
                os.remove(source_file)
                voucher = source_file.rsplit('.', 1)[0] + ".voucher"
                if os.path.exists(voucher):
                    os.remove(voucher)
                print("  Deleted source file.")
            except OSError:
                pass
        else:
            reason = f"Error: FFmpeg conversion failed for {source_file}"
            print(f"  {reason}")
            mark_failed(clean_prefix, reason)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_library.py <profile_name>")
        sys.exit(1)
    process_books(sys.argv[1])
