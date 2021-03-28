import hashlib
import tempfile
import pyzipper as pyz
import boto3
from botocore.errorfactory import ClientError
from pathlib import Path

def fingerprint(file_path):
  return md5(open(file_path, 'rb').read())

def b(s):
  """converts to bytes"""
  try:
    return s.encode() # convert to bytes
  except (UnicodeEncodeError, AttributeError):
    return s # already bytes

def md5(content):
  return hashlib.md5(b(content)).hexdigest()

def combined_fingerprint(files):
  prints = [fingerprint(f) for f in files]
  return md5("-".join(prints))

def encrypted_zip(files, out_path, password):
  with pyz.AESZipFile(out_path, 'w', compression=pyz.ZIP_LZMA, encryption=pyz.WZ_AES) as z:
    z.setpassword(password)
    for f in files:
      z.write(f, f.name)
  return out_path

def children(dir_path):
  dirs, files = [], []
  for p in dir_path.glob("*"):
    if p.is_dir():
      dirs.append(p)
    else:
      files.append(p)
  return dirs, files

def encrypted_backup(dir_path, password, bucket="my_bucket", base_path=None, **kwargs):
  dir_path = Path(dir_path)
  assert dir_path.is_dir(), "must be a directory"
  password = b(password)
  dirs, files = children(dir_path)

  if base_path is None:
    base_path = Path(dir_path.name)
    log_title("backing up: {}".format(base_path))
  else:
    base_path = base_path / dir_path.name

  for d in dirs:
    encrypted_backup(d, password, bucket=bucket, base_path=base_path, **kwargs)

  if len(files) == 0:
    return

  fingerprint = combined_fingerprint(files)
  fname = fingerprint + ".zip"
  key = str(Path(base_path)/fname)
  if s3_object_exists(bucket, key):
    log_step(dir_path, "\t OK")
    return


  with tempfile.TemporaryDirectory() as tmp_dir:
    z = encrypted_zip(files, Path(tmp_dir)/fname, password)
    log_step(dir_path, "\t-> {}/{}".format(bucket, key))
    backup(z, bucket, key, **kwargs)

def bucket_key(base_path, child_path):
  """
  Removes parent's directory path from children
  Example:
  >>> origin_path = Path("/tmp/dump")
  >>> child_path = Path("/tmp/dump/recursive/example")
  >>> bucket_key(origin_path, child_path)
  >>> 'recursive/example'
  """
  if origin_path == child_path:
    return origin_path.name
  else:
    return str(child_path).replace(str(origin_path), "")[1:]

def backup(src_path, bucket, key, backup_type="s3"):
  if backup_type == "s3":
    s3_backup(src_path, bucket, key)
  else:
    local_backup(src_path, bucket, key)

def s3_backup(src_path, bucket, key):
  path = Path(key)
  folder = str(path.parent)
  fname = path.name

  # Don't do anything if fingerprinted zip already uploaded
  if s3_object_exists(bucket, key):
      return

  # Remove outdated zips
  for x in get_matching_s3_keys(bucket, prefix=folder):
    x = Path(x)

    if str(x.parent) == str(folder) and x.name != fname:
      s3_delete_file(bucket, key)


  # Upload latest zip.
  s3_upload(src_path, bucket, key)

def s3_delete_file(bucket, key):
  s3 = boto3.resource('s3')
  s3.Object(bucket, key).delete()

def s3_upload(src_path, bucket, key):
  src_path = str(src_path)
  s3_client = boto3.client('s3')
  s3_client.upload_file(src_path, bucket, key)

def s3_object_exists(bucket, key):
  s3 = boto3.client('s3')
  try:
    s3.head_object(Bucket=bucket, Key=key)
    return True
  except ClientError:
    # Not found
    return False

def local_backup(src_path, bucket, key):
  """useful for testing"""
  import shutil
  path = Path("/tmp")/bucket/key
  path.parent.mkdir(parents=True, exist_ok=True)
  shutil.copy(src_path, path)

def log_title(*args):
  print("=>", *args)

def log_step(*args):
  args = [str(a) for a in args]
  print("+ {: <40} {: >40}".format(*args))

# --- kudos to https://alexwlchan.net/2019/07/listing-s3-keys/

def get_matching_s3_objects(bucket, prefix="", suffix=""):
  """
  Generate objects in an S3 bucket.

  :param bucket: Name of the S3 bucket.
  :param prefix: Only fetch objects whose key starts with
      this prefix (optional).
  :param suffix: Only fetch objects whose keys end with
      this suffix (optional).
  """
  s3 = boto3.client("s3")
  paginator = s3.get_paginator("list_objects_v2")

  kwargs = {'Bucket': bucket}

  # We can pass the prefix directly to the S3 API.  If the user has passed
  # a tuple or list of prefixes, we go through them one by one.
  if isinstance(prefix, str):
    prefixes = (prefix, )
  else:
    prefixes = prefix

  for key_prefix in prefixes:
    kwargs["Prefix"] = key_prefix

    for page in paginator.paginate(**kwargs):
      try:
        contents = page["Contents"]
      except KeyError:
        break

      for obj in contents:
        key = obj["Key"]
        if key.endswith(suffix):
          yield obj


def get_matching_s3_keys(bucket, prefix="", suffix=""):
  """
  Generate the keys in an S3 bucket.

  :param bucket: Name of the S3 bucket.
  :param prefix: Only fetch keys that start with this prefix (optional).
  :param suffix: Only fetch keys that end with this suffix (optional).
  """
  for obj in get_matching_s3_objects(bucket, prefix, suffix):
    yield obj["Key"]
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='encrypt and backup your files to the cloud')
    parser.add_argument("bucket", help="aws bucket")
    parser.add_argument("password", help="files will be encrypted with this password")
    args = parser.parse_args()


    # files should be volume mounted to /data
    encrypted_backup("/data", bucket=args.bucket, password=args.password)
