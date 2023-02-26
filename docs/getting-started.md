## Prerequisites

Python 3.7+


## Installation

You can install stream-zip from [PyPI](https://pypi.org/project/stream-zip/) using pip.

```bash
pip install stream-zip
```

This installs the latest version of stream-zip.

If you regularly install stream-zip, such as during application deployment, to avoid unexpected changes as new versions are released, you can pin to a specific version. [Poetry](https://python-poetry.org/) or [pip-tools](https://pip-tools.readthedocs.io/en/latest/) are popular tools that can be used for this.


## ZIP files

Some understanding of ZIP files is needed to use stream-zip. A ZIP file is a collection of member files, where each member file has 5 properties.

1. Name
2. Modification time
3. Compression and metadata format
4. Permissions
5. Binary contents

stream-unzip does not offer defaults for any of these 5 properties.


## Basic usage

A single function is exposed, `stream_zip`. This function takes an iterable of member files, and returns an iterable yielding the bytes of the ZIP file. Each member file must be a tuple of the above 5 properties.

```python
from datetime import datetime
from stream_zip import ZIP_32, stream_zip

member_files = (
    (
        'my-file-1.txt',     # Name
        datetime.now(),      # Modification time
        0o600,               # Permissions - owner can read and write
        ZIP_32,              # ZIP_32 has good support but limited to 4GB
        (b'Some bytes 1',),  # Iterable of chunks of contents
    ),
)
zipped_chunks = stream_zip(member_files):

for zipped_chunk in zipped_chunks:
    print(zipped_chunk)
```

## Generators

In the above example `member_files` is a tuple. However, any iterable that yields tuples can be used, for example a generator.

```python
from datetime import datetime
from stream_zip import ZIP_32, stream_zip

def member_files():
    modified_at = datetime.now()
    perms = 0o600
    yield ('my-file-1.txt', modified_at, perms, ZIP_32, (b'Some bytes 1',))

zipped_chunks = stream_zip(member_files()):

for zipped_chunk in zipped_chunks:
    print(zipped_chunk)
```

Each iterable of binary chunks of file contents could be a generator.

```python
from datetime import datetime
from stream_zip import ZIP_32, stream_zip

def member_files():
    modified_at = datetime.now()
    perms = 0o600

    def file_1_data():
        yield b'Some bytes 1'

    yield ('my-file-1.txt', modified_at, perms, ZIP_32, file_1_data())

zipped_chunks = stream_zip(member_files()):

for zipped_chunk in zipped_chunks:
    print(zipped_chunk)
```

This pattern of generators is typical for stream-unzip. It allows avoiding loading all the bytes of member files into memory at once.


## Full example

This is a example of a ZIP showing all supported compression and metadata formats. See [Limitations](limitations.md) for a discussion of these.

```python
from datetime import datetime
from stream_zip import ZIP_64, ZIP_32, NO_COMPRESSION_64, NO_COMPRESSION_32, stream_zip

def member_files():
    modified_at = datetime.now()
    perms = 0o600

    def file_1_data():
        yield b'Some bytes 1'

    def file_2_data():
        yield b'Some bytes 1'
        yield b'Some bytes 2'

    def file_3_data():
        yield b'Some bytes 1'
        yield b'Some bytes 2'
        yield b'Some bytes 3'
        yield b'Some bytes 4'

    def file_4_data():
        for i in range(5):
            yield bytes(f'Some bytes {i}', encoding="utf-8")

    # ZIP_64 mode
    yield 'my-file-1.txt', modified_at, perms, ZIP_64, file_1_data()

    # ZIP_32 mode
    yield 'my-file-2.txt', modified_at, perms, ZIP_32, file_2_data()

    # No compression for ZIP_64 files
    yield 'my-file-3.txt', modified_at, perms, NO_COMPRESSION_64, file_3_data()

    # No compression for ZIP_32 files
    yield 'my-file-4.txt', modified_at, perms, NO_COMPRESSION_32, file_4_data()

for zipped_chunk in stream_zip(member_files()):
    print(zipped_chunk)
```
