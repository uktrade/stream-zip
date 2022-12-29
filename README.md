# stream-zip [![PyPI version](https://badge.fury.io/py/stream-zip.svg)](https://pypi.org/project/stream-zip/) [![CircleCI](https://circleci.com/gh/uktrade/stream-zip.svg?style=shield)](https://circleci.com/gh/uktrade/stream-zip) [![Test Coverage](https://api.codeclimate.com/v1/badges/80442ee55a1276e83b44/test_coverage)](https://codeclimate.com/github/uktrade/stream-zip/test_coverage)

Python function to construct a ZIP archive on the fly - without having to store the entire ZIP in memory or disk. This is useful in memory-constrained environments, or when you would like to start returning compressed data before you've even retrieved all the uncompressed data. Generating ZIPs on-demand in a web server is a typical use case for stream-zip.

Offers similar functionality to [zipfly](https://github.com/BuzonIO/zipfly), but with a different API, and does not use Python's zipfile module under the hood. Creates both Zip32/2.0/Legacy and Zip64 files.

To unZIP files on the fly try [stream-unzip](https://github.com/uktrade/stream-unzip).


## Installation

```bash
pip install stream-zip
```


## Usage

The function `stream_zip` takes a nested iterable of the files and data to go into the ZIP, and it returns an iterable of the bytes of the zip file.

```python
from datetime import datetime
from stream_zip import ZIP_64, ZIP_32, NO_COMPRESSION_64, NO_COMPRESSION_32, stream_zip

def unzipped_files():
    modified_at = datetime.now()
    perms = 0o600

    def file_1_data():
        yield b'Some bytes 1'

    def file_2_data():
        yield b'Some bytes 2'

    def file_3_data():
        yield b'Some bytes 3'

    def file_4_data():
        yield b'Some bytes 4'

    # ZIP_64 mode
    yield 'my-file-1.txt', modified_at, perms, ZIP_64, file_1_data()

    # ZIP_32 mode
    yield 'my-file-2.txt', modified_at, perms, ZIP_32, file_2_data()

    # No compression for ZIP_32 files
    yield 'my-file-3.txt', modified_at, perms, NO_COMPRESSION_64, file_3_data()

    # No compression for ZIP_64 files
    yield 'my-file-4.txt', modified_at, perms, NO_COMPRESSION_32, file_4_data()

for zipped_chunk in stream_zip(unzipped_files()):
    print(zipped_chunk)
```


## Custom zlib options

You can customise the compression object by overriding the default `get_compressobj` parameter, which is shown below.

```python
for zipped_chunk in stream_zip(unzipped_files(), get_compressobj=lambda: zlib.compressobj(wbits=-zlib.MAX_WBITS, level=9)):
    print(zipped_chunk)
```


## File-like object

If you need a file-like object rather than an iterable yielding bytes, you can pass the return value of `stream_zip` through `to_file_like_obj` defined as below.

```python
def to_file_like_obj(iterable):
    chunk = b''
    offset = 0
    it = iter(iterable)

    def up_to_iter(size):
        nonlocal chunk, offset

        while size:
            if offset == len(chunk):
                try:
                    chunk = next(it)
                except StopIteration:
                    break
                else:
                    offset = 0
            to_yield = min(size, len(chunk) - offset)
            offset = offset + to_yield
            size -= to_yield
            yield chunk[offset - to_yield:offset]

    class FileLikeObj:
        def read(self, size=-1):
            return b''.join(up_to_iter(float('inf') if size is None or size < 0 else size))

    return FileLikeObj()
```

This can be used to upload large ZIP files to S3 using [boto3's upload_fileobj](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.upload_fileobj), which splits larger files into multipart uploads.

```python
import boto3
from boto3.s3.transfer import TransferConfig

zipped_chunks = stream_zip(unzipped_files())
zipped_chunks_obj = to_file_like_obj(zipped_chunks)

s3 = boto3.client('s3')
s3.upload_fileobj(
    zipped_chunks_obj, 'mybucket', 'mykey',
    # Since we're streaming the final total size is unknown, so we have to tell boto3 what part
    # size to use to accomodate the entire file - S3 has a hard coded limit of 10000 parts
    # In this example we choose a part size of 200MB, so 2TB maximum final object size
    Config=TransferConfig(multipart_chunksize=1024 * 1024 * 200),
)
```


## Custom chunk size

The default `bytes` instance size is 65536 bytes. To customise this, you can override the `chunk_size` parameter.

```python
for zipped_chunk in stream_zip(unzipped_files(), chunk_size=65536):
    print(zipped_chunk)
```

This one size is used both for input - splitting or gathering any uncompressed data into `chunk_size` bytes before attempting to compress it, and in output - splitting or gathering any compressed data into `chunk_size` bytes before returning it to client code.


## Limitations

It's not possible to _completely_ stream-write ZIP files. Small bits of metadata for each member file, such as its name, must be placed at the _end_ of the ZIP. In order to do this, stream-zip buffers this metadata in memory until it can be output.

No compression is supported by two different mechanisms:

- Using `NO_COMPRESSION_*` constants as in the above examples. However in these cases the entire contents of each uncompressed file is buffered in memory, and so should not be used for large files. This is because for raw uncompressed data, where the reader has no way of knowing when it gets to the end, its size and CRC32 must be _before_ it in the ZIP file.

- Using `ZIP_*` constants, but passing `level=0` into a custom zlib compression object. This avoids the buffering into memory that `NO_COMPRESSION_*` will perform, but the output stream would be slightly larger. This is because the data will contain extra bytes every so often so it can indicate its end to the reader.

It doesn't seem possible to automatically choose [ZIP_64](https://en.wikipedia.org/wiki/ZIP_(file_format)#ZIP64) based on file sizes if streaming, since the specification of ZIP_32 vs ZIP_64 must be _before_ the compressed data of each file in the final stream, and so before the sizes are known. Hence the onus is on client code to choose. ZIP_32 has greater support but is limited to 4GiB (gibibyte), while ZIP_64 has less support, but has a much greater limit of 16EiB (exbibyte). These limits apply to both the compressed and uncompressed sizes of each member file.


## Exception hierarchy

  - **ZipError**

    Base class for all explicitly-thrown exceptions

    - **ZipValueError** (also inherits from the **ValueError** built-in)

      Base class for errors relating to invalid arguments

      - **ZipOverflowError** (also inherits from the **OverflowError** built-in)

        The size or positions of data in the ZIP are too large to store in the requested mode

        - **UncompressedSizeOverflowError**

          The uncompressed size of a member file is too large. The maximum uncompressed size for ZIP_32 mode is 2^32 - 1 bytes, and for ZIP_64 mode is 2^64 - 1 bytes.

        - **CompressedSizeOverflowError**

          The compressed size of a member file is too large. The maximum compressed size for ZIP_32 mode is 2^32 - 1 bytes, and for ZIP_64 mode is 2^64 - 1 bytes.

        - **CentralDirectorySizeOverflowError**

          The size of the central directory, a section at the end of the ZIP that lists all the member files. The maximum size for ZIP_32 mode is 2^32 - 1 bytes, and for ZIP_64 mode is 2^64 - 1 bytes.

          If any `_64` mode files are in the ZIP, the central directory is in ZIP_64 mode, and ZIP_32 mode otherwise.

        - **CentralDirectoryNumberOfEntriesOverflowError**

          Too many entries in the central directory, a section at the end of the ZIP that lists all the member files. The limit for ZIP_32 mode is 2^16 - 1 entries, and for ZIP_64 mode is 2^64 - 1 entries.

          If any `_64` mode files are in the ZIP, the central directory is in ZIP_64 mode, and ZIP_32 mode otherwise.

        - **OffsetOverflowError**

          The offset of data in the ZIP is too high, i.e. the ZIP is too large. The limit for ZIP_32 mode is 2^32 - 1 bytes, and for ZIP_64 mode is 2^64 - 1 bytes.

          This can be raised when stream-zip adds member files, or when it adds the central directory at the end of the ZIP file. If any `_64` mode files are in the ZIP, the central directory is in ZIP_64 mode, and ZIP_32 mode otherwise.

          It is possible for the ZIP file to be larger than the maximum allowed offset without this exception being thrown. For example in ZIP_32 mode the archive can can be larger than 2^32 - 1 bytes.

        - **NameLengthOverflowError**

          The length of a file name is too high. The limit is 2^16 - 1 bytes, and applied to file names after UTF-8 encoding.
