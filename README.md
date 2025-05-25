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

## Building the Docker Image

To build the Docker image for the server:

1.  Navigate to the root directory of the project (`torrent-bot/`).
2.  Run the build command:

    ```shell
    docker build -t torrent-server-bot -f server/Dockerfile .
    ```
    *   `-t torrent-server-bot`: Tags the image with the name `torrent-server-bot`. You can choose any name.
    *   `-f server/Dockerfile`: Specifies the path to the Dockerfile within the `server` directory.
    *   `.`: Sets the build context to the current directory (the project root).

## Running the Docker Container (Standalone)

Once the image is built, you can run it as a standalone container. You will need to pass sensitive information as environment variables.

```shell
docker run -d \
    -p 5000:5000 \
    -e FLASK_SECRET_KEY="your_very_strong_and_unique_secret_key_here" \
    -e QB_USER="your_qb_username" \
    -e QB_PASS="your_qb_password" \
    -e APP_USERS="user1:yoursecurepassword1,user2:anotherpassword2" \
    -e QB_URL="http://your_qbittorrent_host:port" \
    -e CORS_ORIGINS="http://localhost:3000,chrome-extension://your_extension_id_here" \
    # Non-sensitive environment variables are set in the Dockerfile or have defaults
    --name my-torrent-server \
    torrent-server-bot
```

*   `-d`: Runs the container in detached mode.
*   `-p 5000:5000`: Maps port 5000 on the host to port 5000 in the container.
*   `-e VARIABLE_NAME="value"`: Sets an environment variable.
*   `--name my-torrent-server`: Assigns a name to the running container.
*   `torrent-server-bot`: The name of the image you built.

### Environment Variables to Set at Runtime

The following environment variables **must** be set when running the container:

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
