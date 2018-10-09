#!/bin/bash
set -euxo pipefail

if [[ $(python --version) == 'Python 3.6'* ]]; then
	black --check futaba
fi
