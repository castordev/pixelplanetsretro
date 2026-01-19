#!/usr/bin/env bash
set -o errexit

# Ensure Skyfield ephemeris file is available in the deployment bundle.
# de421.bsp is ~16–20MB and can be too large for some git workflows; download at build time.
if [ ! -f "de421.bsp" ]; then
	echo "Downloading de421.bsp (Skyfield ephemeris)..."
	curl -L -o de421.bsp "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de421.bsp"
fi

python manage.py collectstatic --noinput
