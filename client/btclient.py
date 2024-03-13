from abc import ABCMeta, abstractmethod


class BTClient(metaclass=ABCMeta):

    @abstractmethod
    def rename_file(self, torrent_hash: str, old_path: str, new_path: str):
        """
        重命名文件

        Args:
            torrent_hash: 种子 hash
            old_path: 文件 id
            new_path: 新的文件名
        """

    @abstractmethod
    def rename_folder(self, torrent_hash: str, old_folder: str, new_folder: str):
        """
        重命名文件夹

        Args:
            torrent_hash: 种子 hash
            old_folder:
            new_folder:

        """

    def get_hashes(self):
        """
        返回客户端所有种子 hash 的集合
        """

    def add_torrent(self, torrent_files, save_path, is_paused):
        """
        添加种子

        Args:
            torrent_files: 种子文件内容
            save_path: 保存路径
            is_paused: 是否添加后暂停
        """