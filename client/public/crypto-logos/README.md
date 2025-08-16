# Crypto Logos

This directory contains SVG logos for various cryptocurrencies used in the real-time price feed. The logos are sourced from the [cryptocurrency-icons](https://github.com/spothq/cryptocurrency-icons) library, which provides over 7,500 icons for almost 500 cryptocurrencies.

## Library Information

- **Source**: [cryptocurrency-icons](https://github.com/spothq/cryptocurrency-icons) by spothq
- **License**: CC0-1.0 (Public Domain)
- **Icons**: Over 7,500 icons for almost 500 cryptocurrencies
- **Styles**: Color, black, white, and icon variants
- **Sizes**: 32x32, 32x32@2x, and 128x128 PNG variants

## Available Logos

The following cryptocurrencies are currently supported in our application:

- `btc.svg` - Bitcoin (BTC)
- `eth.svg` - Ethereum (ETH)
- `xrp.svg` - Ripple (XRP)
- `bnb.svg` - Binance Coin (BNB)
- `ada.svg` - Cardano (ADA)
- `matic.svg` - Polygon (MATIC)
- `dot.svg` - Polkadot (DOT)
- `sol.svg` - Solana (SOL)
- `usdt.svg` - Tether (USDT)
- `usdc.svg` - USD Coin (USDC)
- `generic.svg` - Generic fallback logo for unknown cryptocurrencies

## Usage

The logos are automatically mapped in the `CryptoPriceCard` component using the `getCryptoLogo()` utility function from `@/lib/crypto-logos`.

### Adding New Logos

1. The cryptocurrency-icons library includes logos for almost 500 cryptocurrencies
2. To add a new cryptocurrency, simply update the mapping in `client/lib/crypto-logos.ts`
3. The logo file should already be available in this directory

### Fallback System

If a logo is not found or fails to load:
1. The system will try to load the generic logo from cryptocurrency-icons
2. If that fails, it will generate a colored circle with the first letter of the cryptocurrency symbol

## Logo Specifications

- **Format**: SVG (from cryptocurrency-icons library)
- **Style**: Color variants with brand-accurate colors
- **Quality**: Professional-grade icons used by major crypto platforms
- **Consistency**: All icons follow the same design principles

## Implementation Details

The crypto logos are implemented with:
- Professional icons from the cryptocurrency-icons library
- Automatic fallback to generated logos for unknown cryptocurrencies
- Error handling for failed image loads
- Consistent sizing and styling across all cards
- Support for both light and dark themes
- Brand-accurate colors for each cryptocurrency

## Credits

- **cryptocurrency-icons**: Created by spothq and contributors
- **License**: CC0-1.0 (Public Domain)
- **Website**: [cryptoicons.co](https://cryptoicons.co)
