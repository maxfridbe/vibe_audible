import os
import sys
import subprocess
import time
import shutil
from pathlib import Path

# Add parent directory to sys.path to import process_library
current_dir = Path(__file__).parent.resolve()
sys.path.append(str(current_dir.parent))

try:
    import process_library
except ImportError:
    # In the AppImage, process_library might be in the same dir or site-packages
    try:
        import process_library
    except ImportError:
        print("Error: Could not import process_library.")
        sys.exit(1)

def run_command(cmd, check=True, capture_output=False):
    try:
        result = subprocess.run(
            cmd, 
            check=check, 
            text=True, 
            capture_output=capture_output
        )
        return result
    except subprocess.CalledProcessError as e:
        if check:
            raise e
        return e

def main():
    print("----------------------------------------------------------------")
    print("AUDIBLE DOWNLOADER & CONVERTER (AppImage)")
    print("----------------------------------------------------------------")

    # Set up paths
    # In AppImage, we want to write to the current working directory or a specific data dir
    # NOT the internal read-only filesystem.
    cwd = os.getcwd()
    config_dir = os.path.join(cwd, ".audible")
    os.makedirs(config_dir, exist_ok=True)
    
    # Set environment variable for audible-cli
    os.environ["AUDIBLE_CONFIG_DIR"] = config_dir
    os.environ["SUPPRESS_BOLTDB_WARNING"] = "1"

    config_file = os.path.join(config_dir, "config.toml")
    if not os.path.exists(config_file):
        print("Creating initial config...")
        with open(config_file, 'w') as f:
            f.write("# Audible CLI Configuration\n")

    # --- Step 1: Login ---
    print("\n--- STEP 1: INITIALIZE & LOGIN ---")
    
    print("\nPlease enter the profile name you want to use.")
    print("If you have already logged in, enter the same name as before.")
    profile_name = input("Profile Name [default]: ").strip() or "default"

    # Check if profile exists in config
    profile_exists = False
    try:
        with open(config_file, 'r') as f:
            if f"[profile.{profile_name}]" in f.read():
                profile_exists = True
    except FileNotFoundError:
        pass

    if profile_exists:
        print(f"Profile '{profile_name}' found in config. Skipping login.")
    else:
        print(f"Profile '{profile_name}' not found. Starting login process...")
        print("\nPlease enter your country code (us, uk, de, fr, ca, it, au, in, jp, es, br)")
        country_code = input("Country Code [us]: ").strip() or "us"
        
        auth_file = f"{profile_name}.json"
        
        print(f"\nStarting browser login for region: {country_code}")
        print(f"Creating auth file: {auth_file}")
        
        try:
            # We assume 'audible' is in the path (bundled in AppImage)
            cmd = [
                "audible", "manage", "auth-file", "add",
                "--external-login",
                "--country-code", country_code,
                "--auth-file", auth_file
            ]
            run_command(cmd)
            
            print(f"\nLinking profile '{profile_name}' to auth file...")
            cmd = [
                "audible", "manage", "profile", "add",
                "--profile", profile_name,
                "--auth-file", auth_file,
                "--country-code", country_code,
                "--is-primary"
            ]
            run_command(cmd)
            print("Login successful!")
        except subprocess.CalledProcessError:
            print("Error: Login failed.")
            sys.exit(1)

    # --- Step 2: Prepare Library ---
    print("\n--- STEP 2: PREPARING LIBRARY ---")
    
    library_file = "library.json"
    if os.path.exists(library_file):
        print(f"{library_file} found. Skipping export.")
    else:
        print("Exporting library to list...")
        try:
            cmd = [
                "audible", "-P", profile_name, 
                "library", "export", 
                "--format", "json", 
                "--output", library_file
            ]
            run_command(cmd)
        except subprocess.CalledProcessError:
            print("Error: Failed to export library.")
            sys.exit(1)

    # --- Step 3: Process Books ---
    print("\n--- STEP 3: PROCESSING BOOKS ---")
    print("Starting smart download & convert process...")
    
    # Call the processing logic
    # We pass the profile name to the function
    process_library.process_books(profile_name)

    print("\nDONE!")

if __name__ == "__main__":
    main()