---
layout: sub-navigation
sectionKey: Get started
eleventyNavigation:
    parent: Get started
caption: Get started
order: 2
title: Limitations
---


The `NO_COMPRESSION_32` and `NO_COMPRESSION_64` methods do not stream - they buffer the entire binary contents of the file in memory before output. They do this to calculate the length and CRC 32 to output them before the binary contents in the ZIP. This is required in order for ZIP to be stream unzippable.

However, if you are able to calculate the length and CRC 32 ahead of time, you can pass `NO_COMPRESSION_32(uncompressed_size, crc_32)` or`NO_COMPRESSION_64(uncompressed_size, crc_32)` as the method. These methods do not buffer the binary contents in memory, and so are streaming methods. See [Methods](/methods/) for details of all supported methods.

Note that even for the streaming methods, it's not possible to _completely_ stream-write ZIP files. Small bits of metadata for each member file, such as its name, must be placed at the _end_ of the ZIP. In order to do this, stream-zip buffers this metadata in memory until it can be output. This is likely to only to make a meaningful difference to memory usage for extremely high numbers of member files.
