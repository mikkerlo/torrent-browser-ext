import pytest
from unittest.mock import patch, Mock, call, MagicMock
import requests  # Required for requests.exceptions.HTTPError
from torrent_lib import TorrentDB  # Adjusted import path

# Define a constant for the base save path to avoid repetition
BASE_SAVE_PATH = "/home/fcstorrent/downloads/qbittorrent/"


@pytest.fixture
def mock_qb_client():
    """
    Provides a fully handcrafted mocked qBittorrent Client instance.
    This mock prevents actual network calls and gives direct control over methods.
    """
    # 1. Create our handcrafted client mock instance FIRST
    the_client_mock = MagicMock()

    # 2. Define its interface with simple MagicMocks for methods used by TorrentDB
    the_client_mock.login = MagicMock(return_value=None)
    the_client_mock.download_from_link = MagicMock(return_value="manual_fixture_dl_link_ok")
    the_client_mock.download_from_file = MagicMock(return_value="manual_fixture_dl_file_ok")
    # Add other methods if TorrentDB uses them, e.g., the_client_mock.torrents = MagicMock(return_value=[])

    # 3. Set up attributes that the real qbittorrent.Client might have, which TorrentDB might access
    #    or that the original Client.__init__ would set (which we are bypassing).
    mock_app_object = Mock(spec_set=['preferences'])
    mock_app_object.preferences = {'mocked_preference': 'value'} # Simulate app preferences
    the_client_mock.app = mock_app_object
    the_client_mock.api_version = "mock_api_vXYZ"  # Simulate version attributes
    the_client_mock.app_version = "mock_app_vXYZ"

    # 4. Patch the necessary parts: sessions for underlying network calls, and the Client class
    with patch('requests.Session.get') as mock_session_get, \
         patch('requests.Session.post') as mock_session_post, \
         patch('torrent_lib.Client') as MockQBittorrentClientClass:  # Patching torrent_lib.Client

        # 5. Make the patched Client class return our handcrafted mock when instantiated
        MockQBittorrentClientClass.return_value = the_client_mock

        # 6. Configure session mocks to catch any network calls if parts of the original
        #    qbittorrent.Client.__init__ were to run.
        mock_prefs_response = Mock()
        mock_prefs_response.status_code = 200
        mock_prefs_response.json.return_value = {'mocked_preference': 'value'}
        mock_prefs_response.text = "mocked text"
        mock_session_get.return_value = mock_prefs_response

        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.text = "Ok."
        mock_session_post.return_value = mock_login_response
        
        # 7. Yield the handcrafted mock. This is what tests will receive as 'mock_qb_client'.
        yield the_client_mock


def test_add_download_by_link_retry_success(mock_qb_client):
    # Simulate 403 error on first call to download_from_link, then success
    mock_qb_client.download_from_link.side_effect = [
        requests.exceptions.HTTPError(response=Mock(status_code=403)),
        "success_value_link"
    ]

    db = TorrentDB("http://testurl", "testuser", "testpass")
    result = db.add_download_by_link("magnet:?xt=urn:btih:testlink", "test_user_category")

    assert result == "success_value_link"
    # Initial login in TorrentDB.__init__ + 1 retry login
    assert mock_qb_client.login.call_count == 2
    assert mock_qb_client.download_from_link.call_count == 2
    expected_savepath = BASE_SAVE_PATH + "test_user_category"
    # Using call_args_list to check arguments of both calls
    calls = mock_qb_client.download_from_link.call_args_list
    assert calls[0] == call("magnet:?xt=urn:btih:testlink", category="test_user_category", savepath=expected_savepath)
    assert calls[1] == call("magnet:?xt=urn:btih:testlink", category="test_user_category", savepath=expected_savepath)


def test_add_download_by_link_non_403_error(mock_qb_client):
    # Simulate a non-403 HTTPError
    mock_qb_client.download_from_link.side_effect = requests.exceptions.HTTPError(response=Mock(status_code=500))

    db = TorrentDB("http://testurl", "testuser", "testpass")

    with pytest.raises(requests.exceptions.HTTPError) as excinfo:
        db.add_download_by_link("magnet:?xt=urn:btih:anotherlink", "test_user_category")

    assert excinfo.value.response.status_code == 500
    assert mock_qb_client.login.call_count == 1  # Only initial login
    assert mock_qb_client.download_from_link.call_count == 1


def test_add_download_by_link_retry_login_fails(mock_qb_client):
    # Simulate 403 on download, then 403 on re-login attempt
    mock_qb_client.download_from_link.side_effect = requests.exceptions.HTTPError(response=Mock(status_code=403))
    # First login in __init__ is successful (uses fixture default), second login (retry) fails
    # We need to override the fixture's login mock for this specific scenario AFTER the first call.
    # The first call happens during TorrentDB init.
    
    # Configure login side_effect: 
    # 1st call (in __init__): fixture default (None)
    # 2nd call (retry): HTTPError
    # To achieve this, we can't just set side_effect before __init__ for both.
    # Instead, let initial login use fixture's default. Then, for the retry, make it fail.
    # This requires a bit more finesse or breaking down the TorrentDB init from the action.
    # For simplicity here, we'll set a side_effect list that covers both.
    mock_qb_client.login.side_effect = [
        None,  # For __init__ call
        requests.exceptions.HTTPError(response=Mock(status_code=403))  # For retry call
    ]

    db = TorrentDB("http://testurl", "testuser", "testpass")

    with pytest.raises(requests.exceptions.HTTPError) as excinfo:
        db.add_download_by_link("magnet:?xt=urn:btih:linkfail", "test_user_category")

    assert excinfo.value.response.status_code == 403  # Error from login
    assert mock_qb_client.login.call_count == 2  # Initial + 1 attempt
    assert mock_qb_client.download_from_link.call_count == 1  # Only first attempt


def test_add_download_by_link_retry_second_download_fails(mock_qb_client):
    # Simulate 403 on first download, successful re-login, then 403 on second download
    mock_qb_client.download_from_link.side_effect = [
        requests.exceptions.HTTPError(response=Mock(status_code=403)),
        requests.exceptions.HTTPError(response=Mock(status_code=403))
    ]

    db = TorrentDB("http://testurl", "testuser", "testpass")

    with pytest.raises(requests.exceptions.HTTPError) as excinfo:
        db.add_download_by_link("magnet:?xt=urn:btih:linkfailagain", "test_user_category")

    assert excinfo.value.response.status_code == 403  # Error from second download
    assert mock_qb_client.login.call_count == 2  # Initial + 1 re-login
    assert mock_qb_client.download_from_link.call_count == 2  # Both attempts


# Tests for add_download_by_file
def test_add_download_by_file_retry_success(mock_qb_client):
    mock_qb_client.download_from_file.side_effect = [
        requests.exceptions.HTTPError(response=Mock(status_code=403)),
        "success_value_file"
    ]

    db = TorrentDB("http://testurl", "testuser", "testpass")
    mock_file_descriptor = Mock()  # Simulate a file descriptor or path
    result = db.add_download_by_file(mock_file_descriptor, "test_user_category_file")

    assert result == "success_value_file"
    assert mock_qb_client.login.call_count == 2
    assert mock_qb_client.download_from_file.call_count == 2
    expected_savepath = BASE_SAVE_PATH + "test_user_category_file"
    calls = mock_qb_client.download_from_file.call_args_list
    assert calls[0] == call(mock_file_descriptor, category="test_user_category_file", savepath=expected_savepath)
    assert calls[1] == call(mock_file_descriptor, category="test_user_category_file", savepath=expected_savepath)


def test_add_download_by_file_non_403_error(mock_qb_client):


    mock_qb_client.download_from_file.side_effect = requests.exceptions.HTTPError(response=Mock(status_code=401))  # Unauthorized

    db = TorrentDB("http://testurl", "testuser", "testpass")
    mock_file_descriptor = Mock() # Simulate a file descriptor or path

    with pytest.raises(requests.exceptions.HTTPError) as excinfo:
        db.add_download_by_file(mock_file_descriptor, "test_user_category_file")
    assert excinfo.value.response.status_code == 401
    assert mock_qb_client.login.call_count == 1
    assert mock_qb_client.download_from_file.call_count == 1


def test_add_download_by_file_retry_login_fails(mock_qb_client):
    mock_qb_client.download_from_file.side_effect = requests.exceptions.HTTPError(response=Mock(status_code=403))
    mock_qb_client.login.side_effect = [
        None, # Initial __init__ login
        requests.exceptions.HTTPError(response=Mock(status_code=403)) # Retry login
    ]

    db = TorrentDB("http://testurl", "testuser", "testpass")
    mock_file_descriptor = Mock()

    with pytest.raises(requests.exceptions.HTTPError) as excinfo:
        db.add_download_by_file(mock_file_descriptor, "test_user_category_file")

    assert excinfo.value.response.status_code == 403  # Error from login
    assert mock_qb_client.login.call_count == 2
    assert mock_qb_client.download_from_file.call_count == 1


def test_add_download_by_file_retry_second_download_fails(mock_qb_client):
    mock_qb_client.download_from_file.side_effect = [
        requests.exceptions.HTTPError(response=Mock(status_code=403)),
        requests.exceptions.HTTPError(response=Mock(status_code=403))
    ]

    db = TorrentDB("http://testurl", "testuser", "testpass")
    mock_file_descriptor = Mock()

    with pytest.raises(requests.exceptions.HTTPError) as excinfo:
        db.add_download_by_file(mock_file_descriptor, "test_user_category_file")

    assert excinfo.value.response.status_code == 403  # Error from second download
    assert mock_qb_client.login.call_count == 2
    assert mock_qb_client.download_from_file.call_count == 2
