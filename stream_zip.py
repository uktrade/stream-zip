from struct import Struct
import zlib


def stream_zip(files, chunk_size=65536):

    def get_zipped_chunks_uneven():
        local_header_signature = b'PK\x03\x04'
        data_descriptor_signature = b'PK\x07\x08'
        central_directory_header_signature = b'PK\x01\x02'
        zip64_end_of_central_directory_signature = b'PK\x06\x06'
        zip64_end_of_central_directory_locator_signature= b'PK\x06\x07'
        end_of_central_directory_signature = b'PK\x05\x06'
        data_descriptor_struct = Struct('<IQQ')
        zip64_extra_signature = b'\x01\x00'
        zip64_extra_struct = Struct('<HQQQI')
        local_header_struct = Struct('<H2sHHHIIIHH')
        central_directory_file_header_struct = Struct('<HH2sHHHIIIHHHHHII')
        zip64_end_of_central_directory_struct = Struct('<QHHIIQQQQ')
        zip64_end_of_central_directory_locator = Struct('<IQI')
        end_of_central_directory_struct = Struct('<HHHHIIH')
        directory = []

        offset = 0

        def _(chunk):
            nonlocal offset
            offset += len(chunk)
            yield chunk

        for name, modified_at, chunks in files:
            file_offset = offset
            name_encoded = name.encode()
            local_extra = \
                zip64_extra_signature + \
                zip64_extra_struct.pack(
                    28,
                    0,  # Uncompressed sizes - 0 since data descriptor
                    0,  # Compressed size - 0 since data descriptor
                    file_offset,
                    0   # Disk number
                )
            yield from _(local_header_signature)
            yield from _(local_header_struct.pack(
                45,                 # Version
                b'\x08\x00',        # Flags - data descriptor
                8,                  # Compression - deflate
                0,                  # Modification time
                0,                  # Modification date
                0,                  # CRC32 - 0 since data descriptor
                4294967295,         # Compressed size - since zip64
                4294967295,         # Uncompressed size - since zip64
                len(name_encoded),
                len(local_extra),
            ))
            yield from _(name_encoded)
            yield from _(local_extra)

            uncompressed_size = 0
            compressed_size = 0
            crc_32 = zlib.crc32(b'')
            compress_obj = zlib.compressobj(wbits=-zlib.MAX_WBITS, level=9)
            for chunk in chunks:
                uncompressed_size += len(chunk)
                crc_32 = zlib.crc32(chunk, crc_32)
                compressed_chunk = compress_obj.compress(chunk)
                compressed_size += len(compressed_chunk)
                yield from _(compressed_chunk)

            compressed_chunk = compress_obj.flush()
            if compressed_chunk:
                compressed_size += len(compressed_chunk)
                yield from _(compressed_chunk)

            yield from _(data_descriptor_signature)
            yield from _(data_descriptor_struct.pack(crc_32, compressed_size, uncompressed_size))

            directory.append((file_offset, name_encoded, modified_at, compressed_size, uncompressed_size, crc_32))

        central_directory_start_offset = offset

        for file_offset, name_encoded, modified_at, compressed_size, uncompressed_size, crc_32 in directory:
            yield from _(central_directory_header_signature)
            directory_extra = \
                zip64_extra_signature + \
                zip64_extra_struct.pack(
                    28,
                    uncompressed_size,
                    compressed_size,
                    file_offset,
                    0  # Disk number
                )
            yield from _(central_directory_file_header_struct.pack(
                45,                 # Version
                45,                 # Version
                b'\x08\x00',        # Flags - data descriptor
                8,                  # Compression - deflate
                0,                  # Modification time
                0,                  # Modification date
                crc_32,             # CRC32 - 0 since data descriptor
                4294967295,         # Compressed size - since zip64
                4294967295,         # Uncompressed size - since zip64
                len(name_encoded),
                len(directory_extra),
                0,                  # File comment length
                0xffff,             # Disk number - sinze zip64
                0,                  # Internal file attributes - is binary
                0,                  # External file attributes
                0xffffffff,         # Offset of local header - sinze zip64
            ))
            yield from _(name_encoded)
            yield from _(directory_extra)

        central_directory_end_offset = offset
        central_directory_size = central_directory_end_offset - central_directory_start_offset

        zip64_end_of_central_directory_offset = offset

        yield from _(zip64_end_of_central_directory_signature)
        yield from _(zip64_end_of_central_directory_struct.pack(
            44,            # Size of zip64 end of central directory record
            45,            # Version
            45,            # Version
            0,             # Disk number
            0,             # Disk number with central directory
            len(directory),
            len(directory),
            central_directory_size,
            central_directory_start_offset,
        ))

        yield from _(zip64_end_of_central_directory_locator_signature)
        yield from _(zip64_end_of_central_directory_locator.pack(
            0,  # Disk number with zip64 end of central directory record
            zip64_end_of_central_directory_offset,
            1   # Total number of disks
        ))

        yield from _(end_of_central_directory_signature)
        yield from _(end_of_central_directory_struct.pack(
            0xffff,      # Since zip64
            0xffff,      # Since zip64
            0xffff,      # Since zip64
            0xffff,      # Since zip64
            0xffffffff,  # Since zip64
            0xffffffff,  # Since zip64
            0,           # ZIP file comment length
        ))

    def get_zipped_chunks_even(zipped_chunks):
        chunk = b''
        offset = 0
        it = iter(zipped_chunks)

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

    zipped_chunks = get_zipped_chunks_uneven()
    yield from get_zipped_chunks_even(zipped_chunks)
