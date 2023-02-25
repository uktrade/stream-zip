# Recipes

stream-zip takes as input one or more member files as an iterable of tuples, and outputs a single ZIP file as an interable that yields bytes. stream-zip does not ship with code to convert between these and other common structures. However, this page contains recipes that you can take and modify for your case.


## Input recipes

### Named local files

```python
from datetime import datetime
from stream_zip import ZIP_32, stream_zip

def local_files(names):
    now  = datetime.now()

    def contents(name):
        with open(name, 'rb') as f:
            while chunk := f.read(65536):
                yield chunk

    return (
        (name, now, 0o600, ZIP_32, contents(name))
        for name in names
    )

names = ('file-1.txt', 'file-2.txt')
zipped_chunks = stream_zip(local_files(names))
```

## Output recipes

### File-like object

If you need to output a file-like object rather than an iterable yielding bytes, you can pass the return value of `stream_zip` through `to_file_like_obj` defined as below.

```python
def to_file_like_obj(iterable):
    chunk = b''
    offset = 0
    it = iter(iterable)

    def up_to_iter(size):
        nonlocal chunk, offset

        while size:
            if offset == len(chunk):
                try:
                    chunk = next(it)
                except StopIteration:
                    break
                else:
                    offset = 0
            to_yield = min(size, len(chunk) - offset)
            offset = offset + to_yield
            size -= to_yield
            yield chunk[offset - to_yield:offset]

    class FileLikeObj:
        def read(self, size=-1):
            return b''.join(up_to_iter(float('inf') if size is None or size < 0 else size))

    return FileLikeObj()
```


### Upload to S3

The file-like object above can be used to upload large ZIP files to S3 using [boto3's upload_fileobj](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.upload_fileobj), which splits larger files into multipart uploads.

```python
import boto3
from boto3.s3.transfer import TransferConfig

zipped_chunks = stream_zip(unzipped_files())
zipped_chunks_obj = to_file_like_obj(zipped_chunks)

s3 = boto3.client('s3')
s3.upload_fileobj(
    zipped_chunks_obj, 'mybucket', 'mykey',
    # Since we're streaming the final total size is unknown, so we have to tell boto3 what part
    # size to use to accomodate the entire file - S3 has a hard coded limit of 10000 parts
    # In this example we choose a part size of 200MB, so 2TB maximum final object size
    Config=TransferConfig(multipart_chunksize=1024 * 1024 * 200),
)
```