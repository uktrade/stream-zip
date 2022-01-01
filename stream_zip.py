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
        zip64_extra_struct = Struct('<HQQQI')

        modified_at_struct = Struct('<HH')

        directory = deque()
        offset = 0

        def _(chunk):
            nonlocal offset
            offset += len(chunk)
            yield chunk

        for name, modified_at, perms, method, chunks in files:

            file_offset = offset
            name_encoded = name.encode()
            mod_at_encoded = modified_at_struct.pack(
                int(modified_at.second / 2) | \
                (modified_at.minute << 5) | \
                (modified_at.hour << 11),
                modified_at.day | \
                (modified_at.month << 5) | \
                (modified_at.year - 1980) << 9,
            )

            if method == ZIP64:
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
                    0,            # Length of local extra
                ))
                yield from _(name_encoded)
            elif method == ZIP:
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
            else:
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
                extra = \
                    (
                        zip64_extra_signature + \
                        zip64_extra_struct.pack(
                            28,  # Size of extra
                            uncompressed_size,
                            compressed_size,
                            file_offset,
                            0,   # Disk number
                        )
                    ) if needs_zip64 else \
                    b''
                yield from _(local_header_signature)
                yield from _(local_header_struct.pack(
                    20,           # Version
                    b'\x00\x00',  # Flags
                    0,            # Compression - no compression
                    mod_at_encoded,
                    crc_32,
                    0xffffffff if needs_zip64 else compressed_size,
                    0xffffffff if needs_zip64 else uncompressed_size,
                    len(name_encoded),
                    len(extra),
                ))
                yield from _(name_encoded)
                yield from _(extra)

            if method in (ZIP64, ZIP):
                uncompressed_size = 0
                compressed_size = 0
                crc_32 = zlib.crc32(b'')
                compress_obj = zlib.compressobj(wbits=-zlib.MAX_WBITS, level=9)
                for chunk in evenly_sized(chunks):
                    uncompressed_size += len(chunk)
                    crc_32 = zlib.crc32(chunk, crc_32)
                    compressed_chunk = compress_obj.compress(chunk)
                    compressed_size += len(compressed_chunk)
                    yield from _(compressed_chunk)

                compressed_chunk = compress_obj.flush()
                compressed_size += len(compressed_chunk)
                yield from _(compressed_chunk)

                data_descriptor_struct = \
                    data_descriptor_zip64_struct if method is ZIP64 else \
                    data_descriptor_zip_struct

                yield from _(data_descriptor_signature)
                yield from _(data_descriptor_struct.pack(crc_32, compressed_size, uncompressed_size))
            else:
                for chunk in chunks:
                    yield from _(chunk)

            directory.append((file_offset, name_encoded, mod_at_encoded, perms, method, compressed_size, uncompressed_size, crc_32))

        central_directory_start_offset = offset

        for file_offset, name_encoded, mod_at_encoded, perms, method, compressed_size, uncompressed_size, crc_32 in directory:

            external_attr = \
                (perms << 16) | \
                (0x10 if name_encoded[-1:] == b'/' else 0x0)  # MS-DOS directory

            if method == ZIP64:
                extra = \
                    zip64_extra_signature + \
                    zip64_extra_struct.pack(
                        28,  # Size of extra
                        uncompressed_size,
                        compressed_size,
                        file_offset,
                        0,   # Disk number
                    )
                yield from _(central_directory_header_signature)
                yield from _(central_directory_header_struct.pack(
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
                    0xffff,       # Disk number - since zip64
                    0,            # Internal file attributes - is binary
                    external_attr,
                    0xffffffff,   # Offset of local header - since zip64
                ))
                yield from _(name_encoded)
                yield from _(extra)
            elif method == ZIP:
                extra = b''
                yield from _(central_directory_header_signature)
                yield from _(central_directory_header_struct.pack(
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
                    0,            # Disk number - since zip64
                    0,            # Internal file attributes - is binary
                    external_attr,
                    file_offset,  # Offset of local header - since zip64
                ))
                yield from _(name_encoded)
                yield from _(extra)
            else:
                needs_zip64 = uncompressed_size >= 0xffffffff or file_offset >= 0xffffffff
                extra = \
                    (
                        zip64_extra_signature + \
                        zip64_extra_struct.pack(
                            28,  # Size of extra
                            uncompressed_size,
                            compressed_size,
                            file_offset,
                            0,   # Disk number
                        )
                    ) if needs_zip64 else \
                    b''
                yield from _(central_directory_header_signature)
                yield from _(central_directory_header_struct.pack(
                    20,           # Version made by
                    20,           # Version required
                    b'\x00\x00',  # Flags
                    0,            # Compression - none
                    mod_at_encoded,
                    crc_32,
                    0xffffffff if needs_zip64 else compressed_size,
                    0xffffffff if needs_zip64 else uncompressed_size,
                    len(name_encoded),
                    len(extra),
                    0,            # File comment length
                    0,            # Disk number - since zip64
                    0,            # Internal file attributes - is binary
                    external_attr,
                    0xffffffff if needs_zip64 else file_offset,
                ))
                yield from _(name_encoded)
                yield from _(extra)

        central_directory_end_offset = offset
        central_directory_size = central_directory_end_offset - central_directory_start_offset

        needs_zip64_end_of_central_directory = \
            len(directory) >= 0xffff or \
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
                len(directory),  # On this disk
                len(directory),  # In total
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
                len(directory),  # On this disk
                len(directory),  # In total
                central_directory_size,
                central_directory_start_offset,
                0, # ZIP file comment length
            ))

    zipped_chunks = get_zipped_chunks_uneven()
    yield from evenly_sized(zipped_chunks)
