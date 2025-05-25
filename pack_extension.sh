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
  echo "Usage: ./pack_extension.sh <your_server_url> (e.g., https://yourserver.com)"
  exit 1
fi

SERVER_URL=$1
echo_green "Using Server URL: $SERVER_URL"

# 0. Clean up old build and package directories
echo_yellow "Cleaning up old directories..."
rm -rf "$BUILD_DIR"
rm -rf "$PACKAGE_DIR"
mkdir -p "$BUILD_DIR"
mkdir -p "$PACKAGE_DIR"

# 1. Copy source files to a temporary build location
echo_yellow "Copying source files to build directory..."
cp -r "$SOURCE_DIR/"* "$BUILD_DIR/"

# 2. Replace placeholder with the actual server URL
echo_yellow "Replacing server URL placeholder in specified files..."
for FILE_BASENAME in "${FILES_TO_REPLACE_PLACEHOLDER[@]}"; do
  FILE_PATH="$BUILD_DIR/$FILE_BASENAME"
  if [ -f "$FILE_PATH" ]; then
    echo "Updating $FILE_PATH..."
    sed "s|$PLACEHOLDER|$SERVER_URL|g" "$FILE_PATH" > "${FILE_PATH}.tmp" && mv "${FILE_PATH}.tmp" "$FILE_PATH"
  else
    echo_red "Warning: File $FILE_PATH not found for placeholder replacement."
  fi
done

# 3. Create ZIP packages

# Extract version using a two-step grep and sed for better compatibility
VERSION_LINE=$(grep '"version"' "$BUILD_DIR/manifest.json" | head -n 1) 
VERSION=$(echo "$VERSION_LINE" | sed -n 's/.*"version":[[:space:]]*"\([^\"]*\)".*/\1/p')

if [ -z "$VERSION" ]; then
    echo_red "Warning: Could not determine extension version from manifest.json. Using 'unknown_version'."
    VERSION="unknown_version"
fi

echo_green "Detected version: $VERSION"

ZIP_FILENAME_BASE="${EXTENSION_NAME}_v${VERSION}"

# Package for Firefox
FIREFOX_ZIP="${PACKAGE_DIR}/${ZIP_FILENAME_BASE}_firefox.zip"
echo_yellow "Packaging for Firefox: $FIREFOX_ZIP ..."
(cd "$BUILD_DIR" && zip -r -q -9 "../$FIREFOX_ZIP" . -x "*.DS_Store" "*/.DS_Store" "*/Thumbs.db" "*LICENSE*")
echo_green "Firefox package created."

# 4. Clean up build directory (optional, uncomment to keep)
echo_yellow "Cleaning up build directory..."
rm -rf "$BUILD_DIR"

echo_green "
Extension packaging complete!
Packages are in: $PACKAGE_DIR
- Firefox/Chrome: $FIREFOX_ZIP
"

exit 0
