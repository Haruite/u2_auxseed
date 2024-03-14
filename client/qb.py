from client.btclient import BTClient

import qbittorrentapi


class Qbittorrent(BTClient):
    def __init__(self, client: qbittorrentapi.Client):
        self.client = client

    def rename_file(self, torrent_hash, old_path, new_path):
        self.client.torrents_rename_file(torrent_hash=torrent_hash, old_path=old_path, new_path=new_path)

    def rename_folder(self, torrent_hash, old_folder, new_folder):
        try:
            self.client.torrents_rename_folder(torrent_hash, old_path=old_folder, new_path=new_folder)
        except:
            for file in self.client.torrents_files(torrent_hash):
                old_name = file.name
                new_name = old_name.replace(old_folder, new_folder)
                if old_name != new_name:
                    self.client.torrents_rename_file(torrent_hash=torrent_hash, file_id=file.index, new_file_name=new_name)

    def get_hashes(self):
        return {torrent.hash for torrent in self.client.torrents_info()}

    def add_torrent(self, torrent_files, save_path, is_paused):
        self.client.torrents_add(torrent_files=torrent_files, save_path=save_path, is_paused=True)
