cookies = {
    'nexusphp_u2': ''
}  # type: dict[str, str]
'U2 网站 cookie，用于更新数据(如果选择不更新数据则不需要)'
passkey = ''  # type: str
'U2 网站 passkey，用于下载种子'
proxy = ''  # 'http://127.0.0.1:10809'  # type: str
'网络代理'
headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0'
}  # type: dict[str, str]
'请求头'
src_path = r'/de/dl'  # type: str
'需要辅种的文件所在的文件夹'
host = 'localhost'  # type: str
'qb 所在的主机 ip'
port = 8080  # type: int
'qb webui 端口'
username = ''  # type: str
'qb webui 用户名'
password = ''  # type: str
'qb webui 密码'
duplicate_sizes = (
    1073739776, 1073709056, 1073565696, 4681957376, 1000000000, 1073735680, 2200000000, 2000000000,
    4000000000, 1073731584, 1073737728, 1073727488, 13407799296
)  # type: tuple[int, ...]
'由于某些原因，这些体积对应的种子很多(>5)，因此对于最大文件大小是这些值的种子，将最大文件大小改为第二大的文件大小'
char_map = {
    '?': '？',
    '*': '٭',
    '<': '《',
    '>': '》',
    ':': '：',
    '"': "'",
    '/': '／',
    '\\': '／',
    '|': '￨'
}  # Windows 不支持字符的替换规则
max_missing_size = 1024 ** 3  # type: int
'检测种子缺失部分的最大值，超过这个值不辅种'
torrents_folder = '/de/to'  # type: str
'存放 .torrent 文件的目录,如果这个值为空，则所有辅种的种子从网站下载，否则的话先搜索目录里是否有对应种子然后下载，.torrent 文件可以随意命名'
