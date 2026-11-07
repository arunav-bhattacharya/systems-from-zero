#!/usr/bin/env bash
# A tiny certificate authority for lesson 10 of the networking track, made with openssl alone.
#
#   bash /labs/env/net/pki.sh /tmp/pki
#
# It writes, into the folder you name (default /tmp/pki):
#   root.pem, root.key         "Pay Test Root CA": signs itself, valid 10 years. Clients trust this one.
#   inter.pem, inter.key       "Pay Test Issuing CA 1": signed by the root, signs the two below.
#   api.pem, api.key           the server certificate for api.pay.test, signed by the intermediate, 45 days
#   api-chain.pem              api.pem followed by inter.pem: what a server should send
#   checkout.pem, checkout.key a client certificate for the checkout service (mTLS), 45 days
#   checkout-chain.pem         checkout.pem followed by inter.pem
# Every key is an ECDSA P-256 key in PKCS#8 PEM, which both openssl and the JDK read.
set -euo pipefail
dir=${1:-/tmp/pki}
mkdir -p "$dir"
cd "$dir"

key() { openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out "$1.key"; }

# 1. The root: a key pair, and a certificate that the root signs with its own key.
key root
openssl req -x509 -new -key root.key -subj "/O=Pay Test/CN=Pay Test Root CA" -days 3650 \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" -out root.pem

# 2. The intermediate: the root signs its public key. pathlen:0 means it may sign only end certificates.
key inter
openssl req -new -key inter.key -subj "/O=Pay Test/CN=Pay Test Issuing CA 1" -out inter.csr
printf 'basicConstraints=critical,CA:TRUE,pathlen:0\nkeyUsage=critical,keyCertSign,cRLSign\n' > inter.ext
openssl x509 -req -in inter.csr -CA root.pem -CAkey root.key -days 1825 -extfile inter.ext -out inter.pem 2>/dev/null

# 3. The server certificate. Clients check the name in subjectAltName, not the CN.
key api
openssl req -new -key api.key -subj "/CN=api.pay.test" -out api.csr
printf 'subjectAltName=DNS:api.pay.test\nextendedKeyUsage=serverAuth\nkeyUsage=critical,digitalSignature\nbasicConstraints=CA:FALSE\n' > api.ext
openssl x509 -req -in api.csr -CA inter.pem -CAkey inter.key -days 45 -extfile api.ext -out api.pem 2>/dev/null

# 4. A client certificate: the same kind of document, marked for client authentication.
key checkout
openssl req -new -key checkout.key -subj "/O=Pay Test/CN=checkout" -out checkout.csr
printf 'extendedKeyUsage=clientAuth\nkeyUsage=critical,digitalSignature\nbasicConstraints=CA:FALSE\n' > checkout.ext
openssl x509 -req -in checkout.csr -CA inter.pem -CAkey inter.key -days 45 -extfile checkout.ext -out checkout.pem 2>/dev/null

cat api.pem inter.pem > api-chain.pem
cat checkout.pem inter.pem > checkout-chain.pem
rm -f ./*.csr ./*.ext ./*.srl
ls "$dir"
