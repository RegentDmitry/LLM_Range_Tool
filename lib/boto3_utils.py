import boto3, os
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config
import config.credentialsprivate as credentialsprivate
import threading

_s3_client = None
_dynamodb_client = None
_client_lock = threading.RLock()


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        with _client_lock:
            if _s3_client is None:
                config = Config(
                    max_pool_connections=100,
                    retries={
                        'max_attempts': 3,
                        'mode': 'adaptive'
                    },
                    region_name=getattr(credentialsprivate, 'AwsRegion'),
                    connect_timeout=10,
                    read_timeout=30
                )

                _s3_client = boto3.client(
                    's3',
                    aws_access_key_id=getattr(credentialsprivate, 'AwsAccessKey'),
                    aws_secret_access_key=getattr(credentialsprivate, 'AwsSecret'),
                    config=config
                )
    return _s3_client


def _get_dynamodb_client():
    global _dynamodb_client
    if _dynamodb_client is None:
        with _client_lock:
            if _dynamodb_client is None:
                config = Config(
                    max_pool_connections=50,
                    retries={
                        'max_attempts': 3,
                        'mode': 'adaptive'
                    },
                    region_name=getattr(credentialsprivate, 'AwsRegion'),
                    connect_timeout=10,
                    read_timeout=30
                )

                _dynamodb_client = boto3.client(
                    'dynamodb',
                    aws_access_key_id=getattr(credentialsprivate, 'AwsAccessKey'),
                    aws_secret_access_key=getattr(credentialsprivate, 'AwsSecret'),
                    config=config
                )
    return _dynamodb_client


def upload_file_to_s3(file_path, bucket_name, object_name):
    s3_client = _get_s3_client()

    try:
        extra_args = {}
        if file_path.endswith('.gz'):
            extra_args['ContentEncoding'] = 'gzip'

        s3_client.upload_file(file_path, bucket_name, object_name, ExtraArgs=extra_args)
        return True
    except FileNotFoundError:
        print(f"File {file_path} not found")
        return False
    except ClientError as e:
        print(f"Error uploading file: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def download_file_from_s3(bucket_name, s3_file_key, local_path):
    try:
        s3_client = _get_s3_client()

        try:
            s3_client.head_object(Bucket=bucket_name, Key=s3_file_key)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                raise

        folder = os.path.dirname(local_path)
        os.makedirs(folder, exist_ok=True)

        s3_client.download_file(
            bucket_name,
            s3_file_key,
            local_path
        )

        return True

    except NoCredentialsError:
        print("[S3] Error: AWS credentials not found")
        return False
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            print(f"Error: Bucket '{bucket_name}' not found")
        else:
            print(f"Client error: {e}")
        return False
    except Exception as e:
        print(f"Unknown error: {e}")
        return False


def list_files_in_bucket(bucket_name, prefix=None, suffix=None):
    s3_client = _get_s3_client()

    try:
        files = []
        paginator = s3_client.get_paginator('list_objects_v2')

        paginate_kwargs = {'Bucket': bucket_name}
        if prefix:
            paginate_kwargs['Prefix'] = prefix

        for page in paginator.paginate(**paginate_kwargs):
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    if suffix is None or key.endswith(suffix):
                        files.append(key)

        if not files:
            prefix_msg = f" with prefix '{prefix}'" if prefix else ""
            suffix_msg = f" with suffix '{suffix}'" if suffix else ""
            print(f"No files found in bucket {bucket_name}{prefix_msg}{suffix_msg}")

        return files

    except ClientError as e:
        print(f"Error listing files: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []


def get_dynamodb_record(table_name, primary_id, key):
    dynamodb_client = _get_dynamodb_client()

    response = dynamodb_client.get_item(
        TableName=table_name,
        Key={
            f'{primary_id}': {'S': f'{key}'}
        }
    )

    if 'Item' in response:
        return response['Item']
    else:
        return None

def delete_dynamodb_record(table_name, primary_id, key):
   dynamodb_client = _get_dynamodb_client()

   response = dynamodb_client.delete_item(
       TableName=table_name,
       Key={
           f'{primary_id}': {'S': f'{key}'}
       }
   )

   return response


def get_all_dynamodb_keys(table_name, primary_key_name):
   dynamodb_client = _get_dynamodb_client()

   keys = []
   last_evaluated_key = None

   while True:
       scan_kwargs = {
           'TableName': table_name,
           'ProjectionExpression': primary_key_name
       }

       if last_evaluated_key:
           scan_kwargs['ExclusiveStartKey'] = last_evaluated_key

       response = dynamodb_client.scan(**scan_kwargs)

       if 'Items' in response:
           for item in response['Items']:
               keys.append(item[primary_key_name]['S'])

       last_evaluated_key = response.get('LastEvaluatedKey')
       if not last_evaluated_key:
           break

   return keys
def delete_s3(bucket_name, file_key):
    try:
        s3_client = _get_s3_client()
        s3_client.delete_object(Bucket=bucket_name, Key=file_key)
        return True
    except ClientError as e:
        print(f"Error deleting file {file_key}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error deleting file {file_key}: {e}")
        return False


__all__ = ['list_files_in_bucket', 'download_file_from_s3', 'upload_file_to_s3', 'get_dynamodb_record', 'get_all_dynamodb_keys', 'delete_s3', 'delete_dynamodb_record']

if __name__ == '__main__':
    print('hi')