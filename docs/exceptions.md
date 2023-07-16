# Exceptions

Exceptions raised by the source iterables are passed through the `stream_zip` function to client code unchanged. Other exceptions are in the `stream_zip` module and derive from `stream_zip.ZipError`.

## Exception hierarchy

  - **ZipError**

    Base class for all explicitly-thrown exceptions

    - **ZipValueError** (also inherits from the **ValueError** built-in)

        Base class for errors relating to invalid arguments

          - **ZipIntegrityError**

            An integrity check failed

            - **CRC32IntegrityError**

                The CRC32 calculated from data did not match the CRC32 passed into the method

            - **UncompressedSizeIntegrityError**

                The uncompressed size of data did not match the uncompressed size passed into the method

          - **ZipOverflowError** (also inherits from the **OverflowError** built-in)

            The size or positions of data in the ZIP are too large to store using the requested method

            - **UncompressedSizeOverflowError**

                The uncompressed size of a member file is too large. For a `*_32` member file the maximum uncompressed size is 2^32 - 1 bytes, and for a `*_64` member file the maximum uncompressed size is 2^64 - 1 bytes.

            - **CompressedSizeOverflowError**

                The compressed size of a member file is too large. For a `*_32` member file the maximum compressed size is 2^32 - 1 bytes, and for a `*_64` member file the maximum compressed size is 2^64 - 1 bytes.

            - **CentralDirectorySizeOverflowError**

                The central directory, a section at the end of the ZIP that lists all the member files, is too large. The maximum size of the central directory if there are only `*_32` member files is 2^32 - 1 bytes. If there are any `*_64` member files the maximum size is 2^64 - 1 bytes.

            - **CentralDirectoryNumberOfEntriesOverflowError**

                The central directory, a section at the end of the ZIP that lists all the member files, has too many entries. If there are only `*_32` member files the maximum number of entries is 2^16 - 1. If there are any `*_64` member files, the maximum number of entries is 2^64 - 1.

            - **OffsetOverflowError**

                The offset of data in the ZIP is too high, i.e. the ZIP is too large. If there are only `*_32` member files the maximum offset is 2^32 - 1 bytes. If there are any `*_64` member files the maximum offset is 2^64 - 1 bytes.

                This can be raised when stream-zip adds member files, or when it adds the central directory at the end of the ZIP file.

                Due to the nature of the ZIP file format, it is possible for the ZIP file to be larger than the maximum allowed offset without this exception being thrown. For example, even if there are only `*_32` member files, the archive can be larger than 2^32 - 1 bytes.

            - **NameLengthOverflowError**

                The length of a file name is too high. The limit is 2^16 - 1 bytes, and applied to file names after UTF-8 encoding. This is the limit whether or not there are any `*_64` member files.
