FROM python:3.8

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir pyzipper boto3

RUN mkdir /data
WORKDIR /usr/src/ecb
COPY ecb.py ./

ENTRYPOINT ["python", "ecb.py"]

