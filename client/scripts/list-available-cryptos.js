#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

// Read the cryptocurrency-icons manifest
const manifestPath = path.join(__dirname, '../node_modules/cryptocurrency-icons/manifest.json');
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));

// Get all available crypto symbols
const symbols = manifest.map(crypto => crypto.symbol).sort();

console.log('Available cryptocurrencies from cryptocurrency-icons library:');
console.log('===========================================================');
console.log(`Total: ${symbols.length} cryptocurrencies\n`);

// Show first 50 as examples
console.log('Examples:');
symbols.slice(0, 50).forEach((symbol, index) => {
  process.stdout.write(`${symbol.padEnd(8)} `);
  if ((index + 1) % 10 === 0) {
    console.log();
  }
});

if (symbols.length > 50) {
  console.log(`\n... and ${symbols.length - 50} more`);
}

console.log('\nTo add a new cryptocurrency to your app:');
console.log('1. The logo file is already available in /public/crypto-logos/');
console.log('2. Update the mapping in client/lib/crypto-logos.ts');
console.log('3. The logo will be automatically used');
