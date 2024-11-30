FROM minio/minio:latest

COPY config/minio.json /etc/minio/config.json

EXPOSE 9000 9001

ENTRYPOINT ["minio"]