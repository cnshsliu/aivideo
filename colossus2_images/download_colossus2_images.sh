#!/bin/bash

# Download Colossus2 images using curl
# This script bypasses SSL/TLS handshake issues that occur with aria2c

# Create directory for images
mkdir -p colossus2_images

echo "Downloading Colossus2 images..."

# Download each image using curl
curl -O "https://pbs.twimg.com/media/G0_hSrTXgAA628V.jpg"
curl -O "https://pbs.twimg.com/media/Gw4Esy1WwAAoK6X.jpg"
curl -O "https://pbs.twimg.com/media/G1iFP9ZXIAA3ctY.jpg"
curl -O "https://pbs.twimg.com/media/G1h-MceXAAASJwh.jpg"
curl -O "https://pbs.twimg.com/media/Gwe5ghRbIAAbsPT.jpg"
curl -O "https://pbs.twimg.com/media/GwpXvohWMAAPTA9.jpg"
curl -O "https://pbs.twimg.com/media/GwpXvofWIAAnyst.jpg"
curl -O "https://pbs.twimg.com/media/GwpXvogW8AAcVVI.jpg"

# Rename files to descriptive names
mv G0_hSrTXgAA628V.jpg colossus2_images/Colossus2_Gigawatt_Aerial.jpg
mv Gw4Esy1WwAAoK6X.jpg colossus2_images/Colossus2_Glimpse_Supercomputer.jpg
mv G1iFP9ZXIAA3ctY.jpg colossus2_images/Colossus2_Interior_Tour.jpg
mv G1h-MceXAAASJwh.jpg colossus2_images/Colossus2_Doubled_Power.jpg
mv Gwe5ghRbIAAbsPT.jpg colossus2_images/Colossus2_Megapacks_Backup.jpg
mv GwpXvohWMAAPTA9.jpg colossus2_images/Colossus2_Memphis_Site.jpg
mv GwpXvofWIAAnyst.jpg colossus2_images/Colossus2_Chiller_Yard.jpg
mv GwpXvogW8AAcVVI.jpg colossus2_images/Colossus2_Construction.jpg

echo "Download complete! Images saved in colossus2_images/ directory"
echo ""
echo "Downloaded files:"
ls -la colossus2_images/