import os
import glob
import json
import re
import subprocess
import difflib
import sys

LIBRARY_FILE = "audiobooks/library.json"
AUDIOBOOKS_DIR = "audiobooks"

def sanitize_filename(name):
    if not name: return ""
    s = re.sub(r'[^a-zA-Z0-9\-\.]', '_', str(name))
    s = re.sub(r'_{2,}', '_', s)
    return s.strip('_')

def get_metadata(filepath):
    cmd = [
        "ffprobe", "-v", "quiet", 
        "-print_format", "json", 
        "-show_format", 
        filepath
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        tags = data.get("format", {}).get("tags", {})
        return tags.get("title"), tags.get("artist")
    except:
        return None, None

def load_library():
    try:
        with open(LIBRARY_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading library: {e}")
        return []

def main():
    if not os.path.exists(LIBRARY_FILE):
        print(f"Library file not found at {LIBRARY_FILE}")
        return

    library = load_library()
    print(f"Loaded {len(library)} books from library.")

    files = glob.glob(os.path.join(AUDIOBOOKS_DIR, "*.m4b"))
    files.sort()
    
    # Pre-index library for strict matching
    library_by_asin = {b['asin']: b for b in library if 'asin' in b}
    
    # Check each file
    for filepath in files:
        filename = os.path.basename(filepath)
        
        # 1. Strict Match by ASIN in filename
        matched_book = None
        for asin, book in library_by_asin.items():
            if asin in filename:
                matched_book = book
                break
        
        if matched_book:
            continue # Skip files that are already identified/named with ASIN

        # 2. Metadata extraction
        print(f"\n---------------------------------------------------")
        print(f"Processing: {filename}")
        meta_title, meta_artist = get_metadata(filepath)
        
        if not meta_title:
            print("  No title found in metadata. Skipping.")
            continue

        print(f"  Metadata Title:  {meta_title}")
        print(f"  Metadata Artist: {meta_artist}")

        # 3. Fuzzy Match
        # We search primarily by Title
        candidates = []
        titles = [b.get('title', '') for b in library]
        
        # Get matches
        matches = difflib.get_close_matches(meta_title, titles, n=3, cutoff=0.1)
        
        seen_asins = set()
        for m in matches:
            for b in library:
                if b.get('title') == m and b.get('asin') not in seen_asins:
                    candidates.append(b)
                    seen_asins.add(b.get('asin'))
                    break
        
        if not candidates:
            print("  No library matches found.")
            continue

        print(f"\n  Select the correct book from library (or 0 to skip):")
        for idx, book in enumerate(candidates):
            print(f"    {idx+1}. {book.get('title')} (ASIN: {book.get('asin')})")
            print(f"       By: {book.get('authors')}")
        
        choice = input("\n  Choice [1-3, 0]: ").strip()
        
        if choice in ['1', '2', '3'] and int(choice) <= len(candidates):
            selected_book = candidates[int(choice)-1]
            
            # Rename logic
            authors = selected_book.get("authors")
            if isinstance(authors, list): authors = ", ".join(authors)
            
            new_author = sanitize_filename(authors)
            new_series = sanitize_filename(selected_book.get("series_title"))
            new_title = sanitize_filename(selected_book.get("title"))
            new_asin = selected_book.get("asin")
            
            parts = [new_author]
            if new_series: parts.append(new_series)
            parts.append(new_title)
            parts.append(new_asin)
            
            base_name = "_".join(parts)
            
            # Preserve Part suffix
            part_suffix = ""
            part_match = re.search(r'(Part[\s_-]?\d+)', filename, re.IGNORECASE)
            if part_match:
                p_str = part_match.group(1)
                nums = re.findall(r'\d+', p_str)
                if nums:
                    part_suffix = f"_Part_{nums[0]}"
            
            final_name = f"{base_name}{part_suffix}.m4b"
            final_name = re.sub(r'_{2,}', '_', final_name)
            
            new_path = os.path.join(AUDIOBOOKS_DIR, final_name)
            
            if filepath != new_path:
                try:
                    os.rename(filepath, new_path)
                    print(f"  Renamed to: {final_name}")
                except OSError as e:
                    print(f"  Error renaming: {e}")
            else:
                print("  File is already named correctly.")
        else:
            print("  Skipped.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
