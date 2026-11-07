#!/usr/bin/env bash
# How the certificates in this folder were made (OpenSSL 3.4 or newer, for -not_before and -not_after).
# The dates are fixed so the tests never expire: ChainCheckTest sets its clock to 2026-11-10.
# Run it in this folder to make a fresh set; the tests only need the .pem files.
set -euo pipefail
O=${OPENSSL:-openssl}
key() { $O genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out "$1.key"; }
ext() { printf '%b' "$1" > ext.tmp; }
sign() { # sign <name> <subject> <issuer> <not_before> <not_after> <extensions>
    $O req -new -key "$1.key" -subj "$2" -out "$1.csr"
    ext "$6"
    $O x509 -req -in "$1.csr" -CA "$3.pem" -CAkey "$3.key" -not_before "$4" -not_after "$5" -extfile ext.tmp -out "$1.pem"
}
CA='basicConstraints=critical,CA:TRUE\nkeyUsage=critical,keyCertSign,cRLSign\n'
LEAF='keyUsage=critical,digitalSignature\nbasicConstraints=CA:FALSE\nextendedKeyUsage=serverAuth\n'

key root
$O req -x509 -new -key root.key -subj "/O=Pay Test/CN=Pay Test Root CA" -not_before 20260101000000Z -not_after 20360101000000Z \
    -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign" -out root.pem
key inter
sign inter "/O=Pay Test/CN=Pay Test Issuing CA 1" root 20260101000000Z 20310101000000Z "${CA}"
key api
sign api "/CN=api.pay.test" inter 20261107000000Z 20261222000000Z "${LEAF}subjectAltName=DNS:api.pay.test\n"
key api-expired
sign api-expired "/CN=api.pay.test" inter 20260801000000Z 20260915000000Z "${LEAF}subjectAltName=DNS:api.pay.test\n"
key ledger
sign ledger "/CN=ledger.pay.test" inter 20261107000000Z 20261222000000Z "${LEAF}subjectAltName=DNS:ledger.pay.test\n"
key wildcard
sign wildcard "/CN=*.pay.test" inter 20261107000000Z 20261222000000Z "${LEAF}subjectAltName=DNS:*.pay.test,DNS:pay.test\n"
# an impostor: a CA that copies the intermediate's name but has its own key
key fake-inter
$O req -x509 -new -key fake-inter.key -subj "/O=Pay Test/CN=Pay Test Issuing CA 1" -not_before 20260101000000Z -not_after 20310101000000Z \
    -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign" -out fake-inter.pem
key forged
sign forged "/CN=api.pay.test" fake-inter 20261107000000Z 20261222000000Z "${LEAF}subjectAltName=DNS:api.pay.test\n"
# a leaf that signs another certificate, as if it were a CA
key admin
sign admin "/CN=admin.pay.test" api 20261107000000Z 20261222000000Z "${LEAF}subjectAltName=DNS:admin.pay.test\n"
# someone else's root, which the tests do not trust
key other-root
$O req -x509 -new -key other-root.key -subj "/O=Issuer Example/CN=Issuer Example Root CA" -not_before 20260101000000Z -not_after 20360101000000Z \
    -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign" -out other-root.pem
key other
sign other "/CN=api.pay.test" other-root 20261107000000Z 20261222000000Z "${LEAF}subjectAltName=DNS:api.pay.test\n"
rm -f ./*.key ./*.csr ./*.srl ext.tmp
