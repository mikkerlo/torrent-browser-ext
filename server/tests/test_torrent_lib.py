import unittest
from unittest.mock import patch, Mock
import requests # Required for requests.exceptions.HTTPError
from server.torrent_lib import TorrentDB

# Define a constant for the base save path to avoid repetition
BASE_SAVE_PATH = "/home/fcstorrent/downloads/qbittorrent/"

class TestTorrentDB(unittest.TestCase):

    def setUp(self):
        # This setup can be used if there's common mock configuration
        # For now, each test will configure its mocks specifically
        pass

    @patch('server.torrent_lib.Client')
    def test_add_download_by_link_retry_success(self, MockClient):
        mock_qb_client = Mock()
        MockClient.return_value = mock_qb_client

        # Simulate 403 error on first call to download_from_link, then success
        mock_qb_client.download_from_link.side_effect = [
            requests.exceptions.HTTPError(response=Mock(status_code=403)),
            "success_value_link"
        ]
        # login is called once in __init__ and once for retry
        mock_qb_client.login.return_value = None 

        db = TorrentDB("http://testurl", "testuser", "testpass")
        result = db.add_download_by_link("magnet:?xt=urn:btih:testlink", "test_user_category")

        self.assertEqual(result, "success_value_link")
        self.assertEqual(mock_qb_client.login.call_count, 2) # Initial login + 1 retry login
        self.assertEqual(mock_qb_client.download_from_link.call_count, 2)
        expected_savepath = BASE_SAVE_PATH + "test_user_category"
        mock_qb_client.download_from_link.assert_any_call("magnet:?xt=urn:btih:testlink", category="test_user_category", savepath=expected_savepath)

    @patch('server.torrent_lib.Client')
    def test_add_download_by_link_non_403_error(self, MockClient):
        mock_qb_client = Mock()
        MockClient.return_value = mock_qb_client

        # Simulate a non-403 HTTPError
        mock_qb_client.download_from_link.side_effect = requests.exceptions.HTTPError(response=Mock(status_code=500))
        mock_qb_client.login.return_value = None

        db = TorrentDB("http://testurl", "testuser", "testpass")
        
        with self.assertRaises(requests.exceptions.HTTPError) as context:
            db.add_download_by_link("magnet:?xt=urn:btih:anotherlink", "test_user_category")
        
        self.assertEqual(context.exception.response.status_code, 500)
        self.assertEqual(mock_qb_client.login.call_count, 1) # Only initial login
        self.assertEqual(mock_qb_client.download_from_link.call_count, 1)

    @patch('server.torrent_lib.Client')
    def test_add_download_by_link_retry_login_fails(self, MockClient):
        mock_qb_client = Mock()
        MockClient.return_value = mock_qb_client

        # Simulate 403 on download, then 403 on re-login attempt
        mock_qb_client.download_from_link.side_effect = requests.exceptions.HTTPError(response=Mock(status_code=403))
        # First login in __init__ is successful, second login (retry) fails
        mock_qb_client.login.side_effect = [
            None, 
            requests.exceptions.HTTPError(response=Mock(status_code=403))
        ]

        db = TorrentDB("http://testurl", "testuser", "testpass")

        with self.assertRaises(requests.exceptions.HTTPError) as context:
            db.add_download_by_link("magnet:?xt=urn:btih:linkfail", "test_user_category")
        
        self.assertEqual(context.exception.response.status_code, 403) # Error from login
        self.assertEqual(mock_qb_client.login.call_count, 2) # Initial + 1 attempt
        self.assertEqual(mock_qb_client.download_from_link.call_count, 1) # Only first attempt

    @patch('server.torrent_lib.Client')
    def test_add_download_by_link_retry_second_download_fails(self, MockClient):
        mock_qb_client = Mock()
        MockClient.return_value = mock_qb_client

        # Simulate 403 on first download, successful re-login, then 403 on second download
        mock_qb_client.download_from_link.side_effect = [
            requests.exceptions.HTTPError(response=Mock(status_code=403)),
            requests.exceptions.HTTPError(response=Mock(status_code=403))
        ]
        mock_qb_client.login.return_value = None # All logins are successful

        db = TorrentDB("http://testurl", "testuser", "testpass")

        with self.assertRaises(requests.exceptions.HTTPError) as context:
            db.add_download_by_link("magnet:?xt=urn:btih:linkfailagain", "test_user_category")
        
        self.assertEqual(context.exception.response.status_code, 403) # Error from second download
        self.assertEqual(mock_qb_client.login.call_count, 2) # Initial + 1 re-login
        self.assertEqual(mock_qb_client.download_from_link.call_count, 2) # Both attempts

    # Tests for add_download_by_file
    @patch('server.torrent_lib.Client')
    def test_add_download_by_file_retry_success(self, MockClient):
        mock_qb_client = Mock()
        MockClient.return_value = mock_qb_client

        mock_qb_client.download_from_file.side_effect = [
            requests.exceptions.HTTPError(response=Mock(status_code=403)),
            "success_value_file"
        ]
        mock_qb_client.login.return_value = None

        db = TorrentDB("http://testurl", "testuser", "testpass")
        mock_file_descriptor = Mock() # Simulate a file descriptor or path
        result = db.add_download_by_file(mock_file_descriptor, "test_user_category_file")

        self.assertEqual(result, "success_value_file")
        self.assertEqual(mock_qb_client.login.call_count, 2)
        self.assertEqual(mock_qb_client.download_from_file.call_count, 2)
        expected_savepath = BASE_SAVE_PATH + "test_user_category_file"
        mock_qb_client.download_from_file.assert_any_call(mock_file_descriptor, category="test_user_category_file", savepath=expected_savepath)

    @patch('server.torrent_lib.Client')
    def test_add_download_by_file_non_403_error(self, MockClient):
        mock_qb_client = Mock()
        MockClient.return_value = mock_qb_client

        mock_qb_client.download_from_file.side_effect = requests.exceptions.HTTPError(response=Mock(status_code=401)) # Unauthorized
        mock_qb_client.login.return_value = None
        
        db = TorrentDB("http://testurl", "testuser", "testpass")
        mock_file_descriptor = Mock()
        
        with self.assertRaises(requests.exceptions.HTTPError) as context:
            db.add_download_by_file(mock_file_descriptor, "test_user_category_file")
            
        self.assertEqual(context.exception.response.status_code, 401)
        self.assertEqual(mock_qb_client.login.call_count, 1)
        self.assertEqual(mock_qb_client.download_from_file.call_count, 1)

    @patch('server.torrent_lib.Client')
    def test_add_download_by_file_retry_login_fails(self, MockClient):
        mock_qb_client = Mock()
        MockClient.return_value = mock_qb_client

        mock_qb_client.download_from_file.side_effect = requests.exceptions.HTTPError(response=Mock(status_code=403))
        mock_qb_client.login.side_effect = [
            None,
            requests.exceptions.HTTPError(response=Mock(status_code=403))
        ]

        db = TorrentDB("http://testurl", "testuser", "testpass")
        mock_file_descriptor = Mock()

        with self.assertRaises(requests.exceptions.HTTPError) as context:
            db.add_download_by_file(mock_file_descriptor, "test_user_category_file")

        self.assertEqual(context.exception.response.status_code, 403) # Error from login
        self.assertEqual(mock_qb_client.login.call_count, 2)
        self.assertEqual(mock_qb_client.download_from_file.call_count, 1)


    @patch('server.torrent_lib.Client')
    def test_add_download_by_file_retry_second_download_fails(self, MockClient):
        mock_qb_client = Mock()
        MockClient.return_value = mock_qb_client

        mock_qb_client.download_from_file.side_effect = [
            requests.exceptions.HTTPError(response=Mock(status_code=403)),
            requests.exceptions.HTTPError(response=Mock(status_code=403))
        ]
        mock_qb_client.login.return_value = None

        db = TorrentDB("http://testurl", "testuser", "testpass")
        mock_file_descriptor = Mock()

        with self.assertRaises(requests.exceptions.HTTPError) as context:
            db.add_download_by_file(mock_file_descriptor, "test_user_category_file")

        self.assertEqual(context.exception.response.status_code, 403) # Error from second download
        self.assertEqual(mock_qb_client.login.call_count, 2)
        self.assertEqual(mock_qb_client.download_from_file.call_count, 2)

if __name__ == '__main__':
    # Create the directory if it doesn't exist before running tests
    # This is more of a convenience for local execution,
    # in a CI environment, the structure should be ensured by the checkout process.
    # import os
    # if not os.path.exists('server/tests'):
    #    os.makedirs('server/tests')
    unittest.main()
