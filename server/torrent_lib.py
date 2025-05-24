from qbittorrent import Client


class TorrentDB():
    def __init__(self, url, user, passw):
        self.client = Client(url)
        self.client.login(user, passw)

    def get_torrents(self):
        return self.client.torrents()

    def add_download_by_link(self, magnet_link, user):
        return self.client.download_from_link(magnet_link, category=user, savepath="/home/fcstorrent/downloads/qbittorrent/" + user)

    def add_download_by_file(self, file_descr, user):
        return self.client.download_from_file(magnet_link, category=user, savepath="/home/fcstorrent/downloads/qbittorrent/" + user)
