#!/bin/bash

python3 -m pytest \
-v \
--color=no \
--junitxml test_results.xml \
--show-progress \
--show-capture=all
