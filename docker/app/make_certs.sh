#!/usr/bin/env bash
# Local CA + server certificate for the Maya HTTPS server. Runs inside the
# maya-app container; writes into certs/ (gitignored).
#   bash docker/app/make_certs.sh 192.168.1.23 [more IPs or hostnames]
# The CA is kept across runs so a phone that already trusts it keeps working
# when the laptop gets a new LAN IP; only the server cert is reissued.
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p certs
cd certs
printf '*\n' > .gitignore

if [ ! -f ca.key ]; then
  openssl req -x509 -newkey rsa:2048 -nodes -sha256 -days 3650 \
    -keyout ca.key -out ca.crt -subj "/CN=Maya Local CA" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign"
fi

san="DNS:localhost,IP:127.0.0.1"
for h in "$@"; do
  if [[ "$h" =~ ^[0-9.]+$ ]]; then san="$san,IP:$h"; else san="$san,DNS:$h"; fi
done

openssl req -newkey rsa:2048 -nodes -sha256 -keyout key.pem -out server.csr -subj "/CN=Maya"
# iOS rejects server certs valid for more than 825 days; 397 also satisfies Chrome.
cat > server.ext <<EOF
basicConstraints=CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=$san
EOF
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -days 397 -sha256 -extfile server.ext -out cert.pem
rm -f server.csr server.ext
echo "certs/cert.pem issued for: $san"
