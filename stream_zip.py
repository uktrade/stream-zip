def stream_zip(files):
    for name, modified_at, chunks in files:
        yield from chunks
