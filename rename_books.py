import os
import glob
import subprocess
import json
import re
import sys

LIBRARY_FILE = "audiobooks/library.json"
AUDIOBOOKS_DIR = "audiobooks"

def get_metadata(filepath):
    """Extract tags from m4b file using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", 
        "-print_format", "json", 
        "-show_format", 
        filepath
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return data.get("format", {}).get("tags", {})
    except Exception as e:
        print(f"Error reading metadata for {filepath}: {e}")
        return {}

def sanitize_filename(name):
    if not name: return ""
    # Replace non-alphanumeric (except - and .) with _
    s = re.sub(r'[^a-zA-Z0-9\-\.]', '_', str(name))
    # Collapse multiple underscores
    s = re.sub(r'_{2,}', '_', s)
    return s.strip('_')

def normalize_string(s):
    if not s: return ""
    return re.sub(r'[^a-z0-9]', '', s.lower())

def load_library():
    if not os.path.exists(LIBRARY_FILE):
        return []
    try:
        with open(LIBRARY_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def main():
    library = load_library()
    print(f"Loaded {len(library)} books from library cache.")
    
    # Create lookup map: (Title, Author) -> Book Info
    # We use normalized strings for matching
    library_map = {}
    for book in library:
        title = normalize_string(book.get("title", ""))
        # Author is often list or string
        authors = book.get("authors", [])
        if isinstance(authors, list):
            authors = " ".join(authors)
        
        # We assume the metadata 'artist' matches 'authors' roughly
        # For lookup, we might just key by Title if unique, or Title+ASIN
        
        # Store by normalized title for easy lookup
        if title:
            if title not in library_map:
                library_map[title] = []
            library_map[title].append(book)

    files = glob.glob(os.path.join(AUDIOBOOKS_DIR, "*.m4b"))
    print(f"Found {len(files)} M4B files.")

    for filepath in files:
        tags = get_metadata(filepath)
        
        meta_title = tags.get("title", "")
        meta_artist = tags.get("artist", "")
        meta_album = tags.get("album", "")
        
        if not meta_title:
            print(f"Skipping {filepath} - No title in metadata.")
            continue

        # Try to find in library
        norm_title = normalize_string(meta_title)
        
        candidates = library_map.get(norm_title, [])
        
        # If no direct title match, try fuzzy or album match
        if not candidates and meta_album:
             norm_album = normalize_string(meta_album)
             candidates = library_map.get(norm_album, [])

        selected_book = None
        
        if len(candidates) == 1:
            selected_book = candidates[0]
        elif len(candidates) > 1:
            # Disambiguate by author
            norm_artist = normalize_string(meta_artist)
            for b in candidates:
                b_authors = b.get("authors", "")
                if isinstance(b_authors, list): b_authors = " ".join(b_authors)
                if normalize_string(b_authors) in norm_artist or norm_artist in normalize_string(b_authors):
                    selected_book = b
                    break
            # If still ambiguous, maybe check existing filename for ASIN?
            if not selected_book:
                current_filename = os.path.basename(filepath)
                for b in candidates:
                    if b.get("asin") in current_filename:
                        selected_book = b
                        break
        
        # If found in library, construct full name
        if selected_book:
            new_author = sanitize_filename(selected_book.get("authors"))
            new_series = sanitize_filename(selected_book.get("series_title"))
            new_title = sanitize_filename(selected_book.get("title"))
            new_asin = selected_book.get("asin")
            
            parts = [new_author]
            if new_series:
                parts.append(new_series)
            parts.append(new_title)
            parts.append(new_asin)
            
            base_name = "_".join(parts)
        else:
            # Fallback to metadata only
            # Schema: Author_Title_Album.m4b? Or just Author_Title.m4b
            # We don't have ASIN or Series strictly (Album might be series or title)
            print(f"Warning: '{meta_title}' not found in library. Using metadata tags directly.")
            clean_author = sanitize_filename(meta_artist)
            clean_title = sanitize_filename(meta_title)
            # If album is different from title, maybe it's series?
            clean_series = ""
            if meta_album and meta_album != meta_title:
                 clean_series = sanitize_filename(meta_album)
            
            parts = [clean_author]
            if clean_series: parts.append(clean_series)
            parts.append(clean_title)
            # No ASIN
            
            base_name = "_".join(parts)

        # Handle Parts (preserve from original filename if detected)
        # Regex to find _Part_X or -Part-X or Part X
        filename_only = os.path.basename(filepath)
        part_suffix = ""
        part_match = re.search(r'(Part[\s_-]?\d+)', filename_only, re.IGNORECASE)
        if part_match:
            part_str = part_match.group(1)
            # Normalize part string to _Part_X
            part_num = re.search(r'\d+', part_str).group(0)
            part_suffix = f"_Part_{part_num}"

        final_name = f"{base_name}{part_suffix}.m4b"
        final_name = re.sub(r'_{{2,}}', '_', final_name) # Dedup underscores
        
        new_filepath = os.path.join(AUDIOBOOKS_DIR, final_name)
        
        if filepath != new_filepath:
            if os.path.exists(new_filepath):
                print(f"Target exists: {final_name}. Overwriting...")
                try:
                    os.remove(new_filepath)
                    os.rename(filepath, new_filepath)
                except OSError as e:
                    print(f"Error overwriting: {e}")
            else:
                print(f"Renaming: {filename_only}\n      ->  {final_name}")
                try:
                    os.rename(filepath, new_filepath)
                except OSError as e:
                    print(f"Error renaming: {e}")
        else:
            # print(f"Skipping {filename_only} (Already named correctly)")
            pass

if __name__ == "__main__":
    main()