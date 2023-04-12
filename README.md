<!-- --8<-- [start:intro] -->
# stream-zip

[![PyPI version](https://badge.fury.io/py/stream-zip.svg)](https://pypi.org/project/stream-zip/) [![Tests](https://github.com/uktrade/stream-zip/actions/workflows/tests.yml/badge.svg)](https://github.com/uktrade/stream-zip/actions/workflows/tests.yml) [![Test Coverage](https://api.codeclimate.com/v1/badges/80442ee55a1276e83b44/test_coverage)](https://codeclimate.com/github/uktrade/stream-zip/test_coverage)

Python function to construct a ZIP archive on the fly - without having to store the entire ZIP in memory or disk. This is useful in memory-constrained environments, or when you would like to start returning compressed data before you've even retrieved all the uncompressed data. Generating ZIPs on-demand in a web server is a typical use case for stream-zip.

Offers similar functionality to [zipfly](https://github.com/BuzonIO/zipfly), but with a different API, and does not use Python's zipfile module under the hood. Creates both Zip32/2.0/Legacy and Zip64 files.
<!-- --8<-- [end:intro] -->

To unZIP files on the fly try [stream-unzip](https://github.com/uktrade/stream-unzip).

---

Visit the [stream-zip documentation](https://stream-zip.docs.trade.gov.uk/) for usage instructions.
