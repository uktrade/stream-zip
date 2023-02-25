# Exceptions

Exceptions raised by the source iterables are passed through the `stream_zip` function to client code unchanged. Other exceptions are in the `stream_zip` module and derive from `stream_zip.ZipError`.

## Exception hierarchy

  - **ZipError**

    Base class for all explicitly-thrown exceptions

    - **ZipValueError** (also inherits from the **ValueError** built-in)

        Base class for errors relating to invalid arguments

          - **ZipOverflowError** (also inherits from the **OverflowError** built-in)

            The size or positions of data in the ZIP are too large to store in the requested mode

            - **UncompressedSizeOverflowError**

                The uncompressed size of a member file is too large. The maximum uncompressed size for ZIP_32 mode is 2^32 - 1 bytes, and for ZIP_64 mode is 2^64 - 1 bytes.

            - **CompressedSizeOverflowError**

                The compressed size of a member file is too large. The maximum compressed size for ZIP_32 mode is 2^32 - 1 bytes, and for ZIP_64 mode is 2^64 - 1 bytes.

            - **CentralDirectorySizeOverflowError**

                The size of the central directory, a section at the end of the ZIP that lists all the member files. The maximum size for ZIP_32 mode is 2^32 - 1 bytes, and for ZIP_64 mode is 2^64 - 1 bytes.

                If any `_64` mode files are in the ZIP, the central directory is in ZIP_64 mode, and ZIP_32 mode otherwise.

            - **CentralDirectoryNumberOfEntriesOverflowError**

                Too many entries in the central directory, a section at the end of the ZIP that lists all the member files. The limit for ZIP_32 mode is 2^16 - 1 entries, and for ZIP_64 mode is 2^64 - 1 entries.

                If any `_64` mode files are in the ZIP, the central directory is in ZIP_64 mode, and ZIP_32 mode otherwise.

            - **OffsetOverflowError**

                The offset of data in the ZIP is too high, i.e. the ZIP is too large. The limit for ZIP_32 mode is 2^32 - 1 bytes, and for ZIP_64 mode is 2^64 - 1 bytes.

                This can be raised when stream-zip adds member files, or when it adds the central directory at the end of the ZIP file. If any `_64` mode files are in the ZIP, the central directory is in ZIP_64 mode, and ZIP_32 mode otherwise.

                It is possible for the ZIP file to be larger than the maximum allowed offset without this exception being thrown. For example in ZIP_32 mode the archive can can be larger than 2^32 - 1 bytes.

            - **NameLengthOverflowError**

                The length of a file name is too high. The limit is 2^16 - 1 bytes, and applied to file names after UTF-8 encoding.
