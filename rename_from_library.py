import os
import glob
import json
import re
import subprocess

LIBRARY_FILE = "audiobooks/library.json"
AUDIOBOOKS_DIR = "audiobooks"

def sanitize_filename(name):
    if not name: return ""
    s = re.sub(r'[^a-zA-Z0-9\-\.]', '_', str(name))
    s = re.sub(r'_{2,}', '_', s)
    return s.strip('_')

def get_metadata_title_artist(filepath):
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
    library = load_library()
    print(f"Loaded {len(library)} books from library.")

    library_by_asin = {b['asin']: b for b in library if 'asin' in b}
    
    library_by_meta = {}
    for b in library:
        t = b.get('title')
        a = b.get('authors')
        if isinstance(a, list): a = " ".join(a)
        if t and a:
            key = (t.lower().strip(), a.lower().strip())
            library_by_meta[key] = b

    files = glob.glob(os.path.join(AUDIOBOOKS_DIR, "*.m4b"))
    print(f"Scanning {len(files)} files...")

    for filepath in files:
        filename = os.path.basename(filepath)
        
        matched_book = None
        
        # 1. Try to find ASIN in filename
        # Ensure ASIN is long enough to avoid partial matches (e.g. "B0")
        for asin, book in library_by_asin.items():
            if len(asin) >= 8 and asin in filename:
                matched_book = book
                break
        
        # 2. If no ASIN match, try metadata
        if not matched_book:
            meta_title, meta_artist = get_metadata_title_artist(filepath)
            if meta_title and meta_artist:
                key = (meta_title.lower().strip(), meta_artist.lower().strip())
                matched_book = library_by_meta.get(key)
                if not matched_book:
                    candidates = [b for k, b in library_by_meta.items() if k[0] == key[0]]
                    if len(candidates) == 1:
                        matched_book = candidates[0]

        if matched_book:
            authors = matched_book.get("authors")
            if isinstance(authors, list): authors = ", ".join(authors)
            
            new_author = sanitize_filename(authors)
            new_series = sanitize_filename(matched_book.get("series_title"))
            new_title = sanitize_filename(matched_book.get("title"))
            new_asin = matched_book.get("asin")
            
            parts = [new_author]
            if new_series:
                parts.append(new_series)
            parts.append(new_title)
            parts.append(new_asin)
            
            base_name = "_".join(parts)
            
            part_suffix = ""
            part_match = re.search(r'(Part[\s_-]?\d+)', filename, re.IGNORECASE)
            if part_match:
                p_str = part_match.group(1)
                nums = re.findall(r'\d+', p_str)
                if nums:
                    part_suffix = f"_Part_{nums[0]}"
            
            final_name = f"{base_name}{part_suffix}.m4b"
            final_name = re.sub(r'_{2,}', '_', final_name)
            
            new_filepath = os.path.join(AUDIOBOOKS_DIR, final_name)
            
            if filepath != new_filepath:
                print(f"Match: {filename} -> {matched_book.get('title')} ({new_asin})")
                if os.path.exists(new_filepath):
                    print(f"  Target exists. Overwriting: {final_name}")
                    try:
                        os.remove(new_filepath)
                        os.rename(filepath, new_filepath)
                    except OSError as e:
                        print(f"  Error overwriting: {e}")
                else:
                    print(f"  Renaming to: {final_name}")
                    try:
                        os.rename(filepath, new_filepath)
                    except OSError as e:
                        print(f"  Error renaming: {e}")
        else:
            print(f"Could not identify book for: {filename}")

if __name__ == "__main__":
    main()