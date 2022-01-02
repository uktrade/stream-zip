from collections import deque
from struct import Struct
import zlib

NO_COMPRESSION = object()
ZIP = object()
ZIP64 = object()

def stream_zip(files, chunk_size=65536):

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
        data_descriptor_zip64_struct = Struct('<IQQ')
        data_descriptor_zip_struct = Struct('<III')

        central_directory_header_signature = b'PK\x01\x02'
        central_directory_header_struct = Struct('<HH2sH4sIIIHHHHHII')

        zip64_end_of_central_directory_signature = b'PK\x06\x06'
        zip64_end_of_central_directory_struct = Struct('<QHHIIQQQQ')

        zip64_end_of_central_directory_locator_signature= b'PK\x06\x07'
        zip64_end_of_central_directory_locator_struct = Struct('<IQI')

        end_of_central_directory_signature = b'PK\x05\x06'
        end_of_central_directory_struct = Struct('<HHHHIIH')
        
        zip64_extra_signature = b'\x01\x00'
        zip64_local_extra_struct = Struct('<2sHQQ')
        zip64_central_directory_extra_struct = Struct('<2sHQQQ')

        modified_at_struct = Struct('<HH')

        central_directory = deque()
        offset = 0

        def _(chunk):
            nonlocal offset
            offset += len(chunk)
            yield chunk

        def _zip64_local_header_and_data(name_encoded, mod_at_encoded, external_attr, chunks):
            file_offset = offset

            extra = zip64_local_extra_struct.pack(
                zip64_extra_signature,
                16,  # Size of extra
                0,   # Uncompressed size - since data descriptor
                0,   # Compressed size - since data descriptor
            )
            yield from _(local_header_signature)
            yield from _(local_header_struct.pack(
                45,           # Version
                b'\x08\x00',  # Flags - data descriptor
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

            uncompressed_size, compressed_size, crc_32 = yield from _zip_or_zip64_data(
                chunks,
                max_uncompressed_size=0xffffffffffffffff,
                max_compressed_size=0xffffffffffffffff,
            )

            yield from _(data_descriptor_signature)
            yield from _(data_descriptor_zip64_struct.pack(crc_32, compressed_size, uncompressed_size))

            extra = zip64_central_directory_extra_struct.pack(
                zip64_extra_signature,
                24,  # Size of extra
                uncompressed_size,
                compressed_size,
                file_offset,
            )
            return central_directory_header_struct.pack(
                45,           # Version made by
                45,           # Version required
                b'\x08\x00',  # Flags - data descriptor
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

        def _zip_local_header_and_data(name_encoded, mod_at_encoded, external_attr, chunks):
            file_offset = offset

            yield from _(local_header_signature)
            yield from _(local_header_struct.pack(
                20,           # Version
                b'\x08\x00',  # Flags - data descriptor
                8,            # Compression - deflate
                mod_at_encoded,
                0,            # CRC32 - 0 since data descriptor
                0,            # Compressed size - 0 since data descriptor
                0,            # Uncompressed size - 0 since data descriptor
                len(name_encoded),
                0,            # Length of local extra
            ))
            yield from _(name_encoded)

            uncompressed_size, compressed_size, crc_32 = yield from _zip_or_zip64_data(
                chunks,
                max_uncompressed_size=0xffffffff,
                max_compressed_size=0xffffffff,
            )

            yield from _(data_descriptor_signature)
            yield from _(data_descriptor_zip_struct.pack(crc_32, compressed_size, uncompressed_size))

            extra = b''
            return central_directory_header_struct.pack(
                20,           # Version made by
                20,           # Version required
                b'\x08\x00',  # Flags - data descriptor
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

        def _zip_or_zip64_data(chunks, max_uncompressed_size, max_compressed_size):
            # The data is identical for ZIP and ZIP64

            uncompressed_size = 0
            compressed_size = 0
            crc_32 = zlib.crc32(b'')
            compress_obj = zlib.compressobj(wbits=-zlib.MAX_WBITS, level=9)
            for chunk in evenly_sized(chunks):
                uncompressed_size += len(chunk)

                if uncompressed_size > max_uncompressed_size:
                    raise UncompressedSizeOverflowError()

                crc_32 = zlib.crc32(chunk, crc_32)
                compressed_chunk = compress_obj.compress(chunk)
                compressed_size += len(compressed_chunk)

                if compressed_size > max_compressed_size:
                    raise CompressedSizeOverflowError()

                yield from _(compressed_chunk)

            compressed_chunk = compress_obj.flush()
            compressed_size += len(compressed_chunk)
            yield from _(compressed_chunk)

            return uncompressed_size, compressed_size, crc_32

        def _uncompressed_local_header_and_data(name_encoded, mod_at_encoded, external_attr, chunks):
            file_offset = offset

            # We cannot have a data descriptor, and so have to be able to determine the total
            # length and CRC32 before output ofchunks to client code
            chunks = tuple(chunks)
            uncompressed_size = 0
            compressed_size = 0
            crc_32 = zlib.crc32(b'')
            for chunk in chunks:
                crc_32 = zlib.crc32(chunk, crc_32)
                uncompressed_size += len(chunk)
            compressed_size = uncompressed_size
            needs_zip64 = uncompressed_size >= 0xffffffff or file_offset >= 0xffffffff

            def _with_zip64():
                extra = zip64_local_extra_struct.pack(
                    zip64_extra_signature,
                    16,  # Size of extra
                    uncompressed_size,
                    compressed_size,
                )
                yield from _(local_header_signature)
                yield from _(local_header_struct.pack(
                    45,           # Version
                    b'\x00\x00',  # Flags
                    0,            # Compression - no compression
                    mod_at_encoded,
                    crc_32,
                    0xffffffff,
                    0xffffffff,
                    len(name_encoded),
                    len(extra),
                ))
                yield from _(name_encoded)
                yield from _(extra)

                for chunk in chunks:
                    yield from _(chunk)

                extra = zip64_central_directory_extra_struct.pack(
                    zip64_extra_signature,
                    24,  # Size of extra
                    uncompressed_size,
                    compressed_size,
                    file_offset,
                )
                return central_directory_header_struct.pack(
                   45,           # Version made by
                   45,           # Version required
                   b'\x00\x00',  # Flags
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

            def _without_zip64():
                extra = b''
                yield from _(local_header_signature)
                yield from _(local_header_struct.pack(
                    20,           # Version
                    b'\x00\x00',  # Flags
                    0,            # Compression - no compression
                    mod_at_encoded,
                    crc_32,
                    compressed_size,
                    uncompressed_size,
                    len(name_encoded),
                    len(extra),
                ))
                yield from _(name_encoded)
                yield from _(extra)

                for chunk in chunks:
                    yield from _(chunk)

                return central_directory_header_struct.pack(
                   20,           # Version made by
                   20,           # Version required
                   b'\x00\x00',  # Flags
                   0,            # Compression - none
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

            return \
                _with_zip64() if needs_zip64 else \
                _without_zip64()

        for name, modified_at, perms, method, chunks in files:
            name_encoded = name.encode()
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
                _zip64_local_header_and_data if method is ZIP64 else \
                _zip_local_header_and_data if method is ZIP else \
                _uncompressed_local_header_and_data
            central_directory.append((yield from data_func(name_encoded, mod_at_encoded, external_attr, chunks)))

        central_directory_start_offset = offset

        for central_directory_header_entry, name_encoded, extra in central_directory:
            yield from _(central_directory_header_signature)
            yield from _(central_directory_header_entry)
            yield from _(name_encoded)
            yield from _(extra)

        central_directory_end_offset = offset
        central_directory_size = central_directory_end_offset - central_directory_start_offset

        needs_zip64_end_of_central_directory = \
            len(central_directory) >= 0xffff or \
            central_directory_size >= 0xffffffff or \
            central_directory_start_offset >= 0xffffffff

        if needs_zip64_end_of_central_directory:
            yield from _(zip64_end_of_central_directory_signature)
            yield from _(zip64_end_of_central_directory_struct.pack(
                44,  # Size of zip64 end of central directory record
                45,  # Version made by
                45,  # Version required
                0,   # Disk number
                0,   # Disk number with central directory
                len(central_directory),  # On this disk
                len(central_directory),  # In total
                central_directory_size,
                central_directory_start_offset,
            ))

            yield from _(zip64_end_of_central_directory_locator_signature)
            yield from _(zip64_end_of_central_directory_locator_struct.pack(
                0,  # Disk number with zip64 end of central directory record
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
                0,           # ZIP file comment length
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
                0, # ZIP file comment length
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
