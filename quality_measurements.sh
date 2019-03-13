#!/bin/bash

# Experemental: Automated build quality tests.

# Linter command
LINTER_COMMAND="pylint ytm_wd ytm_pageparser.py"
CODE_QUALITY_FILE="code_quality.csv"
DOCKER_SIZE_FILE="docker_image_size.csv"

echo "Current user: $USER"
# Linter results
CODE_Q=$($LINTER_COMMAND | grep -oP "(?<=Your code has been rated at).*?(?=/)")
echo "Code quality: $CODE_Q"
echo $CODE_Q >> $CODE_QUALITY_FILE

# Docker image size
IMG_SIZE=`docker image inspect owlsoul/ytmonitor --format='{{.Size}}'`
IMG_SIZE=$[$IMG_SIZE/1024/1024]
echo "Docker image size: $IMG_SIZE MB"
echo $IMG_SIZE >> $DOCKER_SIZE_FILE
