from struct import Struct


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
                4294967295,         # Compressed size - 0 since zip64
                4294967295,         # Uncompressed size - 0 since zip64
                len(name_encoded),
                len(extra),
            )
            directory.append((name_encoded, modified_at))
            yield name_encoded
            yield extra
            yield from chunks

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
