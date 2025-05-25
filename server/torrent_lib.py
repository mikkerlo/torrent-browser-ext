import requests
from qbittorrent import Client


class TorrentDB():
    def __init__(self, url, user, passw):
        self.url = url
        self.user = user
        self.passw = passw
        self.client = Client(self.url)
        self.client.login(self.user, self.passw)

    def get_torrents(self):
        return self.client.torrents()

    @staticmethod
    def gen_savepath(username):
        return "/home/fcstorrent/downloads/qbittorrent/" + username

    def _execute_with_retry(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                self.client.login(self.user, self.passw)
                return func(*args, **kwargs)
            else:
                raise

    def add_download_by_link(self, magnet_link, user):
        return self._execute_with_retry(
            self.client.download_from_link,
            magnet_link,
            category=user,
            savepath=self.gen_savepath(user)
        )

    def add_download_by_file(self, file_descr, user):
        return self._execute_with_retry(
            self.client.download_from_file,
            file_descr,
            category=user,
            savepath=self.gen_savepath(user)
        )
