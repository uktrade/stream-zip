from struct import Struct
import zlib


def stream_zip(files, chunk_size=65536):

    def get_zipped_chunks_uneven():
        local_header_signature = b'\x50\x4b\x03\x04'
        zip64_size_signature = b'\x01\x00'
        local_header_struct = Struct('<H2sHHHIIIHH')
        directory = []

        for name, modified_at, chunks in files:
            name_encoded = name.encode()
            extra = \
                zip64_size_signature + \
                Struct('<H').pack(16) + \
                Struct('<QQ').pack(0, 0)  # Compressed and uncompressed sizes, 0 since data descriptor
            yield local_header_signature
            yield local_header_struct.pack(
                45,                 # Version
                b'\x08\x00',        # Flags - data descriptor
                8,                  # Compression - deflate
                0,                  # Modification time
                0,                  # Modification date
                0,                  # CRC32 - 0 since data descriptor
                4294967295,         # Compressed size - since zip64
                4294967295,         # Uncompressed size - since zip64
                len(name_encoded),
                len(extra),
            )
            yield name_encoded
            yield extra

            uncompressed_size = 0
            compressed_size = 0
            crc_32 = zlib.crc32(b'')
            compress_obj = zlib.compressobj(wbits=15, level=9)
            for chunk in chunks:
                uncompressed_size += len(chunk)
                crc_32 = zlib.crc32(chunk, crc_32)
                compressed_chunk = compress_obj.compress(chunk)
                compressed_size += len(compressed_chunk)
                yield compressed_chunk

            compressed_chunk = compress_obj.flush()
            if compressed_chunk:
                compressed_size += len(compressed_chunk)
                yield compressed_chunk

            directory.append((name_encoded, modified_at))

        for name, modified_at in directory:
            yield name
            yield str(modified_at).encode()

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
