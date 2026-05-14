#!/bin/bash
docker build -t opentapwall:latest .
rm -rf opentapwall_data
mkdir -p opentapwall_data
docker run -d \
	--name opentapwall \
	-p 8000:8000 \
	-v $(pwd)/opentapwall_data:/data \
	opentapwall:latest
