def stream_zip(files, chunk_size=65536):

    def get_zipped_chunks_uneven():
        local_signature = b'\x50\x4b\x03\x04'
        directory = []

        for name, modified_at, chunks in files:
            yield local_signature
            name_encoded = name.encode()
            directory.append((name_encoded, modified_at))
            yield name_encoded
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
