#!/bin/bash
# Ensure directory exists
mkdir -p "$AUDIBLE_CONFIG_DIR" 2>/dev/null

echo "----------------------------------------------------------------"
echo "STEP 1: INITIALIZE & LOGIN"
echo "----------------------------------------------------------------"

# Initialize config if missing
if [ ! -f "$AUDIBLE_CONFIG_DIR/config.toml" ]; then
    echo "Creating initial config..."
    echo "# Audible CLI Configuration" > "$AUDIBLE_CONFIG_DIR/config.toml"
    chmod 666 "$AUDIBLE_CONFIG_DIR/config.toml"
fi

# Debug: verify config exists
ls -l "$AUDIBLE_CONFIG_DIR/config.toml"

echo ""
echo "Please enter the profile name you want to use."
echo "If you have already logged in, enter the same name as before."
read -p "Profile Name [default]: " PROFILE_NAME
PROFILE_NAME=${PROFILE_NAME:-default}

# Check if profile exists in config.toml
if grep -q "\[profile.$PROFILE_NAME\]" "$AUDIBLE_CONFIG_DIR/config.toml"; then
    echo "Profile '$PROFILE_NAME' found in config. Skipping login."
else
    echo "Profile '$PROFILE_NAME' not found. Starting login process..."
    
    # Prompt for Country Code
    echo ""
    echo "Please enter your country code (us, uk, de, fr, ca, it, au, in, jp, es, br)"
    read -p "Country Code [us]: " COUNTRY_CODE
    COUNTRY_CODE=${COUNTRY_CODE:-us}
    
    AUTH_FILE="${PROFILE_NAME}.json"
    
    echo ""
    echo "Starting browser login for region: $COUNTRY_CODE"
    echo "Creating auth file: $AUTH_FILE"
    
    # Create the auth file (Interactive Browser Login)
    # We use --debug to see if it helps if it fails
    audible manage auth-file add --external-login --country-code "$COUNTRY_CODE" --auth-file "$AUTH_FILE"
    
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create auth file. Please try again."
        exit 1
    fi
    
    echo ""
    echo "Linking profile '$PROFILE_NAME' to auth file..."
    
    # Create the profile pointing to the auth file AND mark it as primary
    audible manage profile add --profile "$PROFILE_NAME" --auth-file "$AUTH_FILE" --country-code "$COUNTRY_CODE" --is-primary
    
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create profile."
        exit 1
    fi
    
    echo "Login successful!"
fi

echo ""
echo "----------------------------------------------------------------"
echo "STEP 2: PREPARING LIBRARY"
echo "----------------------------------------------------------------"
echo "Checking for existing library export..."
if [ -f "library.json" ]; then
    echo "library.json found. Skipping export."
else
    echo "Exporting library to list..."
    audible -P "$PROFILE_NAME" library export --format json --output library.json
fi

if [ ! -f "library.json" ]; then
    echo "Error: Failed to export library."
    exit 1
fi

echo ""
echo "----------------------------------------------------------------"
echo "STEP 3: PROCESSING BOOKS"
echo "----------------------------------------------------------------"
echo "Starting smart download & convert process..."
echo "Running: python process_library.py \"$PROFILE_NAME\""

python3 /usr/local/bin/process_library.py "$PROFILE_NAME"

echo ""
echo "DONE!"