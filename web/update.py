import asyncio
import json
from hashlib import sha1
from typing import Any

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from config import cookies, passkey, proxy, headers, duplicate_sizes
from utils.bencoder import bencode, bdecode


logger.add(level='DEBUG', sink=f'logs/update-{{time}}.log')


class Update:
    def __init__(self):
        self.base_url = 'https://u2.dmhy.org/torrents.php'
        self.page_index = 0
        self.sem = asyncio.Semaphore(5)
        self.end = False
        self.tid_list = []
        with open('resources/newest_tid', 'r') as f:
            self.newest_tid = int(f.read())
        with open('resources/size_id.json', 'r') as fp:
            self.size_id = json.load(fp)
        self.tid_updated = False
        self.session = None

    async def main(self):
        logger.info('开始更新数据')

        async with aiohttp.ClientSession() as self.session:
            tasks = []
            while not self.end:
                page = await self.fetch_page()
                for tid in self.parse_page(page):
                    tasks.append(self.fetch_torrent(tid))
                self.page_index += 1
            await asyncio.gather(*tasks)
        self.session = None

        with open('resources/size_id.json', 'w') as fp:
            json.dump(self.size_id, fp)

        logger.info(f'更新数据完毕，最新种子 id 为 {self.newest_tid}')

    def parse_page(self, page: str):
        soup = BeautifulSoup(page.replace('\n', ''), 'lxml')
        table = soup.select('table.torrents')[0]
        for tr in table.contents[1:]:
            if 'sticky' not in str(tr):
                tid = int(tr.contents[1].a['href'][15:-6])
                if not self.tid_updated:
                    with open('resources/newest_tid', 'w') as f:
                        f.write(str(tid))
                    self.newest_tid = tid
                    self.tid_updated = True
                if tid == self.newest_tid:
                    self.end = True
                    break
                else:
                    yield tid

    async def fetch_page(self):
        async with self.sem:
            async with self.session.get(
                f'{self.base_url}?page={self.page_index}',
                cookies=cookies,
                headers=headers,
                proxy=proxy
            ) as resp:
                return await resp.text()

    async def fetch_torrent(self, torrent_id):
        download_link = f'https://u2.dmhy.org/download.php?id={torrent_id}&passkey={passkey}&https=1'
        async with self.sem:
            if not self.session:
                self.session = aiohttp.ClientSession()
            async with self.session.get(download_link, headers=headers, proxy=proxy) as resp:
                content = await resp.read()
                self.update_size_id(torrent_id, content)
        return content

    def update_size_id(self, torrent_id: int, content: bytes):
        try:
            torrent = bdecode(content)  # 解码后的种子内容
        except:
            return
        info_dict = torrent[b'info']  # info 字典
        info_hash = sha1(bencode(info_dict)).hexdigest()  # info hash v1
        tid_hash = f'{torrent_id}_{info_hash}'
        max_size = self.get_max_size_in_torrent(info_dict)

        if max_size not in self.size_id:
            self.size_id[max_size] = tid_hash
        else:
            _tid_hash = self.size_id[max_size]
            if isinstance(_tid_hash, str):
                self.size_id[max_size] = [_tid_hash, tid_hash]
            else:
                _tid_hash.append(tid_hash)

    @staticmethod
    def get_max_size_in_torrent(info_dict: dict[bytes, Any]) -> str:
        max_size = 0
        if b'files' not in info_dict:
            max_size = info_dict[b'length']
        else:
            for file in info_dict[b'files']:
                if (size := file[b'length']) > max_size:
                    max_size = size

        if max_size in duplicate_sizes:
            _max_size = max_size
            max_size = 0
            if b'files' in info_dict:
                for file in info_dict[b'files']:
                    if (size := file[b'length']) > max_size and size != _max_size:
                        max_size = size

        return str(max_size)


update = Update()
