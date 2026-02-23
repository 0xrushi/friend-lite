#!/bin/bash
set -e

# Generate self-signed SSL certificate for Chronicle services
# Outputs server.crt and server.key in the current directory
# Supports localhost, IP addresses, and domain names

SERVER_ADDRESS="$1"

if [ -z "$SERVER_ADDRESS" ]; then
    echo "Usage: $0 <ip-or-domain>"
    echo "Example: $0 100.83.66.30"
    echo "Example: $0 myserver.tailxxxxx.ts.net"
    exit 1
fi

# Detect if it's an IP address or domain name
if echo "$SERVER_ADDRESS" | grep -E '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$' > /dev/null; then
    IS_IP=true
    echo "Generating SSL certificate for localhost and IP: $SERVER_ADDRESS"
else
    IS_IP=false
    echo "Generating SSL certificate for localhost and domain: $SERVER_ADDRESS"
fi

# Create certificate configuration with Subject Alternative Names
cat > server.conf << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = CA
L = SF
O = Dev
CN = localhost

[v3_req]
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = *.localhost
IP.1 = 127.0.0.1
EOF

# Add custom address as either IP or DNS
if [ "$IS_IP" = true ]; then
    echo "IP.2 = $SERVER_ADDRESS" >> server.conf
else
    echo "DNS.3 = $SERVER_ADDRESS" >> server.conf
fi

# Generate private key
openssl genrsa -out server.key 2048

# Generate certificate signing request
openssl req -new -key server.key -out server.csr -config server.conf

# Generate self-signed certificate
openssl x509 -req -in server.csr -signkey server.key -out server.crt -days 365 -extensions v3_req -extfile server.conf

# Clean up
rm server.csr server.conf

# Set appropriate permissions
chmod 600 server.key
chmod 644 server.crt

echo "SSL certificate generated successfully"
echo "   - Certificate: server.crt"
echo "   - Private key: server.key"
echo "   - Valid for: localhost, *.localhost, 127.0.0.1, $SERVER_ADDRESS"
