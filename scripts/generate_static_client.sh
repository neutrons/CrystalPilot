#!/bin/bash

python -m trame.tools.www --client-type vue3 --output /app/www-content
mkdir -p /app/www-content/assets/js

# Get the static JS from nova-trame and add it to our client build
export NOVA_TRAME_LOCATION="$(pixi run python -c 'import os; import nova.trame; print(os.path.dirname(nova.trame.__file__))')"
cp $NOVA_TRAME_LOCATION/view/theme/assets/js/*.js /app/www-content/assets/js/
