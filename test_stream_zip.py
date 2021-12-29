from datetime import datetime
from stream_zip import stream_zip


def test_dummy():
    now = datetime.fromisoformat('2021-01-01 21:01:12')

    def files():
        yield 'file-1', now, (b'a', b'b')
        yield 'file-2', now, (b'c', b'd')

    expected = \
        b'PK\x03\x04-\x00\x08\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff' + \
        b'\xff\xff\xff\xff\xff\xff\x06\x00\x05\x00file-1dummyabPK\x03\x04-' + \
        b'\x00\x08\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff' + \
        b'\xff\xff\xff\xff\xff\x06\x00\x05\x00file-2dummycdfile-12021-01-01 21:01:12f' + \
        b'ile-22021-01-01 21:01:12'
    assert expected == b''.join(stream_zip(files()))
