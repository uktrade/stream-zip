from datetime import datetime
from stream_zip import stream_zip


def test_dummy():
    now = datetime.fromisoformat('2021-01-01 21:01:12')

    def files():
        yield 'file-1', now, (b'a', b'b')
        yield 'file-2', now, (b'c', b'd')

    expected = b'file-1abfile-2cdfile-12021-01-01 21:01:12file-22021-01-01 21:01:12'
    assert expected == b''.join(stream_zip(files()))
