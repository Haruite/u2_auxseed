from client.btclient import BTClient

import qbittorrentapi


class Qbittorrent(BTClient):
    def __init__(self, client: qbittorrentapi.Client):
        self.client = client

    def rename_file(self, torrent_hash, old_path, new_path):
        self.client.torrents_rename_file(torrent_hash=torrent_hash, old_path=old_path, new_path=new_path)

    def rename_folder(self, torrent_hash, old_folder, new_folder):
        self.client.torrents_rename_folder(torrent_hash, old_path=old_folder, new_path=new_folder)

    def get_hashes(self):
        return {torrent.hash for torrent in self.client.torrents_info()}

    def add_torrent(self, torrent_files, save_path, is_paused):
        self.client.torrents_add(torrent_files=torrent_files, save_path=save_path, is_paused=True)
