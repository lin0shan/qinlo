import selfsigned from 'selfsigned';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const certDir = path.join(__dirname, 'certs');

if (!fs.existsSync(certDir)) {
  fs.mkdirSync(certDir, { recursive: true });
}

const attrs = [
  { name: 'commonName', value: 'dev.local' },
  { name: 'countryName', value: 'CN' },
  { name: 'organizationName', value: 'Dev' },
];

const opts = {
  days: 365,
  keySize: 2048,
  algorithm: 'sha256',
  extensions: [
    { name: 'basicConstraints', cA: false },
    { name: 'keyUsage', digitalSignature: true, keyEncipherment: true },
    { name: 'extKeyUsage', serverAuth: true },
    {
      name: 'subjectAltName',
      altNames: [
        { type: 2, value: 'localhost' },
        { type: 7, value: '127.0.0.1' },
        { type: 7, value: '192.168.0.104' },
      ],
    },
  ],
};

const generate = selfsigned.generate;
const pems = await generate(attrs, opts);

fs.writeFileSync(path.join(certDir, 'localhost-key.pem'), pems.private);
fs.writeFileSync(path.join(certDir, 'localhost.pem'), pems.cert);

console.log('证书已生成到 certs/ 目录');
console.log('SAN: localhost, 127.0.0.1, 192.168.0.104');
