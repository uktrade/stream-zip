# Limitations

It's not possible to _completely_ stream-write ZIP files. Small bits of metadata for each member file, such as its name, must be placed at the _end_ of the ZIP. In order to do this, stream-zip buffers this metadata in memory until it can be output.

No compression is supported by two different mechanisms:

- Using `NO_COMPRESSION_*` constants as the [full example](getting-started.md#full-example). However in these cases the entire contents of each uncompressed file is buffered in memory, and so should not be used for large files. This is because for raw uncompressed data, where the reader has no way of knowing when it gets to the end, its size and CRC32 must be _before_ it in the ZIP file.

- Using `ZIP_*` constants, but passing `level=0` into a custom zlib compression object. This avoids the buffering into memory that `NO_COMPRESSION_*` will perform, but the output stream would be slightly larger. This is because the data will contain extra bytes every so often so it can indicate its end to the reader.

It doesn't seem possible to automatically choose [ZIP_64](https://en.wikipedia.org/wiki/ZIP_(file_format)#ZIP64) based on file sizes if streaming, since the specification of ZIP_32 vs ZIP_64 must be _before_ the compressed data of each file in the final stream, and so before the sizes are known. Hence the onus is on client code to choose. ZIP_32 has greater support but is limited to 4GiB (gibibyte), while ZIP_64 has less support, but has a much greater limit of 16EiB (exbibyte). These limits apply to both the compressed and uncompressed sizes of each member file.
