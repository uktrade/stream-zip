---
title: Getting started
---


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

    # No compression for ZIP_32 files
    yield 'my-file-3.txt', modified_at, perms, NO_COMPRESSION_64, file_3_data()

    # No compression for ZIP_64 files
    yield 'my-file-4.txt', modified_at, perms, NO_COMPRESSION_32, file_4_data()

for zipped_chunk in stream_zip(unzipped_files()):
    print(zipped_chunk)
```
