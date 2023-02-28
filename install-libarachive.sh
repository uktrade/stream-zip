#!/bin/bash

set -e

# This version is the one that comes with macOS, and behaves most similarly to its Archive Utility
curl --output libarchive-3.5.3.tar.gz https://www.libarchive.org/downloads/libarchive-3.5.3.tar.gz
echo "72788e5f58d16febddfa262a5215e05fc9c79f2670f641ac039e6df44330ef51 libarchive-3.5.3.tar.gz" | sha256sum --check
tar -zxf libarchive-3.5.3.tar.gz
(
    cd libarchive-3.5.3
    ./configure
    make
)
