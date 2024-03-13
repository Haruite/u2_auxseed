from base64 import b64encode
from hashlib import sha1

from client.btclient import BTClient
from utils.bencoder import bdecode, bencode

from deluge_client import LocalDelugeRPCClient


class Deluge(BTClient):
    def __init__(self, client: LocalDelugeRPCClient):
        self.client = client

    def rename_file(self, torrent_hash: str, old_path: str, new_path: str):
        for file in self.client.core.get_torrent_status(torrent_hash, ['files'])['files']:
            if file['path'] == old_path:
                file_id = file['index']
                self.client.core.rename_files(torrent_id=torrent_hash, filenames=[(file_id, new_path)])
                break

    def rename_folder(self, torrent_hash: str, old_folder: str, new_folder: str):
        self.client.core.rename_folder(torrent_id=torrent_hash, folder=old_folder, new_folder=new_folder)

    def get_hashes(self):
        return set(self.client.core.get_session_state())

    def add_torrent(self, torrent_files, save_path, is_paused):
        info_hash = sha1(bencode(bdecode(torrent_files)[b'info'])).hexdigest()
        self.client.core.add_torrent_file(
            f'{info_hash}.torrent',
            b64encode(torrent_files),
            {'add_paused': is_paused, 'download_location': save_path}
        )
