# Async Interface

stream-zip does not include an async interface. However, it is possible to construct an async function that wraps stream-zip to allow the construction of zip files in a streaming way from async code without blocking the event loop.

```python
import asyncio
from stream_zip import stream_zip

async def async_stream_zip(async_member_files, *args, **kwargs):

    def sync_iterable(async_iterable):
        async_it = aiter(async_iterable)
        while True:
            try:
                yield asyncio.run_coroutine_threadsafe(anext(async_it), loop).result()
            except StopAsyncIteration:
                break

    def sync_member_files():
        for member_file in sync_iterable(async_member_files):
            yield member_file[0:4] + (sync_iterable(member_file[4],),)

    # to_thread raises an error if StopIteration raised in it
    def to_thread_safe_next():
        try:
            return next(zipped_chunks_it)
        except StopIteration:
            return done

    loop = asyncio.get_event_loop()
    zipped_chunks_it = iter(stream_zip(sync_member_files(), *args, **kwargs))
    done = object()

    while True:
        value = await asyncio.to_thread(to_thread_safe_next)
        if value is done:
            break
        yield value
```

The above allows the member files to be supplied by an async iterable, and the data of each member file to be supplied by an async iterable.

```python
from datetime import datetime
from stat import S_IFREG
from stream_zip import ZIP_32

# Hard coded for example purposes
async def get_async_data():
    yield b'Some bytes 1'
    yield b'Some bytes 2'

# Hard coded for example purposes
async def get_async_member_files():
    yield (
        'my-file-1.txt',     
        datetime.now(),      
        S_IFREG | 0o600,
        ZIP_32,              
        get_async_data(),
    )
    yield (
        'my-file-2.txt',     
        datetime.now(),      
        S_IFREG | 0o600,
        ZIP_32,              
        get_async_data(),
    )

async def main():
    async for chunk in async_stream_zip(get_async_member_files()):
        print(chunk)

asyncio.run(main())
```