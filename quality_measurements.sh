#!/bin/bash

# Experemental: Automated build quality tests.

# Linter command
LINTER_COMMAND="pylint ytm_wd ytm_pageparser.py"

# Linter results
CODE_Q=$($LINTER_COMMAND | grep -oP "(?<=Your code has been rated at).*?(?=/)")
echo "Code quality: $CODE_Q"
echo $CODE_Q > code_quality.csv
