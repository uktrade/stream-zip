from datetime import datetime
from stream_zip import stream_zip


def test_dummy():
    now = datetime.now()

    def files():
        yield 'file-1', now, (b'a', b'b')
        yield 'file-2', now, (b'c', b'd')

    assert b'abcd' == b''.join(stream_zip(files()))
