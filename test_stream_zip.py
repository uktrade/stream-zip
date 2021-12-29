from datetime import datetime
from stream_zip import stream_zip


def test_dummy():
    now = datetime.fromisoformat('2021-01-01 21:01:12')

    def files():
        yield 'file-1', now, (b'a', b'b')
        yield 'file-2', now, (b'c', b'd')

    expected = \
        b'\x50\x4b\x03\x04file-1ab' + \
        b'\x50\x4b\x03\x04file-2cd' + \
        b'file-12021-01-01 21:01:12' + \
        b'file-22021-01-01 21:01:12'
    assert expected == b''.join(stream_zip(files()))
