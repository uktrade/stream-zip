# stream-zip [![CircleCI](https://circleci.com/gh/uktrade/stream-zip.svg?style=shield)](https://circleci.com/gh/uktrade/stream-zip) [![Test Coverage](https://api.codeclimate.com/v1/badges/80442ee55a1276e83b44/test_coverage)](https://codeclimate.com/github/uktrade/stream-zip/test_coverage)

Python function to construct a ZIP archive on the fly - without having to store the entire ZIP in memory or disk. This is useful in memory-constrained environments, or when you would like to start returning compressed data before you've even retrieved all the uncompressed data.

Generating ZIPs on-demand in a web server is a typical use case for stream-zip.

Offers similar functionality to [zipfly](https://github.com/BuzonIO/zipfly), but with a different API, and does not use Python's zipfile module under the hood.


## Installation

```bash
pip install stream-zip
```


## Usage

```python
from datetime import datetime
from stream_zip import stream_zip

def unzipped_files():
    modified_at = datetime.now()
    perms = 0o600

    def file_1_data():
        yield b'Some bytes'

    def file_2_data():
        yield b'Some bytes'

    yield 'my-file-1.txt', modified_at, perms, file_1_data()
    yield 'my-file-2.txt', modified_at, perms, file_2_data()

for zipped_chunk in stream_zip(unzipped_files()):
    print(zipped_chunk)
```
