---
layout: sub-navigation
sectionKey: API reference
order: 1
title: API reference
---


## Modules

stream-zip exposes a single Python module: `stream_zip`.


## Functions

The `stream_zip` module exposes two functions:

- `stream_unzip.stream_zip`
- `stream_unzip.async_stream_zip`


## Methods

Each tuple of the iterable passed to `stream_unzip.stream_zip` and `stream_unzip.async_stream_zip` functions must specify a "method" as their 4th component, which must be one of the following values:

- [`ZIP_32`](/api/methods/#the-32-methods)
- [`NO_COMPRESSION_32`](/api/methods/#the-32-methods)
- [`NO_COMPRESSION_32(uncompressed_size, crc_32)`](/api/methods/#the-32-methods)
- [`ZIP_64`](/api/methods/#the-64-methods)
- [`NO_COMPRESSION_64`](/api/methods/#the-64-methods)
- [`NO_COMPRESSION_64(uncompressed_size, crc_32)`](/api/methods/#the-64-methods)
- [`ZIP_AUTO(uncompressed_size, level=9)`](/api/methods/#the-zip-auto-method)


## Exceptions

Exceptions raised by the source iterables are passed through the `stream_zip.stream_zip` and `stream_zip.async_stream_zip` functions to client code unchanged. All explicitly-thrown exceptions derive from `stream_zip.ZipError`.

Visit the [Exception hierarchy](/api/exception-hierarchy/) for details on all the exception types and how they relate to each other.
