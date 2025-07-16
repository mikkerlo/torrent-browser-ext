# Torrent Server Bot

This project provides a Flask-based web server that acts as an API intermediary to a qBittorrent client. It allows authenticated users to add torrent files or magnet links to a qBittorrent instance via a REST API. The server is designed to be run as a Docker container.

## Prerequisites

*   Docker installed and running.
*   Docker Compose installed (for using `docker-compose.yml`).
*   A running qBittorrent instance accessible from where this server will run.

## Project Structure

The main application code resides in the `server/` directory:

```
torrent-bot/
├── server/
│   ├── __init__.py         # Makes 'server' a Python package
│   ├── app.py              # Flask application (using app factory)
│   ├── torrent_lib.py      # Library for qBittorrent interaction
│   ├── Dockerfile          # Instructions to build the Docker image
│   ├── requirements.txt    # Python dependencies
│   └── tests/              # Pytest tests for the server
│       ├── __init__.py
│       └── test_server.py
├── .dockerignore           # Specifies files to ignore during Docker build
├── .gitignore              # Specifies intentionally untracked files for Git
├── docker-compose.yml      # Docker Compose configuration
├── README.md               # This file
└── ... (other git files, conftest.py)
```

## Browser Extension

This project also includes a browser extension designed to work with the Torrent Server Bot API. The extension allows users to easily send magnet links or .torrent files to their qBittorrent client via the server.

### Extension Features

*   **Login/Logout:** Authenticates with the Torrent Server Bot.
*   **Magnet Link Handling:** Intercepts clicks on magnet links and sends them to the server.
*   **.torrent File Handling:** Automatically detects downloads of .torrent files and uploads them to the server.
*   **User Preferences:** Allows enabling/disabling magnet link and .torrent file handling, and an option to remove .torrent files after successful upload.
*   **Notifications:** Provides on-page and browser notifications for actions.
*   **Cross-browser Compatibility:** Supports both Firefox and Google Chrome.

### Extension Structure

The extension source files are located in the `extension/` directory:

```
extension/
├── background.js                 # Service worker / background script for core logic
├── content.js                    # Injects into web pages to handle magnet links
├── icons/
│   ├── logo.png                  # Extension icon
│   └── logo.svg                  # Extension icon (source)
├── lib/
│   └── browser-polyfill.js       # Polyfill for browser.* APIs (for Chrome compatibility)
├── manifest_chrome.json          # Manifest file for Google Chrome
├── manifest_firefox.json         # Manifest file for Firefox
├── popup.css                     # Styles for the popup UI
├── popup.html                    # HTML structure for the popup UI
├── popup.js                      # JavaScript logic for the popup UI
```

### Building the Extension

The extension needs to be packaged into a ZIP file for installation in browsers. A shell script `pack_extension.sh` is provided for this purpose.

**Prerequisites:**

*   A Unix-like environment with `bash`, `zip`, `sed`, `grep`. (For Windows, use WSL or Git Bash).

**Build Steps:**

1.  **Navigate to the project root directory** (`torrent-bot/`).
2.  **Make the script executable** (if not already):
    ```shell
    chmod +x pack_extension.sh
    ```
3.  **Run the script:**
    ```shell
    ./pack_extension.sh
    ```
    The script will automatically build packages for both Firefox and Chrome.

4.  **Output:**
    The packaged extensions will be placed in the `packages/` directory (e.g., `packages/torrent_bot_extension_v1.1_chrome.zip`). The version number is extracted from the corresponding manifest file during the build process.

### Installing the Extension

After building the extension, you can install it in your browser.

**For Firefox:**

1.  Open Firefox and navigate to `about:addons`.
2.  Click the gear icon on the right side of "Manage Your Extensions".
3.  Select "Install Add-on From File...".
4.  Browse to the `packages/` directory in your project and select the Firefox ZIP file (e.g., `torrent_bot_extension_vX.Y_firefox.zip`).
5.  Follow the prompts to install.

**For Google Chrome:**

1.  Open Chrome and navigate to `chrome://extensions`.
2.  Enable "Developer mode" using the toggle switch in the top right corner.
3.  Click the "Load unpacked" button.
4.  Navigate to your project directory and select the `extension/` folder from your **build directory** (e.g., `torrent-bot/build/` after running the pack script, specifically the contents that were prepared for Chrome *before* zipping). **Alternatively, and often easier for distribution, you can drag and drop the generated `.zip` file (e.g., `torrent_bot_extension_vX.Y_chrome.zip`) from the `packages/` directory directly onto the `chrome://extensions` page.** Chrome will ask if you want to add it.

    *(Note: For Chrome, if loading unpacked, the `build/` directory content varies depending on which browser was built last by `pack_extension.sh`. It's generally more reliable for Chrome to use the packaged `.zip` file or to ensure the `build/` directory contains the Chrome-specific manifest when loading unpacked.)*

## Docker Image Information

The application's Docker image is hosted on GitHub Container Registry (GHCR).

*   **Image location:** `ghcr.io/mikkerlo/torrent-browser-ext:master`

This image is typically updated automatically by the GitHub Actions workflow in this repository whenever changes are pushed to the `master` branch.

## Running the Server

You can run the server using Docker. The recommended method is with Docker Compose, which uses the pre-built image from GHCR.

### Option 1: Running with Docker Compose (Recommended - Uses Pre-built Image)

The `docker-compose.yml` file in the project root is configured to use the pre-built image `ghcr.io/mikkerlo/torrent-browser-ext:master`.

1.  **Configure Environment Variables:**
    You still need to provide runtime environment variables for secrets and specific configurations.
    The `docker-compose.yml` file is set up to facilitate this. You have two main options:

    *   **A: Edit `docker-compose.yml` directly:**
        You can uncomment and set the variables directly in the `environment` section of the `server` service in `docker-compose.yml`.
        ```yaml
        # c:\Users\mikkerlo\Documents\torrent-bot\docker-compose.yml
        services:
          server:
            image: ghcr.io/mikkerlo/torrent-browser-ext:master
            ports:
              - "5000:5000"
            environment:
              FLASK_SECRET_KEY: "your_very_strong_and_unique_secret_key"
              QB_USER: "your_qb_username"
              QB_PASS: "your_qb_password"
              APP_USERS: "user1:pass1,user2:pass2"
              QB_URL: "http://localhost:8080/" # Or your qBittorrent instance URL
              CORS_ORIGINS: "*"
              FLASK_APP: "app:create_app"
              FLASK_RUN_HOST: "0.0.0.0"
              FLASK_RUN_PORT: "5000"
            # ...
        ```

    *   **B: Use a `.env` file (More Secure for Secrets):**
        Create a file named `.env` in the `server` directory (`c:\Users\mikkerlo\Documents\torrent-bot\server\.env`).
        **Add `server/.env` to your `.gitignore` file to prevent committing secrets.**

        Example `server/.env` file content:
        ```env
        FLASK_SECRET_KEY='your_very_strong_and_unique_secret_key_for_compose'
        APP_USERS='user1:somepass,commonuser:anotherpass'
        QB_URL='http://localhost:8080' # Replace with your qBittorrent URL
        QB_USER='qb_admin'
        QB_PASS='qb_admin_password'
        # CORS_ORIGINS='http://localhost:3000,chrome-extension://your_extension_id' # Optional, defaults to *
        ```
        Then, ensure the `env_file` section is active (uncommented) in your `docker-compose.yml`:
        ```yaml
        # c:\Users\mikkerlo\Documents\torrent-bot\docker-compose.yml
        services:
          server:
            image: ghcr.io/mikkerlo/torrent-browser-ext:master
            # ...
            # To use an environment file, uncomment the line below if it isn't already
            env_file:
              - ./server/.env
            # ...
        ```

2.  **Run Docker Compose:**
    Navigate to the project root (`c:\Users\mikkerlo\Documents\torrent-bot\`) and run:
    ```shell
    docker-compose up -d
    ```
    This will pull the `ghcr.io/mikkerlo/torrent-browser-ext:master` image (if not already present locally) and start the `server` service with your configured environment variables.

3.  **To stop the service:**
    ```shell
    docker-compose down
    ```

### Option 2: Running the Docker Container Standalone (Using Pre-built Image)

If you prefer not to use Docker Compose, you can run the pre-built image directly:

```shell
docker run -d \
    -p 5000:5000 \
    -e FLASK_SECRET_KEY="your_very_strong_and_unique_secret_key_here" \
    -e QB_USER="your_qb_username" \
    -e QB_PASS="your_qb_password" \
    -e APP_USERS="user1:yoursecurepassword1,user2:anotherpassword2" \
    -e QB_URL="http://your_qbittorrent_host:port" \
    -e CORS_ORIGINS="http://localhost:3000,chrome-extension://your_extension_id_here" \
    --name my-torrent-server \
    ghcr.io/mikkerlo/torrent-browser-ext:master
```

*   Replace placeholders like `your_very_strong_and_unique_secret_key_here` with actual values.
*   Note that the image name at the end is now `ghcr.io/mikkerlo/torrent-browser-ext:master`.

### Building the Docker Image Locally (Development/Alternative)

If you need to build the image locally (e.g., for development or if you can't access GHCR), you can still do so. The `Dockerfile` is located in the `server/` directory.

1.  Navigate to the root directory of the project (`torrent-bot/`).
2.  Run the build command:

    ```shell
    docker build -t your-custom-tag-name -f server/Dockerfile .
    ```
    *   `-t your-custom-tag-name`: Tags the image with a name of your choice.
    *   `-f server/Dockerfile`: Specifies the path to the Dockerfile.
    *   `.`: Sets the build context to the current directory.

    If you build locally with a custom tag, you would then modify the `image` field in `docker-compose.yml` to `your-custom-tag-name` or use `your-custom-tag-name` in the `docker run` command if running standalone.

### Environment Variables to Set at Runtime

Regardless of how you run the container (Docker Compose or standalone), the following environment variables **must** be set:

*   `FLASK_SECRET_KEY`: **Required**. A strong, unique secret key for Flask session management.
*   `QB_USER`: **Required**. Username for your qBittorrent Web UI.
*   `QB_PASS`: **Required**. Password for your qBittorrent Web UI.
*   `APP_USERS`: **Required**. A comma-separated string of `username:password` pairs for users who can log into this API (e.g., `"user1:pass1,user2:pass2"`).

The following environment variables have defaults in the `Dockerfile` or `docker-compose.yml` but can be overridden:

*   `QB_URL`: Defaults to `http://localhost:8080/`. The full URL of your qBittorrent Web UI.
*   `CORS_ORIGINS`: Defaults to `*`. A comma-separated list of origins to allow for CORS (e.g., `"http://localhost:8080,chrome-extension://your_extension_id"`).
*   `FLASK_APP`: Defaults to `app:create_app`.
*   `FLASK_RUN_HOST`: Defaults to `0.0.0.0`.
*   `FLASK_RUN_PORT`: Defaults to `5000`.
*   `GUNICORN_WORKERS` (Optional): Number of Gunicorn worker processes. If not set, Gunicorn's default will be used.

## Using Docker Compose (Recommended)

For a more convenient way to manage the container and its configuration, a `docker-compose.yml` file is provided in the project root.

1.  **Configure Environment Variables:**
    The `docker-compose.yml` file is set up to use environment variables for configuration. You have two main options:

    *   **Option A: Edit `docker-compose.yml` directly (for testing or if not checking in sensitive data):**
        You can uncomment and set the variables directly in the `environment` section of the `server` service in `docker-compose.yml`.

        ```yaml
        # c:\Users\mikkerlo\Documents\torrent-bot\docker-compose.yml
        services:
          server:
            # ...
            environment:
              FLASK_SECRET_KEY: "your_very_strong_and_unique_secret_key"
              QB_USER: "your_qb_username"
              QB_PASS: "your_qb_password"
              APP_USERS: "user1:pass1,user2:pass2"
              QB_URL: "http://localhost:8080/" # Or your qBittorrent instance URL
              CORS_ORIGINS: "*"
              FLASK_APP: "app:create_app"
              FLASK_RUN_HOST: "0.0.0.0"
              FLASK_RUN_PORT: "5000"
            # ...
        ```

    *   **Option B: Use a `.env` file (Recommended for security):**
        Create a file named `.env` in the `server` directory (`c:\Users\mikkerlo\Documents\torrent-bot\server\.env`).
        **Add `server/.env` to your `.gitignore` file to prevent committing secrets.**

        Example `server/.env` file content:
        ```env
        FLASK_SECRET_KEY='your_very_strong_and_unique_secret_key_for_compose'
        APP_USERS='user1:somepass,commonuser:anotherpass'
        QB_URL='http://localhost:8080' # Replace with your qBittorrent URL
        QB_USER='qb_admin'
        QB_PASS='qb_admin_password'
        # CORS_ORIGINS='http://localhost:3000,chrome-extension://your_extension_id' # Optional, defaults to *
        # QB_SAVE_PATH_BASE is not used by the server directly anymore but was part of old config
        ```
        Then, uncomment the `env_file` section in your `docker-compose.yml`:
        ```yaml
        # c:\Users\mikkerlo\Documents\torrent-bot\docker-compose.yml
        services:
          server:
            # ...
            # To use an environment file, uncomment the line below
            env_file:
              - ./server/.env  # Create this file in the server directory to store your secrets
            # ...
        ```

2.  **Run Docker Compose:**
    Navigate to the project root (`c:\Users\mikkerlo\Documents\torrent-bot\`) and run:
    ```shell
    docker-compose up -d
    ```
    This will build the image (if not already built or if changes are detected) and start the `server` service.

3.  **To stop the service:**
    ```shell
    docker-compose down
    ```
    To stop and remove volumes (if any were defined, though not in this setup):
    ```shell
    docker-compose down -v
    ```

## API Endpoints

The server exposes the following main API endpoints (all require authentication via `/login` first):

*   **POST `/login`**:
    *   Payload: `{"username": "your_user", "password": "your_password"}`
    *   Authenticates the user and creates a session.
*   **POST `/logout`**:
    *   Clears the session.
*   **GET `/status`**:
    *   Returns the login status of the current user.
*   **POST `/add_magnet_link`**:
    *   Payload: `{"magnet_link": "magnet:?xt=...", "target_user": "username_or_common" (optional)}`
    *   Adds a torrent using a magnet link. If `target_user` is not provided, it defaults to the authenticated user. `target_user` can be another valid username or "common".
*   **POST `/add_torrent_file`**:
    *   Multipart form data:
        *   `file`: The .torrent file.
        *   `target_user` (optional form field): `username_or_common`.
    *   Adds a torrent using a .torrent file. If `target_user` is not provided, it defaults to the authenticated user.

Refer to `server/app.py` for detailed route definitions.

## Running Tests

Tests are located in `server/tests/` and can be run using `pytest`.

1.  Navigate to the `server/` directory:
    ```shell
    cd server
    ```
2.  Run pytest:
    ```shell
    pytest
    ```
    Ensure you have the necessary Python dependencies installed in your environment if running tests locally outside of Docker (see `server/requirements.txt`). The tests are configured to mock qBittorrent interactions.
