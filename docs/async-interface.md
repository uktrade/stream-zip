---
layout: sub-navigation
order: 7
title: Async interface
---


stream-zip does not include an async interface. However, it is possible to construct an async function that wraps stream-zip to allow the construction of zip files in a streaming way from async code without blocking the event loop.

```python
import asyncio
from stream_zip import stream_zip

async def async_stream_zip(member_files, *args, **kwargs):

    async def to_async_iterable(sync_iterable):
        # to_thread errors if StopIteration raised in it. So we use a sentinel to detect the end
        done = object()
        it = iter(sync_iterable)
        while (value := await asyncio.to_thread(next, it, done)) is not done:
            yield value

    def to_sync_iterable(async_iterable):
        done = object()
        async_it = aiter(async_iterable)
        while (value := asyncio.run_coroutine_threadsafe(anext(async_it, done), loop).result()) is not done:
            yield value

    loop = asyncio.get_running_loop()
    sync_member_files = (
        member_file[0:4] + (to_sync_iterable(member_file[4],),)
        for member_file in to_sync_iterable(member_files)
    )

    async for chunk in to_async_iterable(stream_zip(sync_member_files, *args, **kwargs)):
        yield chunk
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