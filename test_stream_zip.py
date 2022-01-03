from datetime import datetime
from io import BytesIO
import os
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import pytest
from stream_unzip import stream_unzip

from stream_zip import (
    stream_zip,
    NO_COMPRESSION_64,
    NO_COMPRESSION_32,
    ZIP_64,
    ZIP_32,
    CompressedSizeOverflowError,
    UncompressedSizeOverflowError,
    OffsetOverflowError,
    CentralDirectoryNumberOfEntriesOverflowError,
    NameLengthOverflowError,
)


def test_with_stream_unzip_zip_64():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600

    def files():
        yield 'file-1', now, perms, ZIP_64, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, perms, ZIP_64, (b'c', b'd')

    assert [(b'file-1', None, b'a' * 10000 + b'b' * 10000), (b'file-2', None, b'cd')] == [
        (name, size, b''.join(chunks))
        for name, size, chunks in stream_unzip(stream_zip(files()))
    ]


def test_with_stream_unzip_zip_32():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600

    def files():
        yield 'file-1', now, perms, ZIP_32, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, perms, ZIP_32, (b'c', b'd')

    assert [(b'file-1', None, b'a' * 10000 + b'b' * 10000), (b'file-2', None, b'cd')] == [
        (name, size, b''.join(chunks))
        for name, size, chunks in stream_unzip(stream_zip(files()))
    ]


def test_with_stream_unzip_zip_32_and_zip_64():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600

    def files():
        yield 'file-1', now, perms, ZIP_64, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, perms, ZIP_32, (b'c', b'd')

    assert [(b'file-1', None, b'a' * 10000 + b'b' * 10000), (b'file-2', None, b'cd')] == [
        (name, size, b''.join(chunks))
        for name, size, chunks in stream_unzip(stream_zip(files()))
    ]


def test_with_stream_unzip_with_no_compresion_32():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600

    def files():
        yield 'file-1', now, perms, NO_COMPRESSION_32, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, perms, NO_COMPRESSION_32, (b'c', b'd')

    assert [(b'file-1', 20000, b'a' * 10000 + b'b' * 10000), (b'file-2', 2, b'cd')] == [
        (name, size, b''.join(chunks))
        for name, size, chunks in stream_unzip(stream_zip(files()))
    ]


def test_with_stream_unzip_large_easily_compressible():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600
    batch = b'-' * 500000

    def files():
        def data():
            for i in range(0, 10000):
                yield batch

        yield 'file-1', now, perms, ZIP_64, data()

    num_received = 0
    for name, size, chunks in stream_unzip(stream_zip(files())):
        for chunk in chunks:
            num_received += len(chunk)

    assert num_received == 5000000000


def test_with_stream_unzip_large_not_easily_compressible_with_no_compression_64():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600
    batch = os.urandom(500000)

    def files():
        def data():
            for i in range(0, 10000):
                yield batch

        yield 'file-1', now, perms, ZIP_64, data()
        yield 'file-2', now, perms, NO_COMPRESSION_64, (b'-',)

    num_received = 0
    for name, size, chunks in stream_unzip(stream_zip(files())):
        for chunk in chunks:
            num_received += len(chunk)

    assert num_received == 5000000001


def test_with_stream_unzip_large_not_easily_compressible_with_no_compression_32():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600
    batch = os.urandom(500000)

    def files():
        def data():
            for i in range(0, 10000):
                yield batch

        yield 'file-1', now, perms, ZIP_64, data()
        yield 'file-2', now, perms, NO_COMPRESSION_32, (b'-',)

    with pytest.raises(OffsetOverflowError):
        for name, size, chunks in stream_unzip(stream_zip(files())):
            for chunk in chunks:
                pass


def test_with_stream_unzip_large_not_easily_compressible_with_zip_32():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600
    batch = os.urandom(500000)

    def files():
        def data():
            for i in range(0, 10000):
                yield batch

        yield 'file-1', now, perms, ZIP_64, data()
        yield 'file-2', now, perms, ZIP_32, (b'-',)  # Needs a ZIP_64 offset, but is in ZIP_32 mode

    with pytest.raises(OffsetOverflowError):
        for name, size, chunks in stream_unzip(stream_zip(files())):
            for chunk in chunks:
                pass


def test_zip_overflow_large_not_easily_compressible():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600
    batch = os.urandom(500000)

    def files():
        def data():
            for i in range(0, 10000):
                yield batch

        yield 'file-1', now, perms, ZIP_32, data()

    with pytest.raises(CompressedSizeOverflowError):
        for chunk in stream_zip(files()):
            pass


def test_zip_overflow_large_easily_compressible():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600
    batch = b'-' * 1000000

    def files():
        def data():
            for i in range(0, 10000):
                yield batch

        yield 'file-1', now, perms, ZIP_32, data()

    with pytest.raises(UncompressedSizeOverflowError):
        for chunk in stream_zip(files()):
            pass


def test_with_zipfile_zip_64():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600

    def files():
        yield 'file-1', now, perms, ZIP_64, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, perms, ZIP_64, (b'c', b'd')

    def extracted():
        with ZipFile(BytesIO(b''.join(stream_zip(files())))) as my_zip:
            for my_info in my_zip.infolist():
                with my_zip.open(my_info.filename) as my_file:
                    yield (
                        my_info.filename,
                        my_info.file_size,
                        my_info.date_time,
                        my_info.external_attr,
                        my_file.read(),
                    )

    assert [(
        'file-1',
        20000,
        (2021, 1, 1, 21, 1, 12),
        perms << 16,
        b'a' * 10000 + b'b' * 10000,
    ), (
        'file-2',
        2,
        (2021, 1, 1, 21, 1, 12),
        perms << 16,
        b'cd',
    )] == list(extracted())


def test_with_zipfile_zip_32():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600

    def files():
        yield 'file-1', now, perms, ZIP_32, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, perms, ZIP_32, (b'c', b'd')

    def extracted():
        with ZipFile(BytesIO(b''.join(stream_zip(files())))) as my_zip:
            for my_info in my_zip.infolist():
                with my_zip.open(my_info.filename) as my_file:
                    yield (
                        my_info.filename,
                        my_info.file_size,
                        my_info.date_time,
                        my_info.external_attr,
                        my_file.read(),
                    )

    assert [(
        'file-1',
        20000,
        (2021, 1, 1, 21, 1, 12),
        perms << 16,
        b'a' * 10000 + b'b' * 10000,
    ), (
        'file-2',
        2,
        (2021, 1, 1, 21, 1, 12),
        perms << 16,
        b'cd',
    )] == list(extracted())


def test_with_zipfile_zip_32_and_zip_64():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600

    def files():
        yield 'file-1', now, perms, ZIP_64, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, perms, ZIP_32, (b'c', b'd')

    def extracted():
        with ZipFile(BytesIO(b''.join(stream_zip(files())))) as my_zip:
            for my_info in my_zip.infolist():
                with my_zip.open(my_info.filename) as my_file:
                    yield (
                        my_info.filename,
                        my_info.file_size,
                        my_info.date_time,
                        my_info.external_attr,
                        my_file.read(),
                    )

    assert [(
        'file-1',
        20000,
        (2021, 1, 1, 21, 1, 12),
        perms << 16,
        b'a' * 10000 + b'b' * 10000,
    ), (
        'file-2',
        2,
        (2021, 1, 1, 21, 1, 12),
        perms << 16,
        b'cd',
    )] == list(extracted())


def test_with_zipfile_without_compression():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600

    def files():
        yield 'file-1', now, perms, NO_COMPRESSION_32, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, perms, NO_COMPRESSION_32, (b'c', b'd')

    def extracted():
        with ZipFile(BytesIO(b''.join(stream_zip(files())))) as my_zip:
            for my_info in my_zip.infolist():
                with my_zip.open(my_info.filename) as my_file:
                    yield (
                        my_info.filename,
                        my_info.file_size,
                        my_info.date_time,
                        my_info.external_attr,
                        my_file.read(),
                    )

    assert [(
        'file-1',
        20000,
        (2021, 1, 1, 21, 1, 12),
        perms << 16,
        b'a' * 10000 + b'b' * 10000,
    ), (
        'file-2',
        2,
        (2021, 1, 1, 21, 1, 12),
        perms << 16,
        b'cd',
    )] == list(extracted())


def test_with_zipfile_many_files_zip_64():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600

    def files():
        for i in range(0, 100000):
            yield f'file-{i}', now, perms, ZIP_64, (b'ab',)

    def extracted():
        with ZipFile(BytesIO(b''.join(stream_zip(files())))) as my_zip:
            for my_info in my_zip.infolist():
                with my_zip.open(my_info.filename) as my_file:
                    yield None

    assert len(list(extracted())) == 100000


def test_too_many_files_zip_32():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600

    def files():
        for i in range(0, 100000):
            yield f'file-{i}', now, perms, ZIP_32, (b'ab',)

    with pytest.raises(CentralDirectoryNumberOfEntriesOverflowError):
        for chunk in stream_zip(files()):
            pass


def test_directory_zipfile():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600

    def files():
        yield 'file-1', now, perms, ZIP_64, (b'a' * 10000, b'b' * 10000)
        yield 'file-2/', now, perms, ZIP_64, ()

    def extracted():
        with ZipFile(BytesIO(b''.join(stream_zip(files())))) as my_zip:
            for my_info in my_zip.infolist():
                with my_zip.open(my_info.filename) as my_file:
                    yield (
                        my_info.filename,
                        my_info.file_size,
                        my_info.date_time,
                        my_info.external_attr,
                        my_file.read(),
                    )

    assert [(
        'file-1',
        20000,
        (2021, 1, 1, 21, 1, 12),
        perms << 16,
        b'a' * 10000 + b'b' * 10000,
    ), (
        'file-2/',
        0,
        (2021, 1, 1, 21, 1, 12),
        perms << 16 | 0x10,
        b'',
    )] == list(extracted())


def test_with_unzip_zip64():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600

    def files():
        yield 'file-1', now, perms, ZIP_64, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, perms, ZIP_64, (b'c', b'd')

    def extracted():
        with TemporaryDirectory() as d:
            with open(f'{d}/my.zip', 'wb') as f:
                f.write(b''.join(stream_zip(files())))
            subprocess.run(['unzip', f'{d}/my.zip', '-d', d])

            with open(f'{d}/file-1', 'rb') as f:
                yield 'file-1', f.read()

            with open(f'{d}/file-2', 'rb') as f:
                yield 'file-2', f.read()

    assert [(
        'file-1',
        b'a' * 10000 + b'b' * 10000,
    ), (
        'file-2',
        b'cd',
    )] == list(extracted())


def test_with_unzip_zip_32_and_zip_64():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600

    def files():
        yield 'file-1', now, perms, ZIP_64, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, perms, ZIP_32, (b'c', b'd')

    def extracted():
        with TemporaryDirectory() as d:
            with open(f'{d}/my.zip', 'wb') as f:
                f.write(b''.join(stream_zip(files())))
            subprocess.run(['unzip', f'{d}/my.zip', '-d', d])

            with open(f'{d}/file-1', 'rb') as f:
                yield 'file-1', f.read()

            with open(f'{d}/file-2', 'rb') as f:
                yield 'file-2', f.read()

    assert [(
        'file-1',
        b'a' * 10000 + b'b' * 10000,
    ), (
        'file-2',
        b'cd',
    )] == list(extracted())


def test_with_unzip_with_no_compression_32():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600

    def files():
        yield 'file-1', now, perms, NO_COMPRESSION_32, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, perms, NO_COMPRESSION_32, (b'c', b'd')

    def extracted():
        with TemporaryDirectory() as d:
            with open(f'{d}/my.zip', 'wb') as f:
                f.write(b''.join(stream_zip(files())))
            subprocess.run(['unzip', f'{d}/my.zip', '-d', d])

            with open(f'{d}/file-1', 'rb') as f:
                yield 'file-1', f.read()

            with open(f'{d}/file-2', 'rb') as f:
                yield 'file-2', f.read()

    assert [(
        'file-1',
        b'a' * 10000 + b'b' * 10000,
    ), (
        'file-2',
        b'cd',
    )] == list(extracted())


def test_name_length_overflow():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600

    def files():
        yield '-' * (2**16), now, perms, ZIP_64, (b'ab',)

    with pytest.raises(NameLengthOverflowError):
        for chunk in stream_zip(files()):
            pass


def test_exception_propagates():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600

    def files():
        yield 'file-1', now, perms, ZIP_64, (b'a' * 10000, b'b' * 10000)
        raise Exception('From generator')

    with pytest.raises(Exception,  match='From generator'):
        for chunk in stream_zip(files()):
            pass


def test_chunk_sizes():
    now = datetime.fromisoformat('2021-01-01 21:01:12')
    perms = 0o600

    def files():
        yield 'file-1', now, perms, ZIP_64, (os.urandom(500000),)

    def get_sizes():
        for chunk in stream_zip(files()):
            yield len(chunk)

    sizes = list(get_sizes())
    assert set(sizes[:-1]) == {65536}
    assert sizes[-1] <= 65536
