# Storage — S3 connector

This folder contains the S3-backed file manager used by the project. The main implementation is `s3_manager.S3FileManager`, which implements the abstract API in `base_manager.AbstractFileManager`.

## Quick summary of available operations

### Methods in `S3FileManager`:

#### Bucket management

- `verify_bucket()`: check whether the configured bucket exists and is accessible.
- `create_bucket(bucket_name: Optional[str] = None)`: create the configured or given bucket.
- `delete_bucket(bucket_name: str)`: delete the given bucket (must not be the current one).
- `list_buckets() -> List[str]`: list all accessible buckets.
- `set_bucket(bucket_name: str)`: set the current bucket (creates it if it does not exist).
- `get_bucket() -> str `: get the current bucket.

#### File and directory operations

- `upload_file(local_path: str, remote_path: str)`: upload a local file to the remote path in the bucket.
- `download_file(remote_path: str, local_path: str)`: download a file from the bucket to a local path.
- `delete_file(remote_path: str)`: delete a file from the bucket.
- `list_files(prefix: str = "") -> List[str]`: list all files in the bucket with the given prefix.
- `create_directory(path: str)`: create a virtual directory in the bucket.
- `delete_directory(path: str)`: delete a virtual directory and its contents from the bucket.

## Usage

### Environment variables

- `AWS_ACCESS_KEY_ID` — AWS access key ID
- `AWS_SECRET_ACCESS_KEY` — AWS secret access key
- `S3_BUCKET_NAME` — default bucket name used by the manager
- `AWS_REGION` — AWS region to use (default: `eu-central-1` in code)
- `SCAYLE_S3_ENDPOINT` — custom S3 endpoint used by Scayle (optional)
- `AWS_S3_ENDPOINT` — alternative env name used for local testing (overrides SCAYLE_S3_ENDPOINT)

### Sample `.env` configuration

```sh
AWS_ACCESS_KEY_ID=YOUR_KEY
AWS_SECRET_ACCESS_KEY=YOUR_SECRET
S3_BUCKET_NAME=my-demo-bucket
AWS_REGION=eu-central-1
AWS_S3_ENDPOINT=http://localhost:4566   # optional, for localstack
```

## Getting started

```python
from storage.s3_manager import S3FileManager
import os

bucket = os.getenv("S3_BUCKET_NAME", "my-demo-bucket")
m = S3FileManager(bucket_name=bucket)

# upload
m.upload_file("local/path/file.csv", "remote/path/file.csv")

# list
print(m.list_files("remote/path/"))

# download
m.download_file("remote/path/file.csv", "local/path/downloaded.csv")

# delete
m.delete_file("remote/path/file.csv")
```

Environment / CLI examples (Linux/Mac)

```bash
# export env vars in shell
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export S3_BUCKET_NAME=my-demo-bucket
export AWS_REGION= <region name> # eu-central-1

# for localstack testing
export AWS_S3_ENDPOINT=http://localhost:4566

# run a small test using python -c
python -c "from storage.s3_manager import S3FileManager; import os; m=S3FileManager(os.getenv('S3_BUCKET_NAME')); print(m.list_buckets())"
```

## Unit tests (mocked)
A set of unit tests that mock boto3 is provided at:

- `storage/tests/test_s3_manager.py`

Run tests:

```bash
# run all tests
pytest -q

# or run only storage tests
pytest -q storage/tests/test_s3_manager.py
```

> Notes on tests:

Tests use `unittest.mock` to patch `boto3.client` and simulate responses and errors.
They validate behaviour for bucket verification/creation, file upload/download/delete, listing, directory create/delete and bucket deletion guard.


## Notes and tips

- The manager will attempt to verify the configured bucket at initialization and create it if it does not exist (creation respects AWS_REGION when present).
- For local testing (LocalStack) set AWS_S3_ENDPOINT (or SCAYLE_S3_ENDPOINT) to your local endpoint and provide credentials.
- The implementation uses boto3 with S3 signature version `s3v4`.
- Errors and operations are logged using the logger from `AbstractFileManager`. You can pass your own logger to the constructor.
