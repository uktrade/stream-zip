---
layout: sub-navigation
sectionKey: Get started
caption: Get started
eleventyNavigation:
    parent: Get started
order: 4
title: Output examples
---


This page contains examples to show how the output of stream-zip can be manipulated for different cases. It is likely you will have to modifiy them for your specific needs.

The examples assume an iterable of member files is available in the variable `member_files`. See [Get started](/get-started/) for a guide on how to construct this, or [Input examples](/input-examples/) for examples.


## Local file

Saving the ZIP to a local file can be done wtih Python's built-in `open` function.

```python
from stream_zip import stream_zip

zipped_chunks = stream_zip(member_files)
with open('my.zip', 'wb') as f:
    for chunk in zipped_chunks:
        f.write(chunk)
```


## File-like object

If you need to output a file-like object rather than an iterable yielding bytes, you can pass the return value of `stream_zip` through the `to_file_like_obj` function from [to-file-like-obj](https://github.com/uktrade/to-file-like-obj).

```python
from stream_zip import stream_zip
from to_file_like_obj import to_file_like_obj

zipped_chunks = stream_zip(member_files)
zipped_chunks_obj = to_file_like_obj(zipped_chunks)
```


## Upload to S3

The `to_file_like_obj` function from [to-file-like-obj](https://github.com/uktrade/to-file-like-obj) can be used to upload large ZIP files to S3 with [boto3's upload_fileobj](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.upload_fileobj).

```python
import boto3
from boto3.s3.transfer import TransferConfig
from stream_zip import stream_zip
from to_file_like_obj import to_file_like_obj

zipped_chunks = stream_zip(member_files)
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


## Submit your own

Pull requests (PRs) that propose changes to this page are especially welcome. PRs can be made at the [source of this page](https://github.com/uktrade/stream-zip/blob/main/docs/output-examples.md). Submitting a PR requires a [GitHub account](https://github.com/join) and knowledge of the [GitHub fork and PR process](https://docs.github.com/en/pull-requests).
