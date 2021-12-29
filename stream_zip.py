def stream_zip(files, chunk_size=65536):

    def get_zipped_chunks_uneven():
        for name, modified_at, chunks in files:
            yield from chunks

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
