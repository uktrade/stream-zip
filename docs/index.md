# stream-zip

Python function to construct a ZIP archive on the fly - without having to store the entire ZIP in memory or disk. This is useful in memory-constrained environments, or when you would like to start returning compressed data before you've even retrieved all the uncompressed data. Generating ZIPs on-demand in a web server is a typical use case for stream-zip.

Offers similar functionality to [zipfly](https://github.com/BuzonIO/zipfly), but with a different API, and does not use Python's zipfile module under the hood. Creates both Zip32/2.0/Legacy and Zip64 files.

To unZIP files on the fly try [stream-unzip](https://github.com/uktrade/stream-unzip).

## Commands

* `mkdocs new [dir-name]` - Create a new project.
* `mkdocs serve` - Start the live-reloading docs server.
* `mkdocs build` - Build the documentation site.
* `mkdocs -h` - Print help message and exit.

## Project layout

    mkdocs.yml    # The configuration file.
    docs/
        index.md  # The documentation homepage.
        ...       # Other markdown pages, images and other files.
