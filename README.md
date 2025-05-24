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

Once the image is built, you can run it as a standalone container:

```shell
docker run -d \
    -p 5000:5000 \
    -e FLASK_SECRET_KEY="a_very_strong_and_unique_secret_key_here" \
    -e APP_USERS="user1:yoursecurepassword1,user2:anotherpassword2" \
    -e QB_URL="http://your_qbittorrent_host:port" \
    -e QB_USER="your_qb_username" \
    -e QB_PASS="your_qb_password" \
    -e QB_SAVE_PATH_BASE="/downloads/" \
    -e CORS_ORIGINS="http://localhost:3000,chrome-extension://your_extension_id_here" \
    --name my-torrent-server \
    torrent-server-bot
```

*   `-d`: Runs the container in detached mode.
*   `-p 5000:5000`: Maps port 5000 on the host to port 5000 in the container.
*   `--name my-torrent-server`: Assigns a name to the running container.
*   `torrent-server-bot`: The name of the image you built.

### Environment Variables

The following environment variables **must** or **should** be set when running the container:

*   `FLASK_SECRET_KEY`: **Required**. A strong, unique secret key for Flask session management.
*   `APP_USERS`: **Required**. A comma-separated string of `username:password` pairs for users who can log into this API (e.g., `"user1:pass1,user2:pass2"`).
*   `QB_URL`: **Required**. The full URL of your qBittorrent Web UI (e.g., `http://192.168.1.100:8080`).
*   `QB_USER`: **Required**. Username for your qBittorrent Web UI.
*   `QB_PASS`: **Required**. Password for your qBittorrent Web UI.
*   `QB_SAVE_PATH_BASE`: **Required**. The base directory *within your qBittorrent setup* where downloads should be saved (e.g., `/downloads/`). The server will append the username to this path (e.g. `/downloads/user1/`).
*   `CORS_ORIGINS`: **Recommended**. A comma-separated list of origins to allow for CORS (e.g., `"http://localhost:8080,chrome-extension://your_extension_id"`). Defaults to `*` if not set, which is permissive.
*   `GUNICORN_WORKERS` (Optional): Number of Gunicorn worker processes. Defaults to 1 in the image. You can add `-e GUNICORN_WORKERS=2` for example.

## Using Docker Compose

For a more convenient way to manage the container and its configuration, a `docker-compose.yml` file is provided.

1.  **Create a `.env` file** in the project root (`torrent-bot/`) to store your environment variables. **Do not commit this file to Git if it contains sensitive credentials.** Add `.env` to your `.gitignore` file (it's already there in the provided one).

    Example `.env` file content:
    ```env
    FLASK_SECRET_KEY=a_very_strong_and_unique_secret_key_for_compose
    APP_USERS=user1:somepass,commonuser:anotherpass
    QB_URL=http://localhost:8080 # Replace with your qBittorrent URL
    QB_USER=qb_admin
    QB_PASS=qb_admin_password
    QB_SAVE_PATH_BASE=/data/torrents/ # Path qBittorrent uses for saving
    CORS_ORIGINS=http://localhost:3000,chrome-extension://your_extension_id

    # Optional Gunicorn workers
    # GUNICORN_WORKERS=2
    ```

2.  **Run Docker Compose:**
    Navigate to the project root (`torrent-bot/`) and run:
    ```shell
    docker-compose up -d
    ```
    This will build the image (if not already built or if changes are detected) and start the `torrent-server` service defined in `docker-compose.yml`.

3.  **To stop the service:**
    ```shell
    docker-compose down
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
