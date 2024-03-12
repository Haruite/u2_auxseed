import asyncio
import os
import sys
from hashlib import sha1
from typing import Optional

import aiohttp
import qbittorrentapi
from loguru import logger

from config import src_path, duplicate_sizes, host, port, username, password, char_map, max_missing_size, torrents_folder
from utils.bencoder import bdecode, bencode, bdecode1
from web.update import update

logger.add(level='DEBUG', sink=f'{os.getcwd()}/logs/main-{{time}}.log')


class U2AuxSeed:
    def __init__(self):
        self.size_id = update.size_id
        logger.info('欢迎使用 u2_aux_seed 脚本')
        logger.info(
            f'当前可辅种的最新的种子 id 为 {update.newest_tid}, 是否需要更新数据？更新需要一定时间，更新后可辅种最新的种子')
        logger.info(f'输入 y/n')
        if input().lower() == 'y':
            asyncio.run(update.main())
        self.client = qbittorrentapi.Client(host=host, port=port, username=username, password=password)
        self.hashes_in_client = {torrent.hash for torrent in self.client.torrents_info()}
        self.hash_to_fn = {}
        if torrents_folder:
            logger.info(f'开始读取 {torrents_folder} 中的 .torrent 文件...')
            for fn in os.listdir(torrents_folder):
                if fn.endswith('.torrent'):
                    try:
                        info_hash = sha1(bencode(bdecode(os.path.join(torrents_folder, fn))[b'info'])).hexdigest()
                        self.hash_to_fn[info_hash] = fn
                    except:
                        pass
            logger.info(f'所有 .torrent 文件读取完毕')

    @staticmethod
    def get_max_size_in_path(path: str) -> int:
        max_size = 0
        for root, dirs, files in os.walk(path):
            if files:
                for file in files:
                    size = os.path.getsize(os.path.join(root, file))
                    if size > max_size:
                        max_size = size

        if max_size in duplicate_sizes:
            _max_size = max_size
            max_size = 0
            for root, dirs, files in os.walk(path):
                if files:
                    for file in files:
                        size = os.path.getsize(os.path.join(root, file))
                        if size > max_size and size != _max_size:
                            max_size = size
            if max_size == 0:
                max_size = _max_size

        return max_size

    @staticmethod
    def get_file_list_in_folder(path: str) -> list[str]:
        file_list = []
        for root, dirs, files in os.walk(path):
            if files:
                for file in files:
                    file_list.append(os.path.join(root, file))
        return file_list

    @staticmethod
    def decode_name(name: bytes) -> Optional[str]:
        try:
            name = name.decode('utf-8')
            return ''.join(char_map.get(c) or c for c in name)
        except Exception:
            try:
                name = name.decode('ansi')
                return ''.join(char_map.get(c) or c for c in name)
            except Exception:
                pass
        return ''

    def add_torrent_to_single_file(self, path: str, content: bytes, tid: str, info_hash: str):
        try:
            info_dict = bdecode(content)[b'info']
        except:
            info_dict = bdecode1(content)[b'info']
        save_path, filename = os.path.split(path)

        if b'files' not in info_dict:
            name = self.decode_name(info_dict[b'name'])
            if name:
                self.client.torrents_add(torrent_files=content, save_path=save_path, is_paused=True)
                if name != filename:
                    self.client.torrents_rename_file(info_hash, 0, filename)
                logger.info(f'Add torrent {tid}, info_hash {info_hash}')
            else:
                logger.error(f'Cannot add torrent {tid}, because file name cannot be decoded')
        else:
            size1 = os.path.getsize(path)
            size2 = 0
            index = 0
            for i, file in enumerate(info_dict[b'files']):
                if (length := file[b'length']) != size1:
                    size2 += length
                else:
                    index = i
            if size2 <= max_missing_size:
                self.client.torrents_add(torrent_files=content, save_path=save_path, is_paused=True)
                self.client.torrents_rename_file(info_hash, index, filename)
            else:
                logger.error(f'Cannot add torrent {tid}, because missing file size exceeded')

    async def get_torrent_content(self, tid, _hash):
        if fn := self.hash_to_fn.get(_hash):
            with open(os.path.join(torrents_folder, fn), 'rb') as fp:
                content = fp.read()
            logger.info(f'Read .torrent file {fn}')
        else:
            content = await update.fetch_torrent(tid)
            logger.info(f'Downloaded .torrent file of torrent {tid}')
        return content

    async def aux_seed_single_file(self, path: str):
        max_size = os.path.getsize(path)
        if tid_hash := self.size_id.get(str(max_size)):
            if isinstance(tid_hash, str):
                tid_hash = [tid_hash]
                for _tid_hash in tid_hash:
                    tid, _hash = _tid_hash.split('_')
                    if _hash not in self.hashes_in_client:
                        logger.info(f'{path} -> torrent {tid}')
                        content = await self.get_torrent_content(tid, _hash)
                        self.add_torrent_to_single_file(path, content, tid, _hash)
                    else:
                        logger.debug(f'{path} -> torrent {tid} already added')
        else:
            logger.debug(f'{path} cannot be auxseeded')

    def add_torrent_to_multi_file(self, path: str, file_list: list[str], content: bytes, tid: str, _hash: str):
        try:
            info_dict = bdecode(content)[b'info']
        except:
            info_dict = bdecode1(content)[b'info']
        if b'files' not in info_dict:
            size1 = info_dict[b'length']
            size2 = 0
            name = ''
            save_path = ''
            for file in list(file_list):
                if (size := os.path.getsize(file)) == size1:
                    save_path, name = os.path.split(file)
                    file_list.remove(file)
                else:
                    size2 += size
            if size2 > max_missing_size:
                logger.error(f'Cannot add torrent {tid}, because missing file size exceeded')
            else:
                self.client.torrents_add(torrent_files=content, save_path=save_path, is_paused=True)
                logger.info(f'Add torrent {tid} -> {path}')
                if (origin_name := self.decode_name(info_dict[b'name'])) != name:
                    self.client.torrents_rename_file(_hash, 0, name)
                    logger.info(f'Rename file of torrent {tid}, {origin_name} -> {name}')
        else:
            folder_name_map = self.map_torrent_files_to_multi_file(path, self.decode_name(info_dict[b'name']),
                                                                   file_list, info_dict[b'files'])
            base_path = os.path.split(path)[0]
            self.client.torrents_add(torrent_files=content, save_path=base_path, is_paused=True)
            logger.info(f'Add torrent {tid} -> {path}')
            for torrent_folder, local_folder in folder_name_map.items():
                local_folder_path = os.path.join(base_path, local_folder)
                if os.path.exists(local_folder_path) and not os.path.isdir(local_folder_path):
                    try:
                        self.client.torrents_rename_file(torrent_hash=_hash, old_path=torrent_folder, new_path=local_folder)
                        logger.info(f'Rename file of torrent {tid}, {torrent_folder} -> {local_folder}')
                    except Exception as e:
                        logger.error(e)
                else:
                    try:
                        self.client.torrents_rename_folder(torrent_hash=_hash, old_path=torrent_folder, new_path=local_folder)
                        logger.info(f'Rename folder of torrent {tid}, {torrent_folder} -> {local_folder}')
                    except Exception as e:
                        logger.error(e)

    def map_torrent_files_to_multi_file(self, path: str, name: str, file_list: list[str],
                                        torrent_files: list[dict[bytes, int | list[bytes]]]) -> dict[str, str]:
        folder_name_map = {}
        base_path, folder_name = os.path.split(path)

        local_files_size_to_path = {os.path.getsize(path): path for path in file_list}
        torrent_files.sort(key=lambda x: x[b'length'], reverse=True)

        unmatch_size = 0
        for torrent_file in torrent_files:
            if (size := torrent_file[b'length']) not in local_files_size_to_path:
                unmatch_size += size
                if unmatch_size > max_missing_size:
                    return {}

        for torrent_file in torrent_files:
            if (size := torrent_file[b'length']) in local_files_size_to_path:
                if size > 4 * 1024 ** 2:

                    missing_size = 0
                    for _torrent_file in torrent_files:
                        _torrent_file_path = os.path.join(base_path, name, *list(map(self.decode_name, _torrent_file[b'path'])))
                        for key, val in folder_name_map.items():
                            _torrent_file_path = _torrent_file_path.replace(key, val)
                        if _torrent_file_path not in file_list:
                            missing_size += _torrent_file[b'length']
                    if missing_size == unmatch_size:
                        self.remove_files_from_file_list(base_path, name, file_list, torrent_files, folder_name_map)
                        return folder_name_map

                    local_file_path = local_files_size_to_path[size][len(base_path) + 1:]
                    torrent_file_path = os.path.join(name, *list(map(self.decode_name, torrent_file[b'path'])))

                    for key, val in folder_name_map.items():
                        torrent_file_path = torrent_file_path.replace(key, val)

                    if local_file_path == torrent_file_path:
                        continue
                    else:
                        flag = False
                        for _torrent_file in torrent_files:
                            _torrent_file_path = os.path.join(name, *list(map(self.decode_name, _torrent_file[b'path'])))
                            if _torrent_file_path == local_file_path and _torrent_file[b'length'] == size:
                                flag = True
                        if flag:
                            continue

                    separator = '\\' if sys.platform == 'win32' else '/'

                    local_file_path_list = local_file_path.split(separator)
                    torrent_file_path_list = torrent_file_path.split(separator)

                    is_file = True
                    for i in range(min(len(local_file_path_list), len(torrent_file_path_list)) - 1):
                        if local_file_path_list[-1] == torrent_file_path_list[-1]:
                            is_file = False
                            local_file_path_list.pop(-1)
                            torrent_file_path_list.pop(-1)
                        else:
                            break

                    torrent_folder = separator.join(torrent_file_path_list)
                    local_folder = separator.join(local_file_path_list)
                    if not is_file:
                        torrent_folder += separator
                        local_folder += separator

                    if torrent_folder not in folder_name_map:
                        folder_name_map[torrent_folder] = local_folder

        self.remove_files_from_file_list(base_path, name, file_list, torrent_files, folder_name_map)
        return folder_name_map

    def remove_files_from_file_list(self, base_path, name, file_list, torrent_files, folder_name_map):
        for _torrent_file in torrent_files:
            _torrent_file_path = os.path.join(base_path, name, *list(map(self.decode_name, _torrent_file[b'path'])))
            for key, val in folder_name_map.items():
                _torrent_file_path = _torrent_file_path.replace(key, val)
            if _torrent_file_path in file_list:
                file_list.remove(_torrent_file_path)

    async def aux_seed_folder(self, path: str):
        max_size = self.get_max_size_in_path(path)
        if not (tid_hash := self.size_id.get(str(max_size))):
            logger.debug(f'{path} cannot be auxseeded')
            return

        if isinstance(tid_hash, str):
            tid_hash = [tid_hash]
        for _tid_hash in tid_hash:
            file_list = self.get_file_list_in_folder(path)
            tid, _hash = _tid_hash.split('_')
            if _hash in self.hashes_in_client:
                logger.debug(f'{path} -> torrent {tid} already added')
                continue
            content = await self.get_torrent_content(tid, _hash)
            await self.add_torrent_loop(path, file_list, content, tid, _hash)

    async def add_torrent_loop(self, path: str, file_list: list[str], content: bytes, tid: str, _hash: str):
        cur_len = len(file_list)
        while True:
            pre_len = cur_len
            self.add_torrent_to_multi_file(path, file_list, content, tid, _hash)
            if not file_list:
                return
            max_size = max(map(os.path.getsize, file_list))
            tid_hash = self.size_id.get(str(max_size))
            if not tid_hash:
                break
            if isinstance(tid_hash, list):
                tid_hash = tid_hash[0]
            tid, _hash = tid_hash.split('_')
            content = await self.get_torrent_content(tid, _hash)
            cur_len = len(file_list)
            if cur_len == pre_len:
                break

    async def aux_seed(self, path):
        if os.path.isdir(path):
            await self.aux_seed_folder(path)
        else:
            await self.aux_seed_single_file(path)

    async def run(self):
        tasks = []
        for name in os.listdir(src_path):
            path = os.path.join(src_path, name)
            tasks.append(self.aux_seed(path))
        async with aiohttp.ClientSession() as self.session:
            await asyncio.gather(*tasks)
            if update.session:
                await update.session.close()


if __name__ == '__main__':
    asyncio.run(U2AuxSeed().run())
