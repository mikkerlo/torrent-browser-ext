#!/bin/bash

# Script to pack the WebExtension for Firefox and Chrome

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
EXTENSION_NAME="torrent_bot_extension"
SOURCE_DIR="./extension" # Relative to the script's location (root)
BUILD_DIR="./build"
PACKAGE_DIR="./packages"

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

BROWSERS_TO_BUILD=("firefox" "chrome")

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
