---
layout: sub-navigation
sectionKey: API reference
caption: API reference
eleventyNavigation:
    parent: API reference
order: 4
title: Compression methods
---


Each member file of a ZIP is compressed with one of the below methods.


## The *_32 methods

- `ZIP_32`
- `NO_COMPRESSION_32`
- `NO_COMPRESSION_32(uncompressed_size, crc_32)`

These methods are the historical standard methods for ZIP files.

`ZIP_32` compresses the file by default, but it is affected the `get_compressobj` parameter to `stream_unzip`. For example, by passing `get_compressobj=lambda: zlib.compressobj(wbits=-zlib.MAX_WBITS, level=0)`, the `level=0` part would result in this file not being compressed. Its size would increase slightly due to overhead of the underlying algorithm.

Both `NO_COMPRESSION_32` and `NO_COMPRESSION_32(uncompressed_size, crc_32)` store the contents of the file in the ZIP uncompressed exactly as supplied, and are not affected by the `get_compressobj` parameter to `stream_unzip`.

For `NO_COMPRESSION_32` the entire contents are buffered in memory before output begins, and so should not be used for large files. For `NO_COMPRESSION_32(uncompressed_size, crc_32)` the contents are streamed, but at the price of having to determine the uncompressed size and CRC 32 of the contents beforehand. These limitations, although awkward when writing the ZIP, allow the ZIP file to be read in a streaming way.

Each member file using using one of these methods is limited to 4GiB (gibibyte). This limitation is on the uncompressed size of the data, and (if `ZIP_32`) the compressed size of the data, and how far the start of the member file is from the beginning in the final ZIP file. Also, each member file cannot be later than the 65,535th member file in a ZIP. If a file only has only these members, the entire file is a Zip32 file, and the end of the final member file must be less than 4GiB from the beginning of the final ZIP. If these limits are breached, a `ZipOverflowError` will be raised.

This has very high support. You can usually assume anything that can open a ZIP file can open ZIP files with only `ZIP_32` or `NO_COMPRESSION_32` members.


## The *_64 methods

- `ZIP_64`
- `NO_COMPRESSION_64`
- `NO_COMPRESSION_64(uncompressed_size, crc_32)`

These methods use the Zip64 extension to the original ZIP format.

`ZIP_64` compresses the file by default, but it is affected the `get_compressobj` parameter to `stream_unzip`. For example, by passing `get_compressobj=lambda: zlib.compressobj(wbits=-zlib.MAX_WBITS, level=0)`, the `level=0` part would result in this file not being compressed. However, its size would increase slightly due to overhead of the underlying algorithm.

Both `NO_COMPRESSION_64` and `NO_COMPRESSION_64(uncompressed_size, crc_32)` store the contents of the file in the ZIP uncompressed exactly as supplied, and are not affected by the `get_compressobj` parameter to `stream_unzip`.

For `NO_COMPRESSION_64` the entire contents are buffered in memory before output begins, and so should not be used for large files. For `NO_COMPRESSION_64(uncompressed_size, crc_32)` the contents are streamed, but at the price of having to determine the uncompressed size and CRC 32 of the contents beforehand. These limitations, although awkward when writing the ZIP, allow the ZIP file to be read in a streaming way.

Each member file is limited to 16EiB (exbibyte). This limitation is on the uncompressed size of the data, and (if `ZIP_64`) the compressed size of the data, and how far the member starts from the beginning in the final ZIP file. If these limits are breached, a `ZipOverflowError` will be raised.

Support is limited to newer clients. However, at the time of writing there are three known cases where even modern client support is limited:

- [LibreOffice does not support OpenDocument files that are created with the Zip64 extension.](https://bugs.documentfoundation.org/show_bug.cgi?id=128244)
- [Java's ZipInputStream will fail on Zip64 files in some cases.](https://bugs.openjdk.org/browse/JDK-8298530)
- [MacOS Safari's default auto extract behaviour only extracts the first member of a ZIP if that first member is Zip64, and effectively deletes the others.](https://github.com/uktrade/stream-zip/pull/42) This means that in most cases, if your ZIP file is to be made available via download from web pages, and if it has more than one member file, the first member file should never be `ZIP_64` or `NO_COMPRESSION_64`. Instead, use `ZIP_32` or `NO_COMPRESSION_32`.

## The ZIP_AUTO method

`ZIP_AUTO(uncompressed_size, level=9)`

This dynamic method chooses `ZIP_32` if it is sure a `ZipOverflowError` won't occur with its lower limits, but chooses `ZIP_64` otherwise. It uses the required parameter of `uncompressed_size`, as well as other more under the hood details, such as how far the member file would appear from the start of the ZIP file.

Compression level can be changed by overwriting the `level` parameter. Specifically, passing `level=0` disables compresion for this member file, but its size would increase slightly due to the overhead of the underlying algorithm. It is not affected by the `get_compressobj` parameter to `stream_unzip`.
