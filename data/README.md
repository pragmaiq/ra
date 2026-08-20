# Data

This directory contains the source `.jsonl` files and the output cleaned raw data. By default, all the `.jsonl` files are ignore, due that they're too large (for our case specifically). The pipeline works with multiple files at the same time, we're defining the files within an environment variable `DATA_FILES=file1.jsonl,file2.jsonl,...` and the output file is by default `raw.jsonl`.