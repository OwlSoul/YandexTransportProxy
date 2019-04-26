#!/bin/bash

# Execute tests (python pytest)

python3 -m pytest \
-v \
--color=no \
--junitxml test_results.xml \
--show-progress \
--show-capture=all
