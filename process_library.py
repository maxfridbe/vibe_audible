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

def sanitize_filename(name):
    # Replace non-alphanumeric (except - and .) with _
    # Collapse multiple underscores
    if not name: return ""
    s = re.sub(r'[^a-zA-Z0-9\-\.]', '_', str(name))
    s = re.sub(r'_{2,}', '_', s)
    return s.strip('_')

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
        authors = book.get('authors')
        series_title = book.get('series_title')
        
        if not asin or not title:
            continue
        
        # Prepare tracking names
        clean_title_prefix = sanitize_filename(title)
        err_filename = f"err_{clean_title_prefix}.notdownloadable"
        
        # Calculate base target name early
        clean_author = sanitize_filename(authors)
        clean_series = sanitize_filename(series_title)
        clean_title = sanitize_filename(title)
        
        # Base name for the new file: Author_Series_Title_ASIN
        name_parts = [clean_author]
        if clean_series:
            name_parts.append(clean_series)
        name_parts.append(clean_title)
        name_parts.append(asin)
        
        base_target_name = "_".join(name_parts)

        # 1. Check for existing M4B (Highest Priority) - Skip if found
        normalized_title = normalize_string(title)
        found_match = False
        
        for m4b in all_m4b_files:
            norm_m4b = normalize_string(m4b)
            if normalized_title in norm_m4b or asin.lower() in m4b.lower():
                found_match = True
                break
        
        if found_match:
            print(f"Skipping '{title}' - Matching M4B file found.")
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

            # Attempt 1: Force AAX
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
                     norm_f = normalize_string(f)
                     if asin.lower() in f.lower() or normalized_title in norm_f:
                         source_files.append(f)
                
                if not source_files:
                    reason = f"Error: Download failed or file not found for {title} (ASIN: {asin})"
                    print(f"  {reason}")
                    mark_failed(clean_title_prefix, reason)
                    continue
            else:
                source_files = new_files
                for f in source_files:
                    print(f"  Downloaded: {f}")

        # 5. Get Activation Bytes
        auth_cmd = ["audible", "-P", profile_name, "activation-bytes"]
        auth_res = subprocess.run(auth_cmd, capture_output=True, text=True)
        match = re.search(r'[a-fA-F0-9]{8}', auth_res.stdout)
        if not match:
            reason = "Error: Could not determine activation bytes."
            print(f"  {reason}")
            mark_failed(clean_title_prefix, reason)
            continue
        activation_bytes = match.group(0)

        # 6. Convert Loop
        for source_file in source_files:
            # Handle multi-part suffix
            part_suffix = ""
            # Look for Part information in the source filename
            # matches Part_1, Part-1, Part1
            part_match = re.search(r'(Part[\s_-]?\d+)', source_file, re.IGNORECASE)
            if part_match:
                part_suffix = "_" + part_match.group(1).replace('-', '_').replace(' ', '_')
            
            final_filename = f"{base_target_name}{part_suffix}.m4b"
            # Ensure no double underscores
            final_filename = re.sub(r'_{{2,}}', '_', final_filename)
            
            tmp_target_m4b = final_filename.rsplit('.', 1)[0] + "_tmp.m4b"
            
            if os.path.exists(final_filename):
                 print(f"  Target already exists: {final_filename}")
                 try: os.remove(source_file)
                 except OSError: pass
                 continue

            duration = get_duration(source_file)
            print(f"  Converting {source_file} -> {final_filename}...")
            
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
                fallback_cmd = ["ffmpeg", "-y", "-hide_banner", "-stats", "-loglevel", "error",
                                "-activation_bytes", activation_bytes, "-i", source_file, "-c", "copy", tmp_target_m4b]
                success = (subprocess.run(fallback_cmd).returncode == 0)

            if success:
                print("    Conversion complete.")
                try:
                    os.rename(tmp_target_m4b, final_filename)
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
                mark_failed(clean_title_prefix, reason)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_library.py <profile_name>")
        sys.exit(1)
    process_books(sys.argv[1])