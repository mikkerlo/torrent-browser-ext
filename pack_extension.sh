#!/bin/bash

# Script to pack the WebExtension for Firefox and Chrome

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
EXTENSION_NAME="torrent_bot_extension"
SOURCE_DIR="./extension" # Relative to the script's location (root)
BUILD_DIR="./build"
PACKAGE_DIR="./packages"

# Files to replace placeholder in
FILES_TO_REPLACE_PLACEHOLDER=(
  "background.js"
  "popup.js"
)
PLACEHOLDER="__SERVER_URL_PLACEHOLDER__"

# --- Helper Functions ---
echo_green() {
  echo -e "\033[0;32m$1\033[0m"
}
echo_red() {
  echo -e "\033[0;31m$1\033[0m"
}
echo_yellow() {
  echo -e "\033[0;33m$1\033[0m"
}

# --- Script Start ---

# Check for host argument
if [ -z "$1" ]; then
  echo_red "Error: No server host provided."
  echo "Usage: ./pack_extension.sh <your_server_url> [browser]"
  echo "  [browser] can be 'firefox', 'chrome', or omitted (to build both)."
  echo "  Example (specific): ./pack_extension.sh https://yourserver.com firefox"
  echo "  Example (both):   ./pack_extension.sh https://yourserver.com"
  exit 1
fi

SERVER_URL=$1
INPUT_BROWSER=$2

BROWSERS_TO_BUILD=()

if [ -z "$INPUT_BROWSER" ]; then
  echo_green "No browser specified, building for both Firefox and Chrome."
  BROWSERS_TO_BUILD=("firefox" "chrome")
elif [ "$INPUT_BROWSER" == "firefox" ] || [ "$INPUT_BROWSER" == "chrome" ]; then
  echo_green "Targeting Browser: $INPUT_BROWSER"
  BROWSERS_TO_BUILD=("$INPUT_BROWSER")
else
  echo_red "Error: Invalid browser specified. Must be 'firefox', 'chrome', or omitted."
  exit 1
fi

echo_green "Using Server URL: $SERVER_URL"

# 0. Clean up old build and package directories
echo_yellow "Cleaning up old directories..."
rm -rf "$BUILD_DIR"
rm -rf "$PACKAGE_DIR"
mkdir -p "$BUILD_DIR"
mkdir -p "$PACKAGE_DIR"

# --- Packaging Function ---
package_for_browser() {
  local BROWSER_TYPE=$1
  echo_yellow "\nStarting packaging process for $BROWSER_TYPE..."

  # Re-create build dir for a clean state for this browser build
  # (or ensure it's clean if running for multiple browsers sequentially)
  rm -rf "$BUILD_DIR"
  mkdir -p "$BUILD_DIR"

  # 1. Copy source files to a temporary build location
  echo_yellow "Copying source files to build directory for $BROWSER_TYPE..."
  cp -r "$SOURCE_DIR/"* "$BUILD_DIR/"

  # Choose the correct manifest file based on the browser argument
  local MANIFEST_FILE_NAME="manifest_${BROWSER_TYPE}.json"
  local MANIFEST_FILE_PATH_SOURCE="$SOURCE_DIR/$MANIFEST_FILE_NAME"
  local MANIFEST_FILE_PATH_BUILD="$BUILD_DIR/manifest.json" # The extension expects 'manifest.json'

  if [ -f "$MANIFEST_FILE_PATH_SOURCE" ]; then
    echo_yellow "Using manifest for $BROWSER_TYPE: $MANIFEST_FILE_NAME"
    cp "$MANIFEST_FILE_PATH_SOURCE" "$MANIFEST_FILE_PATH_BUILD"
  else
    echo_red "Error: Manifest file $MANIFEST_FILE_PATH_SOURCE not found for $BROWSER_TYPE."
    return 1 # Indicate failure
  fi

  # 2. Replace placeholder with the actual server URL in the build directory files
  echo_yellow "Replacing server URL placeholder for $BROWSER_TYPE..."
  for FILE_BASENAME in "${FILES_TO_REPLACE_PLACEHOLDER[@]}"; do
    local FILE_PATH="$BUILD_DIR/$FILE_BASENAME"
    if [ -f "$FILE_PATH" ]; then
      # echo "Updating $FILE_PATH for $BROWSER_TYPE..." # Can be verbose
      sed "s|$PLACEHOLDER|$SERVER_URL|g" "$FILE_PATH" > "${FILE_PATH}.tmp" && mv "${FILE_PATH}.tmp" "$FILE_PATH"
    else
      echo_red "Warning: File $FILE_PATH not found for placeholder replacement (Browser: $BROWSER_TYPE)."
    fi
  done

  # 3. Create ZIP package for the current browser
  local VERSION_LINE=$(grep '"version"' "$MANIFEST_FILE_PATH_BUILD" | head -n 1)
  local VERSION=$(echo "$VERSION_LINE" | sed -n 's/.*"version":[[:space:]]*"\([^\"]*\)".*/\1/p')

  if [ -z "$VERSION" ]; then
      echo_red "Warning: Could not determine extension version for $BROWSER_TYPE from $MANIFEST_FILE_PATH_BUILD. Using 'unknown_version'."
      VERSION="unknown_version"
  fi
  echo_green "Detected version for $BROWSER_TYPE: $VERSION (from $MANIFEST_FILE_PATH_BUILD)"

  local ZIP_FILENAME_BASE="${EXTENSION_NAME}_v${VERSION}_${BROWSER_TYPE}"
  local TARGET_ZIP="${PACKAGE_DIR}/${ZIP_FILENAME_BASE}.zip"

  echo_yellow "Packaging for $BROWSER_TYPE: $TARGET_ZIP ..."
  (cd "$BUILD_DIR" && zip -r -q -9 "../$TARGET_ZIP" . -x "manifest_firefox.json" "manifest_chrome.json" "*.DS_Store" "*/.DS_Store" "*/Thumbs.db" "*LICENSE*")
  echo_green "$BROWSER_TYPE package created: $TARGET_ZIP"
  
  PACKAGES_CREATED+=("$TARGET_ZIP") # Add to list of created packages
}

# --- Main Script Logic ---

# Initial clean up of package directory (Build dir is cleaned per-browser)
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

PACKAGES_CREATED=() # Array to store names of created packages

for CURRENT_BROWSER_TO_BUILD in "${BROWSERS_TO_BUILD[@]}"; do
  package_for_browser "$CURRENT_BROWSER_TO_BUILD"
  if [ $? -ne 0 ]; then
    echo_red "\nFailed to package for $CURRENT_BROWSER_TO_BUILD. Aborting further builds."
    # Clean up build directory if a build fails mid-way
    rm -rf "$BUILD_DIR"
    exit 1
  fi
done

# 4. Clean up build directory (optional, uncomment to keep for debugging)
echo_yellow "\nCleaning up final build directory..."
rm -rf "$BUILD_DIR"

echo_green "
Extension packaging complete!"
if [ ${#PACKAGES_CREATED[@]} -gt 0 ]; then
  echo_green "Packages are in: $PACKAGE_DIR"
  for PKG_PATH in "${PACKAGES_CREATED[@]}"; do
    echo_green "- $PKG_PATH"
  done
else
  echo_yellow "No packages were created."
fi

exit 0
