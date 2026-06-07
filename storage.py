"""
storage.py — bucket-agnostic storage layer.

Local   : a folder on disk (for testing, or a Drive/Dropbox-synced folder).
S3      : any S3-compatible bucket — AWS S3, Cloudflare R2, Supabase Storage,
          DigitalOcean Spaces, MinIO. Just point the endpoint/keys at yours.

Credentials are read from environment variables — never hard-coded here.
"""
import os, io, json

class Storage:
    def list_keys(self, prefix): raise NotImplementedError
    def read_bytes(self, key): raise NotImplementedError
    def read_text(self, key, default=None): raise NotImplementedError
    def write_text(self, key, text): raise NotImplementedError

class LocalStorage(Storage):
    def __init__(self, base_dir):
        self.base = os.path.abspath(base_dir); os.makedirs(self.base, exist_ok=True)
    def _p(self, key): return os.path.join(self.base, key)
    def list_keys(self, prefix=""):
        root = self._p(prefix); out = []
        if os.path.isdir(root):
            for dp, _, fns in os.walk(root):
                for fn in fns:
                    full = os.path.join(dp, fn)
                    out.append(os.path.relpath(full, self.base))
        return sorted(out)
    def read_bytes(self, key):
        with open(self._p(key), "rb") as f: return f.read()
    def read_text(self, key, default=None):
        try:
            with open(self._p(key), "r", encoding="utf-8") as f: return f.read()
        except FileNotFoundError: return default
    def write_text(self, key, text):
        p = self._p(key); os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f: f.write(text)

class S3Storage(Storage):
    def __init__(self, bucket, prefix="", endpoint_url=None, region=None):
        import boto3  # lazy import so LocalStorage works without boto3 installed
        self.bucket = bucket; self.prefix = prefix.rstrip("/")
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url or os.getenv("S3_ENDPOINT") or os.getenv("R2_ENDPOINT") or None,
            region_name=region or os.getenv("S3_REGION") or "auto",
            aws_access_key_id=os.getenv("S3_ACCESS_KEY") or os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("S3_SECRET_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY") or os.getenv("R2_SECRET_ACCESS_KEY"),
        )
    def _full(self, key): return f"{self.prefix}/{key}" if self.prefix else key
    def list_keys(self, prefix=""):
        full = self._full(prefix); keys = []
        tok = None
        while True:
            kw = dict(Bucket=self.bucket, Prefix=full)
            if tok: kw["ContinuationToken"] = tok
            r = self.s3.list_objects_v2(**kw)
            for o in r.get("Contents", []):
                k = o["Key"]
                if self.prefix and k.startswith(self.prefix + "/"): k = k[len(self.prefix) + 1:]
                keys.append(k)
            if r.get("IsTruncated"): tok = r.get("NextContinuationToken")
            else: break
        return sorted(keys)
    def read_bytes(self, key):
        return self.s3.get_object(Bucket=self.bucket, Key=self._full(key))["Body"].read()
    def read_text(self, key, default=None):
        try: return self.read_bytes(key).decode("utf-8")
        except Exception: return default
    def write_text(self, key, text):
        self.s3.put_object(Bucket=self.bucket, Key=self._full(key),
                           Body=text.encode("utf-8"), ContentType="application/json")

def make_storage():
    has_remote = os.getenv("S3_ENDPOINT") or os.getenv("R2_ENDPOINT") or os.getenv("S3_BUCKET") or os.getenv("R2_BUCKET")
    kind = (os.getenv("STORAGE") or ("s3" if has_remote else "local")).lower()
    if kind == "s3":
        bucket = os.getenv("S3_BUCKET") or os.environ["R2_BUCKET"]
        return S3Storage(bucket=bucket, prefix=os.getenv("S3_PREFIX", "quotes"))
    return LocalStorage(os.getenv("LOCAL_DIR", "./bucket"))
