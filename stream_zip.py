from collections import deque
from struct import Struct
import zlib

_NO_COMPRESSION_32 = object()
_NO_COMPRESSION_64 = object()
_ZIP_32 = object()
_ZIP_64 = object()

_AUTO_UPGRADE_CENTRAL_DIRECTORY = object()
_NO_AUTO_UPGRADE_CENTRAL_DIRECTORY = object()

def NO_COMPRESSION_32(offset, default_get_compressobj):
    return _NO_COMPRESSION_32, _NO_AUTO_UPGRADE_CENTRAL_DIRECTORY, default_get_compressobj

def NO_COMPRESSION_64(offset, default_get_compressobj):
    return _NO_COMPRESSION_64, _NO_AUTO_UPGRADE_CENTRAL_DIRECTORY, default_get_compressobj

def ZIP_32(offset, default_get_compressobj):
    return _ZIP_32, _NO_AUTO_UPGRADE_CENTRAL_DIRECTORY, default_get_compressobj

def ZIP_64(offset, default_get_compressobj):
    return _ZIP_64, _NO_AUTO_UPGRADE_CENTRAL_DIRECTORY, default_get_compressobj

def ZIP_AUTO(uncompressed_size, level=9):
    def method_compressobj(offset, default_get_compressobj):
        # The limit of 4293656841 is calculated using the logic from a zlib function
        # https://github.com/madler/zlib/blob/04f42ceca40f73e2978b50e93806c2a18c1281fc/deflate.c#L696
        # Specifically, worked out by assuming the compressed size of a stream cannot be bigger than
        #
        # uncompressed_size + (uncompressed_size >> 12) + (uncompressed_size >> 14) + (uncompressed_size >> 25) + 7
        #
        # This is the 0.03% deflate bound for memLevel of 8 default abs(wbits) = MAX_WBITS
        #
        # Note that Python's interaction with zlib is not consistent between versions of Python
        # https://stackoverflow.com/q/76371334/1319998
        # so Python could be causing extra deflate-chunks output which could break the limit. However, couldn't
        # get output of sized 4293656841 to break the Zip32 bound of 0xffffffff here for any level, including 0
        method = _ZIP_64 if uncompressed_size > 4293656841 or offset > 0xffffffff else _ZIP_32
        return (method, _AUTO_UPGRADE_CENTRAL_DIRECTORY, lambda: zlib.compressobj(level=level, memLevel=8, wbits=-zlib.MAX_WBITS))
    return method_compressobj


def stream_zip(files, chunk_size=65536, get_compressobj=lambda: zlib.compressobj(wbits=-zlib.MAX_WBITS, level=9)):

    def evenly_sized(chunks):
        chunk = b''
        offset = 0
        it = iter(chunks)

        def up_to(num):
            nonlocal chunk, offset

            while num:
                if offset == len(chunk):
                    try:
                        chunk = next(it)
                    except StopIteration:
                        break
                    else:
                        offset = 0
                to_yield = min(num, len(chunk) - offset)
                offset = offset + to_yield
                num -= to_yield
                yield chunk[offset - to_yield:offset]

        while True:
            block = b''.join(up_to(chunk_size))
            if not block:
                break
            yield block

    def get_zipped_chunks_uneven():
        local_header_signature = b'PK\x03\x04'
        local_header_struct = Struct('<H2sH4sIIIHH')

        data_descriptor_signature = b'PK\x07\x08'
        data_descriptor_zip_64_struct = Struct('<IQQ')
        data_descriptor_zip_32_struct = Struct('<III')

        central_directory_header_signature = b'PK\x01\x02'
        central_directory_header_struct = Struct('<BBBB2sH4sIIIHHHHHII')

        zip_64_end_of_central_directory_signature = b'PK\x06\x06'
        zip_64_end_of_central_directory_struct = Struct('<QHHIIQQQQ')

        zip_64_end_of_central_directory_locator_signature= b'PK\x06\x07'
        zip_64_end_of_central_directory_locator_struct = Struct('<IQI')

        end_of_central_directory_signature = b'PK\x05\x06'
        end_of_central_directory_struct = Struct('<HHHHIIH')
        
        zip_64_extra_signature = b'\x01\x00'
        zip_64_local_extra_struct = Struct('<2sHQQ')
        zip_64_central_directory_extra_struct = Struct('<2sHQQQ')

        modified_at_struct = Struct('<HH')

        central_directory = deque()
        central_directory_size = 0
        central_directory_start_offset = 0
        zip_64_central_directory = False
        offset = 0

        def _(chunk):
            nonlocal offset
            offset += len(chunk)
            yield chunk

        def _raise_if_beyond(offset, maximum, exception_class):
            if offset > maximum:
                raise exception_class()

        def _zip_64_local_header_and_data(name_encoded, mod_at_encoded, external_attr, _get_compress_obj, chunks):
            file_offset = offset

            _raise_if_beyond(file_offset, maximum=0xffffffffffffffff, exception_class=OffsetOverflowError)

            extra = zip_64_local_extra_struct.pack(
                zip_64_extra_signature,
                16,  # Size of extra
                0,   # Uncompressed size - since data descriptor
                0,   # Compressed size - since data descriptor
            )
            yield from _(local_header_signature)
            yield from _(local_header_struct.pack(
                45,           # Version
                b'\x08\x08',  # Flags - data descriptor and utf-8 file names
                8,            # Compression - deflate
                mod_at_encoded,
                0,            # CRC32 - 0 since data descriptor
                0xffffffff,   # Compressed size - since zip64
                0xffffffff,   # Uncompressed size - since zip64
                len(name_encoded),
                len(extra),
            ))
            yield from _(name_encoded)
            yield from _(extra)

            uncompressed_size, compressed_size, crc_32 = yield from _zip_data(
                chunks,
                _get_compress_obj,
                max_uncompressed_size=0xffffffffffffffff,
                max_compressed_size=0xffffffffffffffff,
            )

            yield from _(data_descriptor_signature)
            yield from _(data_descriptor_zip_64_struct.pack(crc_32, compressed_size, uncompressed_size))

            extra = zip_64_central_directory_extra_struct.pack(
                zip_64_extra_signature,
                24,  # Size of extra
                uncompressed_size,
                compressed_size,
                file_offset,
            )
            return central_directory_header_struct.pack(
                45,           # Version made by
                3,            # System made by (UNIX)
                45,           # Version required
                0,            # Reserved
                b'\x08\x08',  # Flags - data descriptor and utf-8 file names
                8,            # Compression - deflate
                mod_at_encoded,
                crc_32,
                0xffffffff,   # Compressed size - since zip64
                0xffffffff,   # Uncompressed size - since zip64
                len(name_encoded),
                len(extra),
                0,            # File comment length
                0,            # Disk number
                0,            # Internal file attributes - is binary
                external_attr,
                0xffffffff,   # Offset of local header - since zip64
            ), name_encoded, extra

        def _zip_32_local_header_and_data(name_encoded, mod_at_encoded, external_attr, _get_compress_obj, chunks):
            file_offset = offset

            _raise_if_beyond(file_offset, maximum=0xffffffff, exception_class=OffsetOverflowError)

            yield from _(local_header_signature)
            yield from _(local_header_struct.pack(
                20,           # Version
                b'\x08\x08',  # Flags - data descriptor and utf-8 file names
                8,            # Compression - deflate
                mod_at_encoded,
                0,            # CRC32 - 0 since data descriptor
                0,            # Compressed size - 0 since data descriptor
                0,            # Uncompressed size - 0 since data descriptor
                len(name_encoded),
                0,            # Length of local extra
            ))
            yield from _(name_encoded)

            uncompressed_size, compressed_size, crc_32 = yield from _zip_data(
                chunks,
                _get_compress_obj,
                max_uncompressed_size=0xffffffff,
                max_compressed_size=0xffffffff,
            )

            yield from _(data_descriptor_signature)
            yield from _(data_descriptor_zip_32_struct.pack(crc_32, compressed_size, uncompressed_size))

            extra = b''
            return central_directory_header_struct.pack(
                20,           # Version made by
                3,            # System made by (UNIX)
                20,           # Version required
                0,            # Reserved
                b'\x08\x08',  # Flags - data descriptor and utf-8 file names
                8,            # Compression - deflate
                mod_at_encoded,
                crc_32,
                compressed_size,
                uncompressed_size,
                len(name_encoded),
                len(extra),
                0,            # File comment length
                0,            # Disk number
                0,            # Internal file attributes - is binary
                external_attr,
                file_offset,
            ), name_encoded, extra

        def _zip_data(chunks, _get_compress_obj, max_uncompressed_size, max_compressed_size):
            uncompressed_size = 0
            compressed_size = 0
            crc_32 = zlib.crc32(b'')
            compress_obj = _get_compress_obj()
            for chunk in chunks:
                uncompressed_size += len(chunk)

                _raise_if_beyond(uncompressed_size, maximum=max_uncompressed_size, exception_class=UncompressedSizeOverflowError)

                crc_32 = zlib.crc32(chunk, crc_32)
                compressed_chunk = compress_obj.compress(chunk)
                compressed_size += len(compressed_chunk)

                _raise_if_beyond(compressed_size, maximum=max_compressed_size, exception_class=CompressedSizeOverflowError)

                yield from _(compressed_chunk)

            compressed_chunk = compress_obj.flush()
            compressed_size += len(compressed_chunk)

            _raise_if_beyond(compressed_size, maximum=max_compressed_size, exception_class=CompressedSizeOverflowError)

            yield from _(compressed_chunk)

            return uncompressed_size, compressed_size, crc_32

        def _no_compression_64_local_header_and_data(name_encoded, mod_at_encoded, external_attr, _get_compress_obj, chunks):
            file_offset = offset

            _raise_if_beyond(file_offset, maximum=0xffffffffffffffff, exception_class=OffsetOverflowError)

            chunks, size, crc_32 = _no_compression_buffered_data_size_crc_32(chunks, maximum_size=0xffffffffffffffff)

            extra = zip_64_local_extra_struct.pack(
                zip_64_extra_signature,
                16,    # Size of extra
                size,  # Uncompressed
                size,  # Compressed
            )
            yield from _(local_header_signature)
            yield from _(local_header_struct.pack(
                45,           # Version
                b'\x00\x08',  # Flags - utf-8 file names
                0,            # Compression - no compression
                mod_at_encoded,
                crc_32,
                0xffffffff,   # Compressed size - since zip64
                0xffffffff,   # Uncompressed size - since zip64
                len(name_encoded),
                len(extra),
            ))
            yield from _(name_encoded)
            yield from _(extra)

            for chunk in chunks:
                yield from _(chunk)

            extra = zip_64_central_directory_extra_struct.pack(
                zip_64_extra_signature,
                24,    # Size of extra
                size,  # Uncompressed
                size,  # Compressed
                file_offset,
            )
            return central_directory_header_struct.pack(
               45,           # Version made by
               3,            # System made by (UNIX)
               45,           # Version required
               0,            # Reserved
               b'\x00\x08',  # Flags - utf-8 file names
               0,            # Compression - none
               mod_at_encoded,
               crc_32,
               0xffffffff,   # Compressed size - since zip64
               0xffffffff,   # Uncompressed size - since zip64
               len(name_encoded),
               len(extra),
               0,            # File comment length
               0,            # Disk number
               0,            # Internal file attributes - is binary
               external_attr,
               0xffffffff,   # File offset - since zip64
            ), name_encoded, extra


        def _no_compression_32_local_header_and_data(name_encoded, mod_at_encoded, external_attr, _get_compress_obj, chunks):
            file_offset = offset

            _raise_if_beyond(file_offset, maximum=0xffffffff, exception_class=OffsetOverflowError)

            chunks, size, crc_32 = _no_compression_buffered_data_size_crc_32(chunks, maximum_size=0xffffffff)

            extra = b''
            yield from _(local_header_signature)
            yield from _(local_header_struct.pack(
                20,           # Version
                b'\x00\x08',  # Flags - utf-8 file names
                0,            # Compression - no compression
                mod_at_encoded,
                crc_32,
                size,         # Compressed
                size,         # Uncompressed
                len(name_encoded),
                len(extra),
            ))
            yield from _(name_encoded)
            yield from _(extra)

            for chunk in chunks:
                yield from _(chunk)

            return central_directory_header_struct.pack(
               20,           # Version made by
               3,            # System made by (UNIX)
               20,           # Version required
               0,            # Reserved
               b'\x00\x08',  # Flags - utf-8 file names
               0,            # Compression - none
               mod_at_encoded,
               crc_32,
               size,         # Compressed
               size,         # Uncompressed
               len(name_encoded),
               len(extra),
               0,            # File comment length
               0,            # Disk number
               0,            # Internal file attributes - is binary
               external_attr,
               file_offset,
            ), name_encoded, extra

        def _no_compression_buffered_data_size_crc_32(chunks, maximum_size):
            # We cannot have a data descriptor, and so have to be able to determine the total
            # length and CRC32 before output ofchunks to client code

            size = 0
            crc_32 = zlib.crc32(b'')

            def _chunks():
                nonlocal size, crc_32
                for chunk in chunks:
                    size += len(chunk)
                    _raise_if_beyond(size, maximum=maximum_size, exception_class=UncompressedSizeOverflowError)
                    crc_32 = zlib.crc32(chunk, crc_32)
                    yield chunk

            chunks = tuple(_chunks())

            return chunks, size, crc_32

        for name, modified_at, perms, method, chunks in files:
            _method, _auto_upgrade_central_directory, _get_compress_obj = method(offset, get_compressobj)

            name_encoded = name.encode('utf-8')
            _raise_if_beyond(len(name_encoded), maximum=0xffff, exception_class=NameLengthOverflowError)

            mod_at_encoded = modified_at_struct.pack(
                int(modified_at.second / 2) | \
                (modified_at.minute << 5) | \
                (modified_at.hour << 11),
                modified_at.day | \
                (modified_at.month << 5) | \
                (modified_at.year - 1980) << 9,
            )
            external_attr = \
                (perms << 16) | \
                (0x10 if name_encoded[-1:] == b'/' else 0x0)  # MS-DOS directory

            data_func = \
                _zip_64_local_header_and_data if _method is _ZIP_64 else \
                _zip_32_local_header_and_data if _method is _ZIP_32 else \
                _no_compression_64_local_header_and_data if _method is _NO_COMPRESSION_64 else \
                _no_compression_32_local_header_and_data

            central_directory_header_entry, name_encoded, extra = yield from data_func(name_encoded, mod_at_encoded, external_attr, _get_compress_obj, evenly_sized(chunks))
            central_directory_size += len(central_directory_header_signature) + len(central_directory_header_entry) + len(name_encoded) + len(extra)
            central_directory.append((central_directory_header_entry, name_encoded, extra))

            zip_64_central_directory = zip_64_central_directory \
                or (_auto_upgrade_central_directory is _AUTO_UPGRADE_CENTRAL_DIRECTORY and offset > 0xffffffff) \
                or (_auto_upgrade_central_directory is _AUTO_UPGRADE_CENTRAL_DIRECTORY and len(central_directory) > 0xffff) \
                or _method in (_ZIP_64, _NO_COMPRESSION_64)

            max_central_directory_length, max_central_directory_start_offset, max_central_directory_size = \
                (0xffffffffffffffff, 0xffffffffffffffff, 0xffffffffffffffff) if zip_64_central_directory else \
                (0xffff, 0xffffffff, 0xffffffff)

            central_directory_start_offset = offset
            central_directory_end_offset = offset + central_directory_size

            _raise_if_beyond(central_directory_start_offset, maximum=max_central_directory_start_offset, exception_class=OffsetOverflowError)
            _raise_if_beyond(len(central_directory), maximum=max_central_directory_length, exception_class=CentralDirectoryNumberOfEntriesOverflowError)
            _raise_if_beyond(central_directory_size, maximum=max_central_directory_size, exception_class=CentralDirectorySizeOverflowError)
            _raise_if_beyond(central_directory_end_offset, maximum=0xffffffffffffffff, exception_class=OffsetOverflowError)

        for central_directory_header_entry, name_encoded, extra in central_directory:
            yield from _(central_directory_header_signature)
            yield from _(central_directory_header_entry)
            yield from _(name_encoded)
            yield from _(extra)

        if zip_64_central_directory:
            yield from _(zip_64_end_of_central_directory_signature)
            yield from _(zip_64_end_of_central_directory_struct.pack(
                44,  # Size of zip_64 end of central directory record
                45,  # Version made by
                45,  # Version required
                0,   # Disk number
                0,   # Disk number with central directory
                len(central_directory),  # On this disk
                len(central_directory),  # In total
                central_directory_size,
                central_directory_start_offset,
            ))

            yield from _(zip_64_end_of_central_directory_locator_signature)
            yield from _(zip_64_end_of_central_directory_locator_struct.pack(
                0,  # Disk number with zip_64 end of central directory record
                central_directory_end_offset,
                1   # Total number of disks
            ))

            yield from _(end_of_central_directory_signature)
            yield from _(end_of_central_directory_struct.pack(
                0xffff,      # Disk number - since zip64
                0xffff,      # Disk number with central directory - since zip64
                0xffff,      # Number of central directory entries on this disk - since zip64
                0xffff,      # Number of central directory entries in total - since zip64
                0xffffffff,  # Central directory size - since zip64
                0xffffffff,  # Central directory offset - since zip64
                0,           # ZIP_32 file comment length
            ))
        else:
            yield from _(end_of_central_directory_signature)
            yield from _(end_of_central_directory_struct.pack(
                0,  # Disk number
                0,  # Disk number with central directory
                len(central_directory),  # On this disk
                len(central_directory),  # In total
                central_directory_size,
                central_directory_start_offset,
                0, # ZIP_32 file comment length
            ))

    zipped_chunks = get_zipped_chunks_uneven()
    yield from evenly_sized(zipped_chunks)


class ZipError(Exception):
    pass


class ZipValueError(ZipError, ValueError):
    pass


class ZipOverflowError(ZipValueError, OverflowError):
    pass


class UncompressedSizeOverflowError(ZipOverflowError):
    pass


class CompressedSizeOverflowError(ZipOverflowError):
    pass


class CentralDirectorySizeOverflowError(ZipOverflowError):
    pass


class OffsetOverflowError(ZipOverflowError):
    pass


class CentralDirectoryNumberOfEntriesOverflowError(ZipOverflowError):
    pass


class NameLengthOverflowError(ZipOverflowError):
    pass
