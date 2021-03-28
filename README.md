# ECB (Encrypted Cloud Backups)


### Installation
Use [docker](https://docs.docker.com/get-docker/)


### Example Usage

In this example, I'm backing up all of my documents by doing a volume mount into `/data`.

In order to authenticate with AWS, I am also adding my credentials.

Every folder will be uploaded as a password protected zip file. This example password is `supersecret`.

Don't forget to create an AWS bucket first.

```
$ docker run --rm -it -v /home/m/Documents:/data -v /home/m/.aws:/root/.aws binarymason/ecb example-bucket supersecret
=> backing up: data
+  /data/recursive/example      -> example-bucket/data/recursive/example/a5a202c9effae87e5075af01c7358bb9.zip
+  /data/prescreen              -> example-bucket/data/prescreen/1b320fb23b18039ea8922ebfad304bd3.zip
+  /data                        -> example-bucket/data/b2d8f717f0377cec0e15e99bfbb12363.zip
```

### Notes

If a folder is already backed up and has not changed, this tool is smart enough to not do anything.  Feel free to have this run in an automated way on a regular basis.


### Decrypting Files

The easiest tool to use to decrypt password protected zip files is 7zip.
