#!/bin/bash

python3 -m pytest --junitxml test_results.xml --show-progress --show-capture=all
