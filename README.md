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
from stream_zip import ZIP64, ZIP, NO_COMPRESSION, stream_zip

def unzipped_files():
    modified_at = datetime.now()
    perms = 0o600

    def file_1_data():
        yield b'Some bytes'

    def file_2_data():
        yield b'Some bytes'

    def file_3_data():
        yield b'Some bytes'

    # ZIP64 mode
    yield 'my-file-1.txt', modified_at, perms, ZIP64, file_1_data()

    # ZIP mode
    yield 'my-file-1.txt', modified_at, perms, ZIP, file_2_data()

    # No compression
    yield 'my-file-2.txt', modified_at, perms, NO_COMPRESSION, file_3_data()

for zipped_chunk in stream_zip(unzipped_files()):
    print(zipped_chunk)
```


## Limitations

It's not possible to _completely_ stream-write ZIP files. Small bits of metadata for each member file, such as its name, must be placed at the _end_ of the ZIP. In order to do this, stream-unzip buffers this metadata in memory until it can be output.

No compression is supported via the `NO_COMPRESSION` constant as in the above examples. However in this case the entire contents of these are buffered in memory, and so this should not be used for large files. This is because for uncompressed data, its size and CRC32 must be _before_ it in the ZIP file.

It doesn't seem possible to automatically choose [ZIP64](https://en.wikipedia.org/wiki/ZIP_(file_format)#ZIP64) based on file sizes if streaming, since the specification of ZIP vs ZIP64 must be _before_ the compressed data of each file in the final stream, and so before the sizes are known. Hence the onus is on client code to choose. ZIP has greater support but is limited to 4GiB (gibibyte), while ZIP64 has less support, but has a much greater limit of 16EiB (exbibyte). These limits apply to the compressed size of each member file, the uncompressed size of each member file, and to the size of the entire archive.
