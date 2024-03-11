"""
Bencoding implementation written in python3. See https://www.bittorrent.org/beps/bep_0003.html.
For encode/decode a certain object, the decode function takes approximately the same time as the encode function.
"""
from functools import singledispatch
from io import BufferedReader, BytesIO


def bencode(obj):
    fp = []
    write = fp.append

    def _bencode(_obj):
        t = type(_obj)
        if t is int:
            write(b'i')
            write(str(_obj).encode())
            write(b'e')
        elif t is bytes:
            write(str(len(_obj)).encode())
            write(b':')
            write(_obj)
        elif t is str:
            _obj = _obj.encode()
            write(str(len(_obj)).encode())
            write(b':')
            write(_obj)
        elif t is list or t is tuple:
            write(b'l')
            for item in _obj:
                _bencode(item)
            write(b'e')
        elif t is dict:
            write(b'd')
            for key, val in sorted(_obj.items()):
                _bencode(key)
                _bencode(val)
            write(b'e')

    _bencode(obj)
    return b''.join(fp)


def bdecode(_input: bytes | BufferedReader | str):
    """
    Args:
        _input: A bytes object, or IO BufferedReader, or a file path
    Raises:
        AssertionError
        BdecodeError
    """
    _bytes = _input
    if isinstance(_input, BufferedReader):
        _bytes = _input.read()
        assert isinstance(_bytes, bytes), 'Unsupported input stream'
    elif isinstance(_input, str) and len(_input) < 1024:
        with open(_input, 'rb') as _file:
            _bytes = _file.read()
    assert isinstance(_bytes, bytes), "Unsupported input arg"
    fp = BytesIO(_bytes)
    read = fp.read

    def _bdecode():
        c = read(1)
        if c == b'e':
            return StopIteration
        elif c == b'i':
            values = []
            ch = read(1)
            while ch != b'e':
                values.append(ch)
                ch = read(1)
            return int(b''.join(values))
        elif c == b'l':
            result = []
            while True:
                val = _bdecode()
                if val is StopIteration:
                    return result
                result.append(val)
        elif c == b'd':
            result = {}
            while True:
                key = _bdecode()
                if key is StopIteration:
                    return result
                val = _bdecode()
                result[key] = val
        else:
            size = 0
            while c != b':':
                size = size * 10 + (ord(c) - ord('0'))
                c = read(1)
            return read(size)

    return _bdecode()


class BdecodeError(Exception):
    pass


class BencodeError(Exception):
    pass


@singledispatch
def bencode1(obj):
    raise BencodeError(f'Type {type(obj)} of obj <{obj}> is not supported for bencode')


@bencode1.register
def _(obj: bytes):
    return str(len(obj)).encode() + b":" + obj


@bencode1.register
def _(obj: str):
    obj = obj.encode()
    return str(len(obj)).encode() + b":" + obj


@bencode1.register
def _(obj: int):
    return b"i" + str(obj).encode() + b"e"


@bencode1.register
def _(obj: list):
    return b"l" + b"".join(map(bencode1, obj)) + b"e"


@bencode1.register
def _(obj: tuple):
    return b"l" + b"".join(map(bencode1, obj)) + b"e"


@bencode1.register
def _(obj: dict):
    contents = [b'd']
    for k, v in sorted(obj.items()):
        if isinstance(k, (bytes, str)):
            contents.append(bencode1(k))
            contents.append(bencode1(v))
        else:
            raise BencodeError(f'Type {type(k).__name__} of obj <{k}> is not supported for bencode dict obj keys, '
                               f'Only support string or bytes')
    contents.append(b'e')
    return b''.join(contents)


def bdecode1(_input: bytes | BufferedReader | str):
    """
    Args:
        _input: A bytes object, or IO BufferedReader, or a file path
    Raises:
        AssertionError
        BdecodeError
    """
    _bytes = _input
    if isinstance(_input, BufferedReader):
        _bytes = _input.read()
        assert isinstance(_bytes, bytes), 'Unsupported input stream'
    elif isinstance(_input, str) and len(_input) < 1024:
        with open(_input, 'rb') as _file:
            _bytes = _file.read()
    assert isinstance(_bytes, bytes), "Unsupported input arg"

    def _decode_with_start(i):
        """
        Args:
            i(int): the beginning index of object to decode
        """

        c = _bytes[i: i + 1]
        i += 1

        if c == b'i':
            n = _bytes.index(b'e', i)
            return n + 1, int(_bytes[i: n])
        elif c == b'l':
            _list = []
            while _bytes[i: i + 1] != b'e':
                i, _obj = _decode_with_start(i)
                _list.append(_obj)
            return i + 1, _list
        elif c == b'd':
            _dict = {}
            while _bytes[i: i + 1] != b'e':
                i, k = _decode_with_start(i)
                if not isinstance(k, bytes):
                    raise BdecodeError(f"{type(k).__name__} obj {k} can't be used as a dict key")
                i, v = _decode_with_start(i)
                _dict[k] = v
            return i + 1, _dict
        else:
            n = _bytes.index(b':', i)
            bytes_len = int(_bytes[i - 1: n])
            i = n + 1
            return i + bytes_len, _bytes[i: i + bytes_len]

    next_index, obj = _decode_with_start(0)
    total_len = len(_bytes)
    if next_index < total_len:
        raise BdecodeError(f'Decoded {next_index} / {total_len} bytes, some bytes were not decoded')
    return obj
