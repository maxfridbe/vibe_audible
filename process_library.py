import json
import os
import subprocess
import re
import sys
import glob

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

def sanitize_for_glob(name):
    # Remove characters that might interfere with globbing
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

def get_duration(filename):
    cmd = [
        "ffprobe", "-v", "error", 
        "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        filename
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return None

def process_books(profile_name):
    try:
        with open("library.json", "r") as f:
            books = json.load(f)
    except FileNotFoundError:
        print("Error: library.json not found.")
        sys.exit(1)

    print(f"Found {len(books)} books in library.")

    # Get all M4B files once
    all_m4b_files = glob.glob("*.m4b")

    for book in books:
        asin = book.get('asin')
        title = book.get('title')
        
        if not asin or not title:
            continue
        
        clean_prefix = sanitize_for_glob(title)
        err_filename = f"err_{clean_prefix}.notdownloadable"

        # 1. Check for existing M4B (Highest Priority)
        normalized_title = normalize_string(title)
        existing_m4b = None
        
        for m4b in all_m4b_files:
            norm_m4b = normalize_string(m4b)
            if normalized_title in norm_m4b or asin.lower() in m4b.lower():
                existing_m4b = m4b
                break
        
        if existing_m4b:
            print(f"Skipping '{title}' - M4B already exists ({existing_m4b})")
            continue

        # 2. Check for existing AAX/AAXC source files
        source_files = []
        all_source_files = glob.glob("*.aax") + glob.glob("*.aaxc")
        
        for f in all_source_files:
            if asin.lower() in f.lower() or normalized_title in normalize_string(f):
                source_files.append(f)

        # 3. Check for previous failure markers
        if os.path.exists(err_filename):
            if source_files:
                print(f"  Found source file(s) for '{title}', ignoring previous failure marker. Retrying...")
                try: os.remove(err_filename)
                except OSError: pass
            else:
                print(f"Skipping '{title}' - Previously marked as not downloadable.")
                continue

        print(f"\nProcessing: {title} (ASIN: {asin})")

        if source_files:
             for f in list(source_files):
                 if f.endswith(".aaxc"):
                     print(f"  Found AAXC file ({f}). Deleting to attempt AAX download...")
                     try:
                         os.remove(f)
                         voucher = f.rsplit('.', 1)[0] + ".voucher"
                         if os.path.exists(voucher):
                             os.remove(voucher)
                         source_files.remove(f)
                     except OSError: pass
             
        if not source_files:
            print(f"  Downloading...")
            before_files = set(glob.glob("*.aax") + glob.glob("*.aaxc"))

            # Attempt AAX
            cmd = ["audible", "-P", profile_name, "download", "-a", asin, "--aax", "-y"]
            result = subprocess.run(cmd)

            if result.returncode != 0:
                print(f"  AAX failed. Retrying with fallback...")
                cmd_fallback = ["audible", "-P", profile_name, "download", "-a", asin, "--aax-fallback", "-y"]
                subprocess.run(cmd_fallback)

            after_files = set(glob.glob("*.aax") + glob.glob("*.aaxc"))
            new_files = list(after_files - before_files)
            
            if not new_files:
                all_source_files_now = glob.glob("*.aax") + glob.glob("*.aaxc")
                for f in all_source_files_now:
                     if asin.lower() in f.lower() or normalized_title in normalize_string(f):
                         source_files.append(f)
                
                if not source_files:
                    reason = f"Error: Download failed for {title}"
                    print(f"  {reason}")
                    mark_failed(clean_prefix, reason)
                    continue
            else:
                source_files = new_files

        # Get Activation Bytes
        auth_cmd = ["audible", "-P", profile_name, "activation-bytes"]
        auth_res = subprocess.run(auth_cmd, capture_output=True, text=True)
        match = re.search(r'[a-fA-F0-9]{8}', auth_res.stdout)
        if not match:
            reason = "Error: Could not determine activation bytes."
            print(f"  {reason}")
            mark_failed(clean_prefix, reason)
            continue
        activation_bytes = match.group(0)

        # Convert
        for source_file in source_files:
            target_m4b = source_file.rsplit('.', 1)[0] + ".m4b"
            tmp_target_m4b = source_file.rsplit('.', 1)[0] + "_tmp.m4b"
            
            if os.path.exists(target_m4b):
                 print(f"  Part already exists: {target_m4b}")
                 try: os.remove(source_file)
                 except OSError: pass
                 continue

            duration = get_duration(source_file)
            print(f"  Converting {source_file}...")
            
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-progress", "pipe:1",
                "-activation_bytes", activation_bytes, "-i", source_file, "-c", "copy", tmp_target_m4b
            ]
            
            success = False
            if duration and tqdm:
                with tqdm(total=int(duration), unit='s', unit_scale=True, desc="    Progress", leave=False) as pbar:
                    process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, text=True)
                    last_t = 0
                    for line in process.stdout:
                        if "out_time_ms=" in line:
                            try:
                                t_us = int(line.split("=")[1])
                                t_s = t_us // 1000000
                                pbar.update(t_s - last_t)
                                last_t = t_s
                            except: pass
                    process.wait()
                    success = (process.returncode == 0)
            else:
                # Fallback if ffprobe/tqdm fails
                fallback_cmd = ["ffmpeg", "-y", "-hide_banner", "-stats", "-loglevel", "error",
                                "-activation_bytes", activation_bytes, "-i", source_file, "-c", "copy", tmp_target_m4b]
                success = (subprocess.run(fallback_cmd).returncode == 0)

            if success:
                print("    Conversion complete.")
                try:
                    os.rename(tmp_target_m4b, target_m4b)
                    os.remove(source_file)
                    voucher = source_file.rsplit('.', 1)[0] + ".voucher"
                    if os.path.exists(voucher):
                        os.remove(voucher)
                except OSError as e:
                    print(f"    Error finalizing file: {e}")
            else:
                reason = f"Error: FFmpeg failed for {source_file}"
                print(f"  {reason}")
                try: os.remove(tmp_target_m4b)
                except OSError: pass
                mark_failed(clean_prefix, reason)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_library.py <profile_name>")
        sys.exit(1)
    process_books(sys.argv[1])