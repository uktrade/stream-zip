---
layout: sub-navigation
sectionKey: Features
order: 2
title: Features
---

In addition to being memory efficient (with some [limitations](/features/limitations/)) stream-zip:

- Constructs ZIP files that can be stream unzipped, for example by [stream-unzip](https://stream-unzip.docs.trade.gov.uk/)

- Can construct Zip64 ZIP files. Zip64 ZIP files allow sizes far beyond the approximate 4GiB limit of the original ZIP format

- Can construct ZIP files that contain symbolic links

- Can construct ZIP files that contain directories, including empty directories

- Can construct password protected / AES-256 encrypted ZIP files adhering to the [WinZip AE-2 specification](https://www.winzip.com/en/support/aes-encryption/).

- Allows the specification of permissions on the member files and directories (although not all clients respect them)

- By default stores modification time as an extended timestamp. An extended timestamp is a more accurate timestamp than the original ZIP format allows

- Provides an async interface (that uses threads under the hood)