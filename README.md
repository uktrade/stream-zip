# stream-zip [![CircleCI](https://circleci.com/gh/uktrade/stream-zip.svg?style=shield)](https://circleci.com/gh/uktrade/stream-zip) [![Test Coverage](https://api.codeclimate.com/v1/badges/80442ee55a1276e83b44/test_coverage)](https://codeclimate.com/github/uktrade/stream-zip/test_coverage)

Python function to construct a ZIP archive on the fly - without having to store the entire ZIP in memory or disk. This is useful in memory-constrained environments, or when you would like to start returning compressed data before you've even retrieved all the uncompressed data. Generating ZIPs on-demand in a web server is a typical use case for stream-zip.

Offers similar functionality to [zipfly](https://github.com/BuzonIO/zipfly), but with a different API, and does not use Python's zipfile module under the hood.

To unZIP files on the fly try [stream-unzip](https://github.com/uktrade/stream-unzip).


## Installation

```bash
pip install stream-zip
```


## Usage

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


## Limitations

It's not possible to _completely_ stream-write ZIP files. Small bits of metadata for each member file, such as its name, must be placed at the _end_ of the ZIP. In order to do this, stream-unzip buffers this metadata in memory until it can be output.

No compression is supported via the `NO_COMPRESSION_*` constants as in the above examples. However in these cases the entire contents of each are buffered in memory, and so should not be used for large files. This is because for uncompressed data, its size and CRC32 must be _before_ it in the ZIP file.

It doesn't seem possible to automatically choose [ZIP_64](https://en.wikipedia.org/wiki/ZIP_(file_format)#ZIP64) based on file sizes if streaming, since the specification of ZIP_32 vs ZIP_64 must be _before_ the compressed data of each file in the final stream, and so before the sizes are known. Hence the onus is on client code to choose. ZIP_32 has greater support but is limited to 4GiB (gibibyte), while ZIP_64 has less support, but has a much greater limit of 16EiB (exbibyte). These limits apply to the compressed size of each member file, the uncompressed size of each member file, and to the size of the entire archive.


## Exception hierarchy

  - **ZipError**

    Base class for all explicitly-thrown exceptions

    - **ZipValueError** (also inherits from the **ValueError** built-in)

      Base class for errors relating to invalid arguments

      - **ZipOverflowError** (also inherits from the **OverflowError** built-in)

        The sizes of data are too large to store in the requested mode

        - **UncompressedSizeOverflowError**

          The uncompressed size of the data is too large. The maximum uncompressed size for ZIP_32 mode is 2^32 - 1 bytes, and for ZIP_64 mode is 2^64 - 1 bytes.

        - **CompressedSizeOverflowError**

          The compressed size of the data is too large. The maximum compressed size for ZIP_32 mode is 2^32 - 1 bytes, and for ZIP_64 mode is 2^64 - 1 bytes.

        - **CentralDirectorySizeOverflowError**

          The size of the _central directory_, a section at the end of the ZIP that lists all the member files. The maximum size for ZIP_32 mode is 2^32 - 1 bytes, and for ZIP_64 mode is 2^64 - 1 bytes.

          If any `_64` mode files are in the ZIP, the central directory is in ZIP_64 mode, and ZIP_32 mode otherwise.

        - **CentralDirectoryNumberOfEntriesOverflowError**

          Too many files in the central directory, a section at the end of the ZIP that lists all the member files. The limit for ZIP_32 mode is 2^16 - 1 bytes, and for ZIP_64 mode is 2^64 - 1 bytes.

          If any `_64` mode files are in the ZIP, the central directory is in ZIP_64 mode, and ZIP_32 mode otherwise.

        - **OffsetOverflowError**

          The offset of data in the ZIP is too high, i.e. the ZIP is too large. The limit for ZIP_32 mode is 2^32 - 1 bytes, and for ZIP_64 mode is 2^64 - 1 bytes.

          This can be raised when stream-zip adds member files, or when it add the central directory at the end of the ZIP file. If any `_64` mode files are in the ZIP, the central directory is in ZIP_64 mode, and ZIP_32 mode otherwise.

        - **NameLengthOverflowError**

          The length of a file name is too high. The limit is 2^16 - 1 bytes, and applied to file names after UTF-8 encoding.
