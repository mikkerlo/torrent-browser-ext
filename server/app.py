# server/app.py
from flask import Flask, request, jsonify, session
from torrent_lib import TorrentDB 
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_cors import CORS

# Global store for users, loaded by create_app
users = {}
_torrent_db_instance = None

def get_torrent_db_client():
    global _torrent_db_instance
    if _torrent_db_instance is None:
        # This assumes QB_URL, QB_USER, QB_PASS are set as environment variables
        # and accessible when this function is called.
        # The app factory should ensure these are configured if needed earlier,
        # or they are globally available via os.environ directly.
        _torrent_db_instance = TorrentDB(
            url=os.environ.get('QB_URL', 'http://localhost:8080/'), 
            user=os.environ.get('QB_USER', 'admin'), 
            passw=os.environ.get('QB_PASS', 'adminadmin')
        )
    return _torrent_db_instance

# Login required decorator - needs access to 'users' which is global for now
# or could be passed around if not using a global.
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

def create_app(test_config=None):
    app = Flask(__name__)

    # Load configuration
    if test_config is None:
        # Load instance config, if it exists, when not testing
        app.config.from_mapping(
            SECRET_KEY=os.environ.get('FLASK_SECRET_KEY', 'dev_secret_key'),
            # QB_URL, QB_USER, QB_PASS could be set here if preferred over direct os.environ in get_torrent_db_client
            # For example: QB_URL=os.environ.get('QB_URL'), etc.
        )
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Configure CORS
    raw_cors_origins = os.environ.get('CORS_ORIGINS', '*')
    cors_origins_list = [origin.strip() for origin in raw_cors_origins.split(',')]
    CORS(app, supports_credentials=True, origins=cors_origins_list)
    app.logger.info(f"CORS configured for origins: {cors_origins_list}")

    # Load users from environment variable
    # This part mutates the global 'users' dictionary.
    # For cleaner testing or more complex scenarios, consider attaching 'users' to 'app' 
    # or using a dedicated user management class/object.
    global users
    users.clear() # Clear for potential reloads if app factory is called multiple times (e.g. tests)
    app_users_str = os.environ.get('APP_USERS')
    if app_users_str:
        pairs = app_users_str.split(',')
        for pair in pairs:
            if ':' in pair:
                username, password = pair.split(':', 1)
                users[username.strip()] = generate_password_hash(password.strip())
            else:
                app.logger.warning(f"Skipping malformed user entry '{pair}' in APP_USERS")
    if not users:
        app.logger.warning("No users loaded. APP_USERS env var might be empty or malformed. Example: user1:pass1,user2:pass2")
    
    # Ensure the global torrent_db instance is reset if create_app is called again (e.g. tests)
    global _torrent_db_instance
    _torrent_db_instance = None

    # Register Blueprints or define routes directly
    @app.route('/login', methods=['POST'])
    def login():
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400

        user_hash = users.get(username)
        if not user_hash or not check_password_hash(user_hash, password):
            return jsonify({"error": "Invalid credentials"}), 401

        session['username'] = username
        return jsonify({"message": "Login successful"}), 200

    @app.route('/logout', methods=['POST'])
    @login_required
    def logout():
        session.pop('username', None)
        return jsonify({"message": "Logout successful"}), 200

    @app.route('/status', methods=['GET'])
    @login_required
    def status():
        return jsonify({"message": f"Logged in as {session['username']}"}), 200

    @app.route('/add_torrent_file', methods=['POST'])
    @login_required
    def add_torrent_file_route():
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        file_storage = request.files['file']
        if file_storage.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        authenticated_user = session['username']
        target_user_param = request.form.get('target_user')
        final_user = authenticated_user

        if target_user_param:
            if target_user_param.lower() == 'common':
                final_user = 'common'
            elif target_user_param in users:
                final_user = target_user_param
            else:
                return jsonify({"error": f"Target user '{target_user_param}' does not exist."}), 400
        
        app.logger.info(f"Authenticated user '{authenticated_user}' adding torrent for target user '{final_user}'")

        try:
            db = get_torrent_db_client()
            db.add_download_by_file(file_storage.stream, final_user)
            return jsonify({"message": f"Torrent file from {file_storage.filename} added successfully for user {final_user}"}), 200
        except Exception as e:
            app.logger.error(f"Error adding torrent file: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route('/add_magnet_link', methods=['POST'])
    @login_required
    def add_magnet_link_route():
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        magnet_link = data.get('magnet_link')
        if not magnet_link:
            return jsonify({"error": "Magnet link not provided"}), 400

        authenticated_user = session['username']
        target_user_param = data.get('target_user') # Get from JSON payload
        final_user = authenticated_user

        if target_user_param:
            if target_user_param.lower() == 'common':
                final_user = 'common'
            elif target_user_param in users:
                final_user = target_user_param
            else:
                return jsonify({"error": f"Target user '{target_user_param}' does not exist."}), 400

        app.logger.info(f"Authenticated user '{authenticated_user}' adding torrent for target user '{final_user}'")
        
        try:
            db = get_torrent_db_client()
            db.add_download_by_link(magnet_link, final_user)
            return jsonify({"message": f"Magnet link added successfully for user {final_user}"}), 200
        except Exception as e:
            app.logger.error(f"Error adding magnet link: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    return app

# This part is for running with `python app.py` directly (e.g. local development)
# For production, a WSGI server like Gunicorn will import `create_app()` and call it.
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=int(os.environ.get('FLASK_RUN_PORT', 5000)), debug=True)
