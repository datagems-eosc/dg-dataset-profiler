# ...existing code...
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError

from storage.s3_manager import S3FileManager


def make_client_mock():
    m = MagicMock()
    # sensible defaults
    m.head_bucket.return_value = None
    m.create_bucket.return_value = {}
    m.list_buckets.return_value = {"Buckets": [{"Name": "a"}, {"Name": "b"}]}
    m.upload_file.return_value = None
    m.download_file.return_value = None
    m.delete_object.return_value = {}
    m.list_objects_v2.return_value = {"Contents": [{"Key": "file1"}, {"Key": "file2"}]}
    m.put_object.return_value = {}
    m.delete_objects.return_value = {}
    m.delete_bucket.return_value = {}

    # default paginator that yields a single page with the same contents as list_objects_v2
    paginator_mock = MagicMock()
    paginator_mock.paginate.return_value = [
        {"Contents": [{"Key": "file1"}, {"Key": "file2"}]}
    ]
    m.get_paginator.return_value = paginator_mock

    return m


@patch("storage.s3_manager.boto3.client")
def test_init_uses_existing_bucket_when_head_succeeds(mock_boto_client):
    mock_client = make_client_mock()
    mock_boto_client.return_value = mock_client

    mgr = S3FileManager(bucket_name="existing-bucket")

    # head_bucket should have been called for verification
    mock_client.head_bucket.assert_called_with(Bucket="existing-bucket")
    # create_bucket should NOT be called because head_bucket succeeded
    assert not mock_client.create_bucket.called
    assert mgr.get_bucket() == "existing-bucket"


@patch("storage.s3_manager.boto3.client")
def test_init_creates_bucket_when_missing(mock_boto_client):
    mock_client = make_client_mock()

    # simulate head_bucket raising a 404 ClientError for missing bucket
    err_response = {"Error": {"Code": "404", "Message": "Not Found"}}

    def head_bucket_side_effect(**kwargs):
        raise ClientError(err_response, "HeadBucket")

    mock_client.head_bucket.side_effect = head_bucket_side_effect

    mock_boto_client.return_value = mock_client

    mgr = S3FileManager(bucket_name="missing-bucket")

    # verify that create_bucket was attempted
    assert mock_client.create_bucket.called
    # if create_bucket succeeded, manager.bucket_name should be set
    assert mgr.get_bucket() == "missing-bucket"


@patch("storage.s3_manager.boto3.client")
def test_list_buckets_returns_names(mock_boto_client):
    mock_client = make_client_mock()
    mock_boto_client.return_value = mock_client

    mgr = S3FileManager(bucket_name="bucket")
    buckets = mgr.list_buckets()
    assert buckets == ["a", "b"]


@patch("storage.s3_manager.boto3.client")
def test_upload_download_delete_and_list_files(mock_boto_client):
    mock_client = make_client_mock()
    # configure paginator to return specific contents for list_files
    paginator_mock = MagicMock()
    paginator_mock.paginate.return_value = [
        {"Contents": [{"Key": "p1"}, {"Key": "p2"}]}
    ]
    mock_client.get_paginator.return_value = paginator_mock
    mock_boto_client.return_value = mock_client

    mgr = S3FileManager(bucket_name="my-bucket")

    # upload_file should forward args to boto3 client.upload_file
    mgr.upload_file("local/file.txt", "remote/file.txt")
    mock_client.upload_file.assert_called_with(
        "local/file.txt", "my-bucket", "remote/file.txt"
    )

    # download_file should forward args
    mgr.download_file("remote/file.txt", "local/downloaded.txt")
    mock_client.download_file.assert_called_with(
        "my-bucket", "remote/file.txt", "local/downloaded.txt"
    )

    # delete_file should call delete_object with Bucket and Key
    mgr.delete_file("remote/file.txt")
    mock_client.delete_object.assert_called_with(
        Bucket="my-bucket", Key="remote/file.txt"
    )

    # list_files should return the keys from paginator
    files = mgr.list_files(prefix="p")
    assert files == ["p1", "p2"]
    mock_client.get_paginator.assert_called_with("list_objects_v2")
    paginator_mock.paginate.assert_called_with(Bucket="my-bucket", Prefix="p")


@patch("storage.s3_manager.boto3.client")
def test_create_and_delete_directory(mock_boto_client):
    mock_client = make_client_mock()
    # for delete_directory, return some objects
    mock_client.list_objects_v2.return_value = {
        "Contents": [{"Key": "dir/file1"}, {"Key": "dir/file2"}]
    }
    mock_boto_client.return_value = mock_client

    mgr = S3FileManager(bucket_name="dir-bucket")

    # create_directory ensures trailing slash and calls put_object
    mgr.create_directory("dir")
    mock_client.put_object.assert_called_with(Bucket="dir-bucket", Key="dir/")

    # delete_directory should list objects and then call delete_objects with proper payload
    mgr.delete_directory("dir")
    mock_client.list_objects_v2.assert_called_with(Bucket="dir-bucket", Prefix="dir/")
    expected_delete = {"Objects": [{"Key": "dir/file1"}, {"Key": "dir/file2"}]}
    mock_client.delete_objects.assert_called_with(
        Bucket="dir-bucket", Delete=expected_delete
    )


@patch("storage.s3_manager.boto3.client")
def test_delete_directory_no_contents(mock_boto_client):
    mock_client = make_client_mock()
    # simulate no contents in the directory
    mock_client.list_objects_v2.return_value = {}
    mock_boto_client.return_value = mock_client

    mgr = S3FileManager(bucket_name="empty-bucket")

    # should not raise and should not call delete_objects
    mgr.delete_directory("empty")
    mock_client.delete_objects.assert_not_called()


@patch("storage.s3_manager.boto3.client")
def test_delete_bucket_behaviour(mock_boto_client):
    mock_client = make_client_mock()
    mock_boto_client.return_value = mock_client

    mgr = S3FileManager(bucket_name="current-bucket")

    # attempt to delete the current bucket -> should NOT call delete_bucket on client
    mgr.delete_bucket("current-bucket")
    mock_client.delete_bucket.assert_not_called()

    # deleting a different bucket should call client.delete_bucket
    mgr.delete_bucket("other-bucket")
    mock_client.delete_bucket.assert_called_with(Bucket="other-bucket")


@patch("storage.s3_manager.boto3.client")
def test_set_bucket_creates_or_sets_based_on_existence(mock_boto_client):
    mock_client = make_client_mock()

    # head_bucket: return success for 'exists-bucket', raise 404 for others
    def head_bucket_side_effect(**kwargs):
        if kwargs.get("Bucket") == "exists-bucket":
            return None
        raise ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket"
        )

    mock_client.head_bucket.side_effect = head_bucket_side_effect
    mock_boto_client.return_value = mock_client

    mgr = S3FileManager(bucket_name="initial-bucket")

    # setting to an existing bucket should set without creating
    mgr.set_bucket("exists-bucket")
    assert mgr.get_bucket() == "exists-bucket"

    # setting to a non-existent bucket should trigger create_bucket
    mgr.set_bucket("new-bucket")
    assert mock_client.create_bucket.called


@patch("storage.s3_manager.boto3.client")
def test_upload_file_handles_file_not_found_and_no_credentials(mock_boto_client):
    mock_client = make_client_mock()

    # simulate FileNotFoundError raised by boto3 client's upload_file
    mock_client.upload_file.side_effect = FileNotFoundError()
    mock_boto_client.return_value = mock_client

    mgr = S3FileManager(bucket_name="b")

    # Should not raise despite FileNotFoundError being raised internally
    mgr.upload_file("missing", "remote")
    # simulate ClientError for upload (e.g., forbidden)
    mock_client.upload_file.side_effect = ClientError(
        {"Error": {"Code": "403", "Message": "Forbidden"}}, "Upload"
    )
    mgr.upload_file("some", "remote")  # will be caught and logged
