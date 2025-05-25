# server/tests/test_server.py
import pytest
import json
import io
import os
from unittest.mock import patch, MagicMock

# If running pytest from INSIDE the 'server' directory:
# 'app' module (app.py) is at the top level relative to test execution path.
from app import create_app 

@pytest.fixture
def app(monkeypatch):
    """Creates and configures a new app instance for each test."""
    monkeypatch.setenv('FLASK_SECRET_KEY', 'test_secret_key_for_server_tests')
    monkeypatch.setenv('APP_USERS', 'testuser:testpass,user2:anotherpass')
    monkeypatch.setenv('CORS_ORIGINS', '*')
    monkeypatch.setenv('QB_URL', 'http://mock.qbittorrent.tests:8080')
    monkeypatch.setenv('QB_USER', 'mockuser_tests')
    monkeypatch.setenv('QB_PASS', 'mockpass_tests')
    monkeypatch.setenv('QB_SAVE_PATH_BASE', '/mock_downloads/')

    # If running pytest from INSIDE the 'server' directory, app.py is a top-level module.
    # The TorrentDB class is imported into app.py's namespace.
    # So, we patch 'app.TorrentDB' where 'app' refers to server/app.py.
    with patch('app.TorrentDB', autospec=True) as MockedTorrentDB:
        mock_db_instance = MagicMock() # This is the mock for the TorrentDB *instance*

        # To store content captured by the side_effect
        # We use a list to allow modification by the nested function (nonlocal-like)
        captured_data = {'file_content': None}

        def add_download_by_file_side_effect(file_stream, user):
            # Read the stream content when the mock is called
            captured_data['file_content'] = file_stream.read()
            # You can perform other actions or return a specific value if the real method does
            return True # Simulate success

        mock_db_instance.add_download_by_file = MagicMock(
            name='add_download_by_file_mock',
            side_effect=add_download_by_file_side_effect
        )
        mock_db_instance.add_download_by_link = MagicMock(name='add_download_by_link_mock')
        
        # The class mock should return our instance mock
        MockedTorrentDB.return_value = mock_db_instance
        
        flask_app = create_app({
            'TESTING': True,
            'SECRET_KEY': 'test_secret_key_for_server_tests_in_config',
        })

        # Attach the mock instance and the captured_data store to the app for easy access in tests
        flask_app.mock_torrent_client = mock_db_instance
        flask_app.captured_torrent_data = captured_data 
        yield flask_app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def mock_torrent_db_from_app(app):
    """Convenience fixture to get the mock TorrentDB instance from the app."""
    return app.mock_torrent_client

# Helper for login
def login_client(client, username, password):
    return client.post('/login', data=json.dumps({
        'username': username,
        'password': password
    }), content_type='application/json')

# ===== Test Cases =====

def test_login_successful(client):
    response = login_client(client, "testuser", "testpass")
    assert response.status_code == 200
    assert b"Login successful" in response.data
    with client.session_transaction() as sess:
        assert sess['username'] == "testuser"

def test_login_nonexistent_user(client):
    response = login_client(client, "nonexistentuser", "wrongpass")
    assert response.status_code == 401
    assert b"Invalid credentials" in response.data

def test_login_wrong_password(client):
    response = login_client(client, "user2", "wrongpass")
    assert response.status_code == 401
    assert b"Invalid credentials" in response.data

def test_logout(client):
    login_client(client, "testuser", "testpass")
    response = client.post('/logout', content_type='application/json')
    assert response.status_code == 200
    assert b"Logout successful" in response.data
    with client.session_transaction() as sess:
        assert 'username' not in sess

def test_status_loggedin(client):
    login_client(client, "testuser", "testpass")
    response = client.get('/status')
    assert response.status_code == 200
    assert b"Logged in as testuser" in response.data

def test_status_loggedout(client):
    response = client.get('/status')
    assert response.status_code == 401
    assert b"Authentication required" in response.data

def test_add_magnet_link_success(client, mock_torrent_db_from_app):
    login_client(client, "testuser", "testpass")
    magnet_link = "magnet:?xt=urn:btih:TESTHASHSERVERTEST"
    response = client.post('/add_magnet_link', data=json.dumps({
        'magnet_link': magnet_link
    }), content_type='application/json')
    assert response.status_code == 200, response.get_data(as_text=True)
    assert b"Magnet link added successfully for user testuser" in response.data
    mock_torrent_db_from_app.add_download_by_link.assert_called_once_with(magnet_link, "testuser")

def test_add_magnet_link_not_logged_in(client, mock_torrent_db_from_app):
    response = client.post('/add_magnet_link', data=json.dumps({
        'magnet_link': "magnet:?xt=urn:btih:TESTHASHSERVERTEST"
    }), content_type='application/json')
    assert response.status_code == 401
    mock_torrent_db_from_app.add_download_by_link.assert_not_called()

def test_add_torrent_file_success(client, mock_torrent_db_from_app):
    login_client(client, "testuser", "testpass")
    file_content = b"test torrent file content for server tests"
    data = {
        'file': (io.BytesIO(file_content), 'test_server.torrent')
    }
    response = client.post('/add_torrent_file', data=data, content_type='multipart/form-data')
    assert response.status_code == 200, response.get_data(as_text=True)
    assert b"Torrent file from test_server.torrent added successfully for user testuser" in response.data
    mock_torrent_db_from_app.add_download_by_file.assert_called_once()
    
    # Verify the arguments passed to the mock (e.g., the user)
    # The first argument to the mock (args[0]) was the stream, which is now consumed by the side_effect.
    # The side_effect function itself doesn't alter what mock.call_args sees for original arguments.
    args_passed_to_mock, _ = mock_torrent_db_from_app.add_download_by_file.call_args
    assert args_passed_to_mock[1] == "testuser" # User is the second argument

    # Retrieve the content captured by the side_effect
    # Access captured_torrent_data from the app fixture
    captured_content = client.application.captured_torrent_data['file_content']
    assert captured_content == file_content

def test_add_torrent_file_not_logged_in(client, mock_torrent_db_from_app):
    data = {
        'file': (io.BytesIO(b"test torrent file content"), 'test.torrent')
    }
    response = client.post('/add_torrent_file', data=data, content_type='multipart/form-data')
    assert response.status_code == 401
    mock_torrent_db_from_app.add_download_by_file.assert_not_called()

def test_add_torrent_file_no_file(client, mock_torrent_db_from_app):
    login_client(client, "testuser", "testpass")
    response = client.post('/add_torrent_file', data={}, content_type='multipart/form-data')
    assert response.status_code == 400
    assert b"No file part" in response.data
    mock_torrent_db_from_app.add_download_by_file.assert_not_called()

# ---- Tests for target_user functionality ----

# Magnet Links with target_user
def test_add_magnet_link_for_common_user(client, mock_torrent_db_from_app):
    login_client(client, "testuser", "testpass") # Authenticated as testuser
    magnet_link = "magnet:?xt=urn:btih:COMMONHASH"
    response = client.post('/add_magnet_link', data=json.dumps({
        'magnet_link': magnet_link,
        'target_user': 'common'
    }), content_type='application/json')
    assert response.status_code == 200, response.get_data(as_text=True)
    assert b"Magnet link added successfully for user common" in response.data
    mock_torrent_db_from_app.add_download_by_link.assert_called_once_with(magnet_link, "common")

def test_add_magnet_link_for_another_existing_user(client, mock_torrent_db_from_app):
    # APP_USERS for tests includes 'testuser' and 'user2'
    login_client(client, "testuser", "testpass") # Authenticated as testuser
    magnet_link = "magnet:?xt=urn:btih:USER2HASH"
    response = client.post('/add_magnet_link', data=json.dumps({
        'magnet_link': magnet_link,
        'target_user': 'user2' 
    }), content_type='application/json')
    assert response.status_code == 200, response.get_data(as_text=True)
    assert b"Magnet link added successfully for user user2" in response.data
    mock_torrent_db_from_app.add_download_by_link.assert_called_once_with(magnet_link, "user2")

def test_add_magnet_link_for_nonexistent_target_user(client, mock_torrent_db_from_app):
    login_client(client, "testuser", "testpass")
    magnet_link = "magnet:?xt=urn:btih:NONEXISTENTHASH"
    response = client.post('/add_magnet_link', data=json.dumps({
        'magnet_link': magnet_link,
        'target_user': 'nonexistenttarget'
    }), content_type='application/json')
    assert response.status_code == 400
    assert b"Target user 'nonexistenttarget' does not exist." in response.data
    mock_torrent_db_from_app.add_download_by_link.assert_not_called()

# Torrent Files with target_user
def test_add_torrent_file_for_common_user(client, mock_torrent_db_from_app):
    login_client(client, "testuser", "testpass")
    file_content = b"common user torrent file"
    data = {
        'file': (io.BytesIO(file_content), 'common.torrent'),
        'target_user': 'common'
    }
    response = client.post('/add_torrent_file', data=data, content_type='multipart/form-data')
    assert response.status_code == 200, response.get_data(as_text=True)
    assert b"Torrent file from common.torrent added successfully for user common" in response.data
    
    mock_torrent_db_from_app.add_download_by_file.assert_called_once()
    args_passed_to_mock, _ = mock_torrent_db_from_app.add_download_by_file.call_args
    assert args_passed_to_mock[1] == "common"
    captured_content = client.application.captured_torrent_data['file_content']
    assert captured_content == file_content

def test_add_torrent_file_for_another_existing_user(client, mock_torrent_db_from_app):
    login_client(client, "testuser", "testpass") # Authenticated as testuser
    file_content = b"user2 torrent file"
    data = {
        'file': (io.BytesIO(file_content), 'user2.torrent'),
        'target_user': 'user2'
    }
    response = client.post('/add_torrent_file', data=data, content_type='multipart/form-data')
    assert response.status_code == 200, response.get_data(as_text=True)
    assert b"Torrent file from user2.torrent added successfully for user user2" in response.data
    
    mock_torrent_db_from_app.add_download_by_file.assert_called_once()
    args_passed_to_mock, _ = mock_torrent_db_from_app.add_download_by_file.call_args
    assert args_passed_to_mock[1] == "user2"
    captured_content = client.application.captured_torrent_data['file_content']
    assert captured_content == file_content

def test_add_torrent_file_for_nonexistent_target_user(client, mock_torrent_db_from_app):
    login_client(client, "testuser", "testpass")
    data = {
        'file': (io.BytesIO(b"nonexistent target file"), 'nonexistent.torrent'),
        'target_user': 'nonexistenttarget'
    }
    response = client.post('/add_torrent_file', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert b"Target user 'nonexistenttarget' does not exist." in response.data
    mock_torrent_db_from_app.add_download_by_file.assert_not_called()
