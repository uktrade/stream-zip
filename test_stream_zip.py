from datetime import datetime
from io import BytesIO
import os
from zipfile import ZipFile

import pytest
from stream_unzip import stream_unzip

from stream_zip import stream_zip


def test_with_stream_unzip():
    now = datetime.fromisoformat('2021-01-01 21:01:12')

    def files():
        yield 'file-1', now, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, (b'c', b'd')

    assert [(b'file-1', None, b'a' * 10000 + b'b' * 10000), (b'file-2', None, b'cd')] == [
        (name, size, b''.join(chunks))
        for name, size, chunks in stream_unzip(stream_zip(files()))
    ]


def test_with_zipfile():
    now = datetime.fromisoformat('2021-01-01 21:01:12')

    def files():
        yield 'file-1', now, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, (b'c', b'd')

    def extracted():
        with ZipFile(BytesIO(b''.join(stream_zip(files())))) as my_zip:
            for my_info in my_zip.infolist():
                with my_zip.open(my_info.filename) as my_file:
                    yield (
                        my_info.filename,
                        my_info.file_size,
                        my_info.date_time,
                        my_file.read(),
                    )

    assert [(
        'file-1',
        20000,
        (2021, 1, 1, 21, 1, 12),
        b'a' * 10000 + b'b' * 10000,
    ), (
        'file-2',
        2,
        (2021, 1, 1, 21, 1, 12),
        b'cd',
    )] == list(extracted())


def test_exception_propagates():
    now = datetime.fromisoformat('2021-01-01 21:01:12')

    def files():
        yield 'file-1', now, (b'a' * 10000, b'b' * 10000)
        raise Exception('From generator')

    with pytest.raises(Exception,  match='From generator'):
        for chunk in stream_zip(files()):
            pass

def test_chunk_sizes():
    now = datetime.fromisoformat('2021-01-01 21:01:12')

    def files():
        yield 'file-1', now, (os.urandom(1000000),)

    def get_sizes():
        for chunk in stream_zip(files()):
            yield len(chunk)

    sizes = list(get_sizes())
    assert set(sizes[:-1]) == {65536}
    assert sizes[-1] <= 65536
