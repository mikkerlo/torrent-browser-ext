import requests
from qbittorrent import Client


class TorrentDB():
    def __init__(self, url, user, passw):
        self.url = url # Store url as well for re-login
        self.user = user
        self.passw = passw
        self.client = Client(self.url)
        self.client.login(self.user, self.passw)

    def get_torrents(self):
        return self.client.torrents()

    def add_download_by_link(self, magnet_link, user):
        try:
            return self.client.download_from_link(magnet_link, category=user, savepath="/home/fcstorrent/downloads/qbittorrent/" + user)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                # Re-login
                self.client.login(self.user, self.passw)
                # Retry the download
                return self.client.download_from_link(magnet_link, category=user, savepath="/home/fcstorrent/downloads/qbittorrent/" + user)
            else:
                # If it's not a 403 error, re-raise the exception
                raise

    def add_download_by_file(self, file_descr, user):
        try:
            return self.client.download_from_file(file_descr, category=user, savepath="/home/fcstorrent/downloads/qbittorrent/" + user)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                # Re-login
                self.client.login(self.user, self.passw)
                # Retry the download
                return self.client.download_from_file(file_descr, category=user, savepath="/home/fcstorrent/downloads/qbittorrent/" + user)
            else:
                # If it's not a 403 error, re-raise the exception
                raise
