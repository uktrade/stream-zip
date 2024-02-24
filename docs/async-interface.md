---
layout: sub-navigation
order: 7
title: Async interface
---


An async interface is provided via the function `async_stream_zip`. Its usage is exactly the same as `stream_zip` except that:

1. The member files must be provided as an async iterable of tuples.
2. The data of each member file must be provided as an async iterable of bytes.
3. Its return value is an async iterable of bytes.

```python
from datetime import datetime
from stat import S_IFREG
from stream_zip import async_stream_zip, ZIP_32

# Hard coded for example purposes
async def async_data():
    yield b'Some bytes 1'
    yield b'Some bytes 2'

# Hard coded for example purposes
async def async_member_files():
    yield (
        'my-file-1.txt',     
        datetime.now(),      
        S_IFREG | 0o600,
        ZIP_32,              
        async_data(),
    )
    yield (
        'my-file-2.txt',     
        datetime.now(),      
        S_IFREG | 0o600,
        ZIP_32,              
        async_data(),
    )

async def main():
    async for chunk in async_stream_zip(async_member_files()):
        print(chunk)

asyncio.run(main())
```

> ### Warnings
>
> Under the hood `async_stream_zip` uses threads as a layer over the synchronous `stream_zip` function. This has two consequences:
>
> 1. A possible performance penalty over a theoretical implementation that is pure async without threads.
>
> 2. The [contextvars](https://docs.python.org/3/library/contextvars.html) context available in the async iterables of files or data is a shallow copy of the context where async_stream_zip is called from.
>
>   This means that existing context variables are available inside the iterables, but any changes made to the context itself from inside the iterables will not propagate out to the original context. Changes made to mutable data structures that are part of the context, for example dictionaries, will propagate out.
>
>   This does not affect Python 3.6, because contextvars is not available.
