<!-- --8<-- [start:intro] -->
# stream-zip

[![conda-forge package](https://img.shields.io/conda/v/conda-forge/stream-zip?label=conda-forge&color=%234c1)](https://anaconda.org/conda-forge/stream-zip) [![PyPI package](https://img.shields.io/pypi/v/stream-zip?label=PyPI%20package&color=%234c1)](https://pypi.org/project/stream-zip/) [![Test suite](https://img.shields.io/github/actions/workflow/status/uktrade/stream-zip/test.yml?label=Test%20suite)](https://github.com/uktrade/stream-zip/actions/workflows/test.yml) [![Code coverage](https://img.shields.io/codecov/c/github/uktrade/stream-zip?label=Code%20coverage)](https://app.codecov.io/gh/uktrade/stream-zip)

Python function to construct a ZIP archive on the fly - without having to store the entire ZIP in memory or disk. This is useful in memory-constrained environments, or when you would like to start returning compressed data before you've even retrieved all the uncompressed data. Generating ZIPs on-demand in a web server is a typical use case for stream-zip.

Offers similar functionality to [zipfly](https://github.com/BuzonIO/zipfly), but with a different API, and does not use Python's zipfile module under the hood. Creates both Zip32/2.0/Legacy and Zip64 files.
<!-- --8<-- [end:intro] -->

To unZIP files on the fly try [stream-unzip](https://github.com/uktrade/stream-unzip).

<!-- --8<-- [start:features] -->
## Features

In addition to being memory efficient (with some [limitations](https://stream-zip.docs.trade.gov.uk/get-started/#limitations)) stream-zip:

- Constructs ZIP files that can be stream unzipped, for example by [stream-unzip](https://stream-unzip.docs.trade.gov.uk/)

- Can construct Zip64 ZIP files. Zip64 ZIP files allow sizes far beyond the approximate 4GiB limit of the original ZIP format

- Can construct ZIP files that contain symbolic links

- Can construct ZIP files that contain directories, including empty directories

- Can construct password protected / AES-256 encrypted ZIP files adhering to the [WinZip AE-2 specification](https://www.winzip.com/en/support/aes-encryption/).

- Allows the specification of permissions on the member files and directories (although not all clients respect them)

- By default stores modification time as an extended timestamp. An extended timestamp is a more accurate timestamp than the original ZIP format allows

<!-- --8<-- [end:features] -->

---

Visit the [stream-zip documentation](https://stream-zip.docs.trade.gov.uk/) for usage instructions.
