#!/bin/bash

QUALITY=$(pylint --rcfile=pylint.rc transport_proxy.py yandex_transport_core/*.py | grep -oP '(?<=Your code has been rated at).*?(?=/)')

echo "Quality               : $QUALITY"
echo '"Code quality"' > code_quality.csv
echo $QUALITY >> code_quality.csv

SIZE_BYTES=$(docker image inspect owlsoul/ytproxy:dev --format='{{.Size}}')
SIZE_MB=$(( $SIZE_BYTES / 1024 / 1024))

echo "Docker image size (MB): $SIZE_MB"
echo '"Docker image size"' > docker_image_size.csv
echo $SIZE_MB >> docker_image_size.csv
