from datetime import datetime, timezone, timedelta
from io import BytesIO
import asyncio
import contextlib
import os
import platform
import secrets
import stat
import subprocess
import zlib
from tempfile import TemporaryDirectory
from struct import Struct
from zipfile import ZipFile

import pytest
import pyzipper
from stream_unzip import IncorrectAESPasswordError, UnsupportedZip64Error, stream_unzip

from stream_zip import (
    async_stream_zip,
    stream_zip,
    NO_COMPRESSION_64,
    NO_COMPRESSION_32,
    ZIP_AUTO,
    ZIP_64,
    ZIP_32,
    CRC32IntegrityError,
    UncompressedSizeIntegrityError,
    CompressedSizeOverflowError,
    UncompressedSizeOverflowError,
    OffsetOverflowError,
    CentralDirectoryNumberOfEntriesOverflowError,
    CentralDirectorySizeOverflowError,
    NameLengthOverflowError,
)


###################################################################################################
# Utility functions for tests

@contextlib.contextmanager
def cwd(new_dir):
    old_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(old_dir)


def gen_bytes(num):
    chunk = b'-' * 100000
    while num:
        to_yield = min(len(chunk), num)
        num -= to_yield
        yield chunk[:to_yield]


###################################################################################################
# Tests of sync interface: stream_zip

def test_with_stream_unzip_zip_64():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, ZIP_64, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, mode, ZIP_64, (b'c', b'd')

    assert [(b'file-1', None, b'a' * 10000 + b'b' * 10000), (b'file-2', None, b'cd')] == [
        (name, size, b''.join(chunks))
        for name, size, chunks in stream_unzip(stream_zip(files()))
    ]


def test_with_stream_unzip_zip_32():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, ZIP_32, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, mode, ZIP_32, (b'c', b'd')

    assert [(b'file-1', None, b'a' * 10000 + b'b' * 10000), (b'file-2', None, b'cd')] == [
        (name, size, b''.join(chunks))
        for name, size, chunks in stream_unzip(stream_zip(files()), allow_zip64=False)
    ]


def test_with_stream_unzip_zip_32_and_zip_64():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, ZIP_64, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, mode, ZIP_32, (b'c', b'd')

    assert [(b'file-1', None, b'a' * 10000 + b'b' * 10000), (b'file-2', None, b'cd')] == [
        (name, size, b''.join(chunks))
        for name, size, chunks in stream_unzip(stream_zip(files()))
    ]


def test_with_stream_unzip_with_no_compresion_32():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, NO_COMPRESSION_32, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, mode, NO_COMPRESSION_32, (b'c', b'd')

    assert [(b'file-1', 20000, b'a' * 10000 + b'b' * 10000), (b'file-2', 2, b'cd')] == [
        (name, size, b''.join(chunks))
        for name, size, chunks in stream_unzip(stream_zip(files()))
    ]


@pytest.mark.parametrize(
    "method",
    [
        NO_COMPRESSION_32,
        NO_COMPRESSION_64,
    ],
)
def test_with_stream_unzip_with_no_compresion_known_crc_32(method):
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, method(20000, zlib.crc32(b'a' * 10000 + b'b' * 10000)), (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, mode, method(2, zlib.crc32(b'c' + b'd')), (b'c', b'd')

    assert [(b'file-1', 20000, b'a' * 10000 + b'b' * 10000), (b'file-2', 2, b'cd')] == [
        (name, size, b''.join(chunks))
        for name, size, chunks in stream_unzip(stream_zip(files()))
    ]


@pytest.mark.parametrize(
    "method",
    [
        NO_COMPRESSION_32,
        NO_COMPRESSION_64,
    ],
)
def test_with_stream_unzip_with_no_compresion_no_crc_32(method):
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, method(20000, 0), (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, mode, method(2, 0), (b'c', b'd')

    assert [(b'file-1', 20000, b'a' * 10000 + b'b' * 10000), (b'file-2', 2, b'cd')] == [
        (name, size, b''.join(chunks))
        for name, size, chunks in stream_unzip(stream_zip(files()))
    ]


@pytest.mark.parametrize(
    "method",
    [
        NO_COMPRESSION_32,
        NO_COMPRESSION_64,
    ],
)
def test_with_stream_unzip_with_no_compresion_bad_crc_32(method):
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, method(20000, zlib.crc32(b'a' * 10000 + b'b' * 10000)), (b'a' * 10000, b'b' * 10000)
        yield 'file-1', now, mode, method(1, zlib.crc32(b'x')), (b'a',)

    with pytest.raises(CRC32IntegrityError):
        for name, size, chunks in stream_unzip(stream_zip(files())):
            pass


@pytest.mark.parametrize(
    "method",
    [
        NO_COMPRESSION_32,
        NO_COMPRESSION_64,
    ],
)
def test_with_stream_unzip_with_no_compresion_bad_size(method):
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, method(20000, zlib.crc32(b'a' * 10000 + b'b' * 10000)), (b'a' * 10000, b'b' * 10000)
        yield 'file-1', now, mode, method(1, zlib.crc32(b'')), (b'',)

    with pytest.raises(UncompressedSizeIntegrityError):
        for name, size, chunks in stream_unzip(stream_zip(files())):
            pass


def test_with_stream_unzip_auto_small():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, ZIP_AUTO(20000), (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, mode, ZIP_AUTO(2), (b'c', b'd')

    assert [(b'file-1', None, b'a' * 10000 + b'b' * 10000), (b'file-2', None, b'cd')] == [
        (name, size, b''.join(chunks))
        for name, size, chunks in stream_unzip(stream_zip(files()), allow_zip64=False)
    ]


@pytest.mark.parametrize(
    "level",
    [
        0,
        9,
    ],
)
def test_with_stream_unzip_at_zip_32_limit(level):
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, ZIP_AUTO(4293656841, level=level), gen_bytes(4293656841)

    assert [(b'file-1', None, 4293656841)] == [
        (name, size, sum(len(chunk) for chunk in chunks))
        for name, size, chunks in stream_unzip(stream_zip(files()), allow_zip64=False)
    ]


@pytest.mark.parametrize(
    "level",
    [
        0,
        9,
    ],
)
def test_with_stream_unzip_above_zip_32_size_limit(level):
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, ZIP_AUTO(4293656842, level=level), gen_bytes(4293656842)

    assert [(b'file-1', None, 4293656842)] == [
        (name, size, sum(len(chunk) for chunk in chunks))
        for name, size, chunks in stream_unzip(stream_zip(files()))
    ]

    with pytest.raises(UnsupportedZip64Error):
        next(iter(stream_unzip(stream_zip(files()), allow_zip64=False)))


def test_with_stream_unzip_above_zip_32_offset_limit():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, ZIP_AUTO(4000000000, level=0), gen_bytes(4000000000)
        yield 'file-2', now, mode, ZIP_AUTO(4000000000, level=0), gen_bytes(4000000000)
        yield 'file-3', now, mode, ZIP_AUTO(1, level=0), gen_bytes(1)

    assert [(b'file-1', None, 4000000000), (b'file-2', None, 4000000000), (b'file-3', None, 1)] == [
        (name, size, sum(len(chunk) for chunk in chunks))
        for name, size, chunks in stream_unzip(stream_zip(files()))
    ]

    file_1_zip_32 = False
    file_2_zip_32 = False
    with pytest.raises(UnsupportedZip64Error):
        it = iter(stream_unzip(stream_zip(files()), allow_zip64=False))
        name, size, chunks = next(it)
        for c in chunks:
            pass
        file_1_zip_32 = True
        name, size, chunks = next(it)
        for c in chunks:
            pass
        file_2_zip_32 = True
        name, size, chunks = next(it)

    assert file_1_zip_32
    assert file_2_zip_32


def test_with_stream_unzip_large_easily_compressible():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600
    batch = b'-' * 500000

    def files():
        def data():
            for i in range(0, 10000):
                yield batch

        yield 'file-1', now, mode, ZIP_64, data()

    num_received = 0
    for name, size, chunks in stream_unzip(stream_zip(files())):
        for chunk in chunks:
            num_received += len(chunk)

    assert num_received == 5000000000


def test_with_stream_unzip_large_not_easily_compressible_with_no_compression_64():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600
    batch = os.urandom(500000)

    def files():
        def data():
            for i in range(0, 10000):
                yield batch

        yield 'file-1', now, mode, ZIP_64, data()
        yield 'file-2', now, mode, NO_COMPRESSION_64, (b'-',)

    num_received = 0
    for name, size, chunks in stream_unzip(stream_zip(files())):
        for chunk in chunks:
            num_received += len(chunk)

    assert num_received == 5000000001


def test_with_stream_unzip_large_not_easily_compressible_with_no_compression_32():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600
    batch = os.urandom(500000)

    def files():
        def data():
            for i in range(0, 10000):
                yield batch

        yield 'file-1', now, mode, ZIP_64, data()
        yield 'file-2', now, mode, NO_COMPRESSION_32, (b'-',)

    with pytest.raises(OffsetOverflowError):
        for name, size, chunks in stream_unzip(stream_zip(files())):
            for chunk in chunks:
                pass


def test_with_stream_unzip_large_not_easily_compressible_with_zip_32():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = 0o600
    batch = os.urandom(500000)

    def files():
        def data():
            for i in range(0, 10000):
                yield batch

        yield 'file-1', now, mode, ZIP_64, data()
        yield 'file-2', now, mode, ZIP_32, (b'-',)  # Needs a ZIP_64 offset, but is in ZIP_32 mode

    with pytest.raises(OffsetOverflowError):
        for name, size, chunks in stream_unzip(stream_zip(files())):
            for chunk in chunks:
                pass


def test_zip_overflow_large_not_easily_compressible():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600
    batch = os.urandom(500000)

    def files():
        def data():
            for i in range(0, 10000):
                yield batch

        yield 'file-1', now, mode, ZIP_32, data()

    with pytest.raises(CompressedSizeOverflowError):
        for chunk in stream_zip(files()):
            pass


def test_zip_overflow_large_easily_compressible():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600
    batch = b'-' * 1000000

    def files():
        def data():
            for i in range(0, 10000):
                yield batch

        yield 'file-1', now, mode, ZIP_32, data()

    with pytest.raises(UncompressedSizeOverflowError):
        for chunk in stream_zip(files()):
            pass


def test_with_zipfile_zip_64():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1 🍰', now, mode, ZIP_64, (b'a' * 10000, b'b' * 10000)
        yield 'file-2 🍰', now, mode, ZIP_64, (b'c', b'd')

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
        'file-1 🍰',
        20000,
        (2021, 1, 1, 21, 1, 12),
        mode << 16,
        b'a' * 10000 + b'b' * 10000,
    ), (
        'file-2 🍰',
        2,
        (2021, 1, 1, 21, 1, 12),
        mode << 16,
        b'cd',
    )] == list(extracted())


def test_with_zipfile_zip_32():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, ZIP_32, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, mode, ZIP_32, (b'c', b'd')

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
        mode << 16,
        b'a' * 10000 + b'b' * 10000,
    ), (
        'file-2',
        2,
        (2021, 1, 1, 21, 1, 12),
        mode << 16,
        b'cd',
    )] == list(extracted())


def test_with_zipfile_zip_32_and_zip_64():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, ZIP_64, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, mode, ZIP_32, (b'c', b'd')

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
        mode << 16,
        b'a' * 10000 + b'b' * 10000,
    ), (
        'file-2',
        2,
        (2021, 1, 1, 21, 1, 12),
        mode << 16,
        b'cd',
    )] == list(extracted())


def test_with_zipfile_without_compression():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, NO_COMPRESSION_32, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, mode, NO_COMPRESSION_32, (b'c', b'd')

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
        mode << 16,
        b'a' * 10000 + b'b' * 10000,
    ), (
        'file-2',
        2,
        (2021, 1, 1, 21, 1, 12),
        mode << 16,
        b'cd',
    )] == list(extracted())


def test_with_zipfile_many_files_zip_64():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        for i in range(0, 100000):
            yield f'file-{i}', now, mode, ZIP_64, (b'ab',)

    def extracted():
        with ZipFile(BytesIO(b''.join(stream_zip(files())))) as my_zip:
            for my_info in my_zip.infolist():
                with my_zip.open(my_info.filename) as my_file:
                    yield None

    assert len(list(extracted())) == 100000


def test_with_zipfile_no_files():

    def extracted():
        with ZipFile(BytesIO(b''.join(stream_zip(())))) as my_zip:
            yield from my_zip.infolist()

    assert len(list(extracted())) == 0


def test_too_many_files_for_zip_32_raises_exception_in_zip_32_mode():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        for i in range(0, 0xffff + 1):
            yield f'file-{i}', now, mode, ZIP_32, (b'ab',)

    with pytest.raises(CentralDirectoryNumberOfEntriesOverflowError):
        for chunk in stream_zip(files()):
            pass


def test_too_many_files_for_zip_32_no_exception_in_auto_mode():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        for i in range(0, 0xffff + 1):
            yield f'file-{i}', now, mode, ZIP_AUTO(2), (b'ab',)

    num_files = 0
    for _, __, chunks in stream_unzip(stream_zip(files())):
        for chunk in chunks:
            pass
        num_files += 1

    assert num_files == 0xffff + 1


def test_central_directory_size_overflow():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        for i in range(0, 0xffff):
            yield str(i).zfill(5) + '-' * 65502, now, mode, NO_COMPRESSION_32, (b'',)

    with pytest.raises(CentralDirectorySizeOverflowError):
        for chunk in stream_zip(files()):
            pass


def test_directory_zipfile():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, ZIP_64, (b'a' * 10000, b'b' * 10000)
        yield 'file-2/', now, mode, ZIP_64, ()

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
        mode << 16,
        b'a' * 10000 + b'b' * 10000,
    ), (
        'file-2/',
        0,
        (2021, 1, 1, 21, 1, 12),
        mode << 16 | 0x10,
        b'',
    )] == list(extracted())


def test_with_unzip_zip64():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, ZIP_64, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, mode, ZIP_64, (b'c', b'd')

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
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, ZIP_64, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, mode, ZIP_32, (b'c', b'd')

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
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, NO_COMPRESSION_32, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, mode, NO_COMPRESSION_32, (b'c', b'd')

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
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield '-' * (2**16), now, mode, ZIP_64, (b'ab',)

    with pytest.raises(NameLengthOverflowError):
        for chunk in stream_zip(files()):
            pass


def test_exception_propagates():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, ZIP_64, (b'a' * 10000, b'b' * 10000)
        raise Exception('From generator')

    with pytest.raises(Exception,  match='From generator'):
        for chunk in stream_zip(files()):
            pass


def test_exception_from_bytes_propagates():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def data():
        yield b'-'
        raise Exception('From generator')

    def files():
        yield 'file-1', now, mode, ZIP_64, data()

    with pytest.raises(Exception,  match='From generator'):
        for chunk in stream_zip(files()):
            pass


def test_chunk_sizes():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def files():
        yield 'file-1', now, mode, ZIP_64, (os.urandom(500000),)

    def get_sizes():
        for chunk in stream_zip(files()):
            yield len(chunk)

    sizes = list(get_sizes())
    assert set(sizes[:-1]) == {65536}
    assert sizes[-1] <= 65536


@pytest.mark.parametrize(
    "method",
    [
        ZIP_32,
        ZIP_64,
    ],
)
def test_bsdcpio(method):
    assert method in (ZIP_32, ZIP_64)  # Paranoia check that parameterisation works

    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600
    zip_bytes = b''.join(stream_zip((
        ('file-1', now, mode, method, (b'contents',)),
    )))

    def read(path):
        with open(path, 'rb') as f:
            return f.read()

    bsdcpio = os.getcwd() + '/libarchive-3.5.3/bsdcpio'
    with \
            TemporaryDirectory() as d, \
            cwd(d), \
            subprocess.Popen(
                [bsdcpio, '-i'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ) as p:

        a = p.communicate(input=zip_bytes)
        assert a == (b'', b'1 block\n')
        assert p.returncode == 0
        assert read('file-1') == b'contents'


@pytest.mark.parametrize(
    "method",
    [
        ZIP_32,
        ZIP_64,
    ],
)
def test_7z_symbolic_link(method):
    modified_at = datetime.now()
    member_files = (
        ('my-file-1.txt', modified_at, stat.S_IFREG | 0o600, ZIP_64, (b'Some bytes 1',)),
        ('my-link.txt', modified_at, stat.S_IFLNK | 0o600, ZIP_64, (b'my-file-1.txt',)),
    )
    zipped_chunks = stream_zip(member_files)

    with \
            TemporaryDirectory() as d, \
            cwd(d): \

        with open('test.zip', 'wb') as fp:
            for zipped_chunk in zipped_chunks:
                fp.write(zipped_chunk)

        subprocess.run(['7z', 'e', 'test.zip'])

        with open('my-link.txt') as f:
            assert f.read() == 'Some bytes 1'


@pytest.mark.parametrize(
    "method",
    [
        ZIP_32,
        ZIP_64,
    ],
)
@pytest.mark.parametrize(
    "trailing_slash,mode,expected_mode",
    [
        ('', stat.S_IFDIR | 0o700, 'drwx------',),  # Documents that the mode is enough
        ('/', stat.S_IFDIR | 0o700, 'drwx------',),
        ('/', stat.S_IFREG | 0o700, 'drwx------',),  # Documents that trailing slash is enough
    ],
)
def test_7z_empty_directory(method, trailing_slash, mode, expected_mode):
    modified_at = datetime.now()
    member_files = (
        ('my-dir' + trailing_slash, modified_at, mode, method, ()),
    )
    zipped_chunks = stream_zip(member_files)

    with \
            TemporaryDirectory() as d, \
            cwd(d): \

        with open('test.zip', 'wb') as fp:
            for zipped_chunk in zipped_chunks:
                fp.write(zipped_chunk)

        subprocess.run(['7z', 'e', 'test.zip'])

        assert os.path.isdir('my-dir')
        assert stat.filemode(os.lstat('my-dir').st_mode) == expected_mode


@pytest.mark.parametrize(
    "method",
    [
        ZIP_32,
        ZIP_64,
    ],
)
@pytest.mark.parametrize(
    "trailing_slash,mode,expected_mode",
    [
        ('', stat.S_IFDIR | 0o700, '-rwx------'),  # Documents that unzip needs the trailing slash
        ('/', stat.S_IFDIR | 0o700, 'drwx------'),
        ('/', stat.S_IFREG | 0o700, 'drwx------'),  # Documents that trailing slash is enough
    ],
)
def test_unzip_empty_directory(method, trailing_slash, mode, expected_mode):
    modified_at = datetime.now()
    member_files = (
        ('my-dir' + trailing_slash, modified_at, mode, method, ()),
    )
    zipped_chunks = stream_zip(member_files)

    with \
            TemporaryDirectory() as d, \
            cwd(d): \

        with open('test.zip', 'wb') as fp:
            for zipped_chunk in zipped_chunks:
                fp.write(zipped_chunk)

        subprocess.run(['unzip', f'{d}/test.zip', '-d', d])

        assert stat.filemode(os.lstat('my-dir').st_mode) == expected_mode


@pytest.mark.parametrize(
    "method",
    [
        ZIP_32,
        ZIP_64,
    ],
)
@pytest.mark.parametrize(
    "trailing_slash,mode,is_dir",
    [
        ('', stat.S_IFDIR | 0o700, False),  # Documents that zipfile needs the trailing slash
        ('/', stat.S_IFDIR | 0o700, True),
        ('/', stat.S_IFREG | 0o700, True),  # Documents that trailing slash is enough
    ],
)
def test_zipfile_empty_directory(method, trailing_slash, mode, is_dir):
    modified_at = datetime.now()
    member_files = (
        ('my-dir' + trailing_slash, modified_at, stat.S_IFDIR | 0o700, method, ()),
    )
    zipped_chunks = stream_zip(member_files)

    def extracted():
        with ZipFile(BytesIO(b''.join(zipped_chunks))) as my_zip:
            for my_info in my_zip.infolist():
                with my_zip.open(my_info.filename) as my_file:
                    yield (
                        my_info.filename,
                        my_info.is_dir(),
                    )

    assert [('my-dir' + trailing_slash, is_dir)] == list(extracted())


@pytest.mark.parametrize(
    "method",
    [
        ZIP_32,
        ZIP_64,
    ],
)
@pytest.mark.parametrize(
    "trailing_slash,mode,expected_mode",
    [
        ('', stat.S_IFDIR | 0o700, '-rw-rw-r--'),  # Documents that bsdcpio needs the trailing slash and doesn't preserve perms
        ('/', stat.S_IFDIR | 0o700, 'drwxrwxr-x'),  # Documents that bsdcpio doesn't preserve perms
        ('/', stat.S_IFREG | 0o700, 'drwxrwxr-x'),  # Documents that trailing slash is enough and doesn't preserve perms
    ],
)
def test_bsdio_empty_directory(method, trailing_slash, mode, expected_mode):
    modified_at = datetime.now()
    member_files = (
        ('my-dir' + trailing_slash, modified_at, mode, method, ()),
    )
    zip_bytes = b''.join(stream_zip(member_files))

    bsdcpio = os.getcwd() + '/libarchive-3.5.3/bsdcpio'
    with \
            TemporaryDirectory() as d, \
            cwd(d), \
            subprocess.Popen(
                [bsdcpio, '-i'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ) as p:

        a = p.communicate(input=zip_bytes)

        subprocess.run([bsdcpio, f'{d}/test.zip', '-d', d])

        assert stat.filemode(os.lstat('my-dir').st_mode) == expected_mode


@pytest.mark.parametrize(
    "method",
    [
        ZIP_32,
        ZIP_64,
        NO_COMPRESSION_64,
        NO_COMPRESSION_32,
    ],
)
@pytest.mark.parametrize(
    "modified_at,expected_time",
    [
        (datetime(2011, 1, 1, 1, 2, 3, 123), (2011, 1, 1, 1, 2, 2)),
        (datetime(2011, 1, 1, 1, 2, 3, 123, tzinfo=timezone(timedelta(hours=0))), (2011, 1, 1, 1, 2, 2)),
        (datetime(2011, 1, 1, 1, 2, 3, 123, tzinfo=timezone(timedelta(hours=1))), (2011, 1, 1, 1, 2, 2)),
        (datetime(2011, 1, 1, 1, 2, 3, 123, tzinfo=timezone(timedelta(hours=-1))), (2011, 1, 1, 1, 2, 2)),
        (datetime(2011, 1, 1, 1, 2, 3, 123), (2011, 1, 1, 1, 2, 2)),
        (datetime(2011, 1, 1, 1, 2, 4, 123, tzinfo=timezone(timedelta(hours=0))), (2011, 1, 1, 1, 2, 4)),
        (datetime(2011, 1, 1, 1, 2, 4, 123, tzinfo=timezone(timedelta(hours=1))), (2011, 1, 1, 1, 2, 4)),
        (datetime(2011, 1, 1, 1, 2, 4, 123, tzinfo=timezone(timedelta(hours=-1))), (2011, 1, 1, 1, 2, 4)),
    ],
)
def test_zipfile_modification_time(method, modified_at, expected_time):
    member_files = (
        ('my_file', modified_at, stat.S_IFREG | 0o600, method, ()),
    )
    zipped_chunks = stream_zip(member_files)

    def extracted():
        with ZipFile(BytesIO(b''.join(zipped_chunks))) as my_zip:
            for my_info in my_zip.infolist():
                with my_zip.open(my_info.filename) as my_file:
                    yield (
                        my_info.filename,
                        my_info.date_time,
                    )

    assert [('my_file', expected_time)] == list(extracted())


@pytest.mark.parametrize(
    "method",
    [
        ZIP_32,
        ZIP_64,
        NO_COMPRESSION_64,
        NO_COMPRESSION_32,
    ],
)
@pytest.mark.parametrize(
    "timezone,modified_at",
    [
        ('UTC+0', datetime(2011, 1, 1, 1, 2, 3, 123)),
        ('UTC+0', datetime(2011, 1, 1, 1, 2, 3, 123, tzinfo=timezone(timedelta(hours=0)))),
        ('UTC+0', datetime(2011, 1, 1, 1, 2, 3, 123, tzinfo=timezone(timedelta(hours=1)))),
        ('UTC+0', datetime(2011, 1, 1, 1, 2, 3, 123, tzinfo=timezone(timedelta(hours=-1)))),
        ('UTC+1', datetime(2011, 1, 1, 1, 2, 3, 123)),
        ('UTC+1', datetime(2011, 1, 1, 1, 2, 3, 123, tzinfo=timezone(timedelta(hours=0)))),
        ('UTC+1', datetime(2011, 1, 1, 1, 2, 3, 123, tzinfo=timezone(timedelta(hours=1)))),
        ('UTC+1', datetime(2011, 1, 1, 1, 2, 3, 123, tzinfo=timezone(timedelta(hours=-1)))),
        ('UTC-1', datetime(2011, 1, 1, 1, 2, 3, 123)),
        ('UTC-1', datetime(2011, 1, 1, 1, 2, 3, 123, tzinfo=timezone(timedelta(hours=0)))),
        ('UTC-1', datetime(2011, 1, 1, 1, 2, 3, 123, tzinfo=timezone(timedelta(hours=1)))),
        ('UTC-1', datetime(2011, 1, 1, 1, 2, 3, 123, tzinfo=timezone(timedelta(hours=-1)))),
    ],
)
def test_unzip_modification_time(method, timezone, modified_at):
    member_files = (
        ('my_file', modified_at, stat.S_IFREG | 0o600, method, ()),
    )
    zipped_chunks = stream_zip(member_files)

    with \
            TemporaryDirectory() as d, \
            cwd(d): \

        with open('test.zip', 'wb') as fp:
            for zipped_chunk in zipped_chunks:
                fp.write(zipped_chunk)

        subprocess.run(['unzip', f'{d}/test.zip', '-d', d], env={'TZ': timezone})

        assert os.path.getmtime('my_file') == int(modified_at.timestamp())


@pytest.mark.parametrize(
    "method",
    [
        ZIP_32,
        ZIP_64,
        NO_COMPRESSION_64,
        NO_COMPRESSION_32,
    ],
)
@pytest.mark.parametrize(
    "timezone,modified_at,expected_modified_at",
    [
        ('UTC+1', datetime(2011, 1, 1, 1, 2, 3, 123), datetime(2011, 1, 1, 2, 2, 2, 0)),
    ],
)
def test_unzip_modification_time_extended_timestamps_disabled(method, timezone, modified_at, expected_modified_at):
    member_files = (
        ('my_file', modified_at, stat.S_IFREG | 0o600, method, ()),
    )
    zipped_chunks = stream_zip(member_files, extended_timestamps=False)

    with \
            TemporaryDirectory() as d, \
            cwd(d): \

        with open('test.zip', 'wb') as fp:
            for zipped_chunk in zipped_chunks:
                fp.write(zipped_chunk)

        subprocess.run(['unzip', f'{d}/test.zip', '-d', d], env={'TZ': timezone})

        assert os.path.getmtime('my_file') == expected_modified_at.timestamp()


@pytest.mark.parametrize(
    "method",
    [
        ZIP_32,
        ZIP_64,
        NO_COMPRESSION_64,
        NO_COMPRESSION_64(18, 1571107898),
        NO_COMPRESSION_32,
        NO_COMPRESSION_32(18, 1571107898),
    ],
)
def test_password_unzips_with_stream_unzip(method):
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600
    password = secrets.token_urlsafe(32)

    files = (
        ('file-1', now, mode, method, (b'a' * 9, b'b' * 9)),
    )

    assert b''.join(
        chunk
        for _, _, chunks in stream_unzip(stream_zip(files, password=password), password=password)
        for chunk in chunks
    ) == b'a' * 9 + b'b' * 9


@pytest.mark.parametrize(
    "method",
    [
        ZIP_32,
        ZIP_64,
        NO_COMPRESSION_64,
        NO_COMPRESSION_64(18, 1571107898),
        NO_COMPRESSION_32,
        NO_COMPRESSION_32(18, 1571107898),
    ],
)
def test_bad_password_not_unzips_with_stream_unzip(method):
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600
    password = secrets.token_urlsafe(32)

    files = (
        ('file-1', now, mode, method, (b'a' * 9, b'b' * 9)),
    )

    with pytest.raises(IncorrectAESPasswordError):
        list(stream_unzip(stream_zip(files, password=password), password='not'))


@pytest.mark.parametrize(
    "method",
    [
        ZIP_32,
        ZIP_64,
        NO_COMPRESSION_64,
        NO_COMPRESSION_64(18, 1571107898),
        NO_COMPRESSION_32,
        NO_COMPRESSION_32(18, 1571107898),
    ],
)
def test_password_unzips_with_7z(method):
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600
    password = secrets.token_urlsafe(32)

    files = (
        ('file-1', now, mode, method, (b'a' * 9, b'b' * 9)),
    )

    with \
            TemporaryDirectory() as d, \
            cwd(d): \

        with open('test.zip', 'wb') as fp:
            for zipped_chunk in stream_zip(files, password=password):
                fp.write(zipped_chunk)

        r = subprocess.run(['7zz', '-p' + password, 'e', 'test.zip'])
        assert r.returncode == 0

        for file in files:
            with open(file[0], 'rb') as f:
                assert f.read() == (b'a' * 9 ) + (b'b' * 9)


@pytest.mark.parametrize(
    "method",
    [
        ZIP_32,
        ZIP_64,
        NO_COMPRESSION_64,
        NO_COMPRESSION_64(18, 1571107898),
        NO_COMPRESSION_32,
        NO_COMPRESSION_32(18, 1571107898),
    ],
)
def test_password_unzips_with_pyzipper(method):
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600
    password = secrets.token_urlsafe(32)

    files = (
        ('file-1', now, mode, method, (b'a' * 9, b'b' * 9)),
    )

    with \
            TemporaryDirectory() as d, \
            cwd(d): \

        with open('test.zip', 'wb') as fp:
            for zipped_chunk in stream_zip(files, password=password):
                fp.write(zipped_chunk)

        with pyzipper.AESZipFile('test.zip') as zf:
            zf.setpassword(password.encode())
            zf.testzip()
            assert zf.read('file-1') == (b'a' * 9 ) + (b'b' * 9)


@pytest.mark.parametrize(
    "method",
    [
        ZIP_32,
        ZIP_64,
        NO_COMPRESSION_64,
        NO_COMPRESSION_64(18, 1571107898),
        NO_COMPRESSION_32,
        NO_COMPRESSION_32(18, 1571107898),
    ],
)
def test_password_bytes_not_deterministic(method):
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600
    password = secrets.token_urlsafe(32)

    files = (
        ('file-1', now, mode, method, (b'a' * 9, b'b' * 9)),
    )

    assert b''.join(stream_zip(files, password=password)) != b''.join(stream_zip(files, password=password))


@pytest.mark.parametrize(
    "method",
    [
        ZIP_32,
        ZIP_64,
        NO_COMPRESSION_64,
        NO_COMPRESSION_64(18, 1571107898),
        NO_COMPRESSION_32,
        NO_COMPRESSION_32(18, 1571107898),
    ],
)
def test_crc_32_not_in_file(method):
    # AE-2 should not have the CRC_32, so we check that the CRC_32 isn't anywhere in the file. This
    # is "too strong" as check, because it could just happen to appear in the cipher text, which
    # would be fine. The cipher text is by default non-deterministic due to its random salt, and
    # so this could be a flaky test and faily randomly. To make the test not flaky, we make the
    # bytes of the file completely deterministic, by forcing the random numbers used to generate
    # the salt to be non-random

    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600
    password = secrets.token_urlsafe(32)

    files = (
        ('file-1', now, mode, method, (b'a' * 9, b'b' * 9)),
    )
    crc_32 = Struct('<I').pack(1571107898)

    # To make sure we've got the correct CRC_32...
    assert crc_32 in b''.join(stream_zip(files))

    # ... to assert on the lack of it if we're using a password
    encrypted_bytes = b''.join(stream_zip(files, password=password, get_crypto_random=lambda num_bytes: b'-' * num_bytes))
    assert crc_32 not in encrypted_bytes

    # ... and we can just out of paranoia check check substrings of it are not in the file, in case
    # somehow we're leaking part of it. It's not perfect, but it's probably the best we can do
    # and will catch the most likely cases of just not enabling the logic to hide it
    assert crc_32[0:2] not in encrypted_bytes
    assert crc_32[1:3] not in encrypted_bytes
    assert crc_32[2:4] not in encrypted_bytes
    assert crc_32[0:3] not in encrypted_bytes
    assert crc_32[1:4] not in encrypted_bytes


###################################################################################################
# Tests of sync interface: async_stream_zip
#
# Under the hood we know that async_stream_zip delegates to stream_zip, so there isn't as much
# of a need to test everything. We have a brief test that it seems to work in one case, but
# otherwise focus on the riskiest parts: that exceptions don't propagate, that the async version
# doesn't actually stream, or that context vars are not propagated properly

def test_async_stream_zip_equivalent_to_stream_unzip_zip_32_and_zip_64():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    def sync_files():
        yield 'file-1', now, mode, ZIP_64, (b'a' * 10000, b'b' * 10000)
        yield 'file-2', now, mode, ZIP_32, (b'c', b'd')

    async def async_files():
        async def data_1():
            yield b'a' * 10000
            yield b'b' * 10000

        async def data_2():
            yield b'c'
            yield b'd'

        yield 'file-1', now, mode, ZIP_64, data_1()
        yield 'file-2', now, mode, ZIP_32, data_2()

    # Might not be performant, but good enough for the test
    async def async_concat(chunks):
        result = b''
        async for chunk in chunks:
            result += chunk
        return result

    async def test():
        assert b''.join(stream_zip(sync_files())) == await async_concat(async_stream_zip(async_files()))

    asyncio.get_event_loop().run_until_complete(test())


def test_async_exception_propagates():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    async def async_data():
        yield b'-'

    async def async_files():
        yield 'file-1', now, mode, ZIP_64, async_data()
        raise Exception('From generator')

    async def test():
        async for chunk in async_stream_zip(async_files()):
            pass

    with pytest.raises(Exception,  match='From generator'):
        asyncio.get_event_loop().run_until_complete(test())


def test_async_exception_from_bytes_propagates():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    async def async_data():
        yield b'-'
        raise Exception('From generator')

    async def async_files():
        yield 'file-1', now, mode, ZIP_64, async_data()

    async def test():
        async for chunk in async_stream_zip(async_files()):
            pass

    with pytest.raises(Exception,  match='From generator'):
        asyncio.get_event_loop().run_until_complete(test())


def test_async_stream_zip_does_stream():
    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    state = []

    async def async_data():
        for i in range(0, 4):
            state.append('in')
            for j in range(0, 1000):
                yield b'-' * 64000

    async def async_files():
        yield 'file-1', now, mode, ZIP_64, async_data()

    async def test():
        async for chunk in async_stream_zip(async_files()):
            state.append('out')

    asyncio.get_event_loop().run_until_complete(test())
    assert state == ['in', 'in', 'out', 'in', 'out', 'in', 'out', 'out']


@pytest.mark.skipif(
    tuple(int(v) for v in platform.python_version().split('.')) < (3,7,0),
    reason="contextvars are not supported before Python 3.7.0",
)
def test_copy_of_context_variable_available_in_iterable():
    # Ideally the context would be identical in the iterables, because that's what a purely asyncio
    # implementation of stream-zip would likely do

    import contextvars

    now = datetime.strptime('2021-01-01 21:01:12', '%Y-%m-%d %H:%M:%S')
    mode = stat.S_IFREG | 0o600

    var = contextvars.ContextVar('test')
    var.set('set-from-outer')

    d = contextvars.ContextVar('d')
    d.set({'key': 'original-value'})

    inner_files = None
    inner_bytes = None

    async def async_files():
        nonlocal inner_files, inner_bytes

        async def data_1():
            nonlocal inner_bytes
            inner_bytes = var.get()
            var.set('set-from-inner-bytes')
            d.get()['key'] = 'set-from-inner-bytes'
            yield b'-'

        inner_files = var.get()
        var.set('set-from-inner-files')
        d.get()['key'] = 'set-from-inner-files'
        yield 'file-1', now, mode, ZIP_64, data_1()

    async def test():
        async for chunk in async_stream_zip(async_files()):
            pass

    asyncio.get_event_loop().run_until_complete(test())

    assert var.get() == 'set-from-outer'
    assert inner_files == 'set-from-outer'
    assert inner_bytes == 'set-from-outer'
    assert d.get()['key'] == 'set-from-inner-bytes'
