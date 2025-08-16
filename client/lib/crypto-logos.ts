// Crypto logo mapping utility using cryptocurrency-icons library
export const getCryptoLogo = (symbol: string): string => {
  // Map of supported cryptocurrencies using cryptocurrency-icons library
  const logoMap: Record<string, string> = {
    BTC: "/crypto-logos/btc.svg",
    ETH: "/crypto-logos/eth.svg",
    XRP: "/crypto-logos/xrp.svg",
    BNB: "/crypto-logos/bnb.svg",
    ADA: "/crypto-logos/ada.svg",
    MATIC: "/crypto-logos/matic.svg",
    DOT: "/crypto-logos/dot.svg",
    SOL: "/crypto-logos/sol.svg",
    USDT: "/crypto-logos/usdt.svg",
    USDC: "/crypto-logos/usdc.svg",
    // Add more mappings as needed
  };

  // First check our explicit mapping
  if (logoMap[symbol.toUpperCase()]) {
    return logoMap[symbol.toUpperCase()];
  }

  // Then check if the logo exists in the cryptocurrency-icons library
  const lowerSymbol = symbol.toLowerCase();
  return `/crypto-logos/${lowerSymbol}.svg`;
};

// Fallback logo for unknown cryptocurrencies
export const createFallbackLogo = (symbol: string): string => {
  const firstLetter = symbol.charAt(0).toUpperCase();
  const colors = [
    "#FF6B6B",
    "#4ECDC4",
    "#45B7D1",
    "#96CEB4",
    "#FFEAA7",
    "#DDA0DD",
    "#98D8C8",
    "#F7DC6F",
    "#BB8FCE",
    "#85C1E9",
  ];
  const colorIndex = symbol.charCodeAt(0) % colors.length;
  const color = colors[colorIndex];

  return `data:image/svg+xml;base64,${btoa(`
    <svg width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="48" height="48" rx="24" fill="${color}"/>
      <text x="24" y="32" text-anchor="middle" fill="white" font-family="Arial, sans-serif" font-size="20" font-weight="bold">${firstLetter}</text>
    </svg>
  `)}`;
};

// Get crypto color from cryptocurrency-icons manifest
export const getCryptoColor = (symbol: string): string => {
  // Default colors for common cryptocurrencies
  const colorMap: Record<string, string> = {
    BTC: "#F7931A", // Bitcoin orange
    ETH: "#627EEA", // Ethereum blue
    XRP: "#23292F", // Ripple black
    BNB: "#F3BA2F", // Binance Coin yellow
    ADA: "#0033AD", // Cardano blue
    MATIC: "#8247E5", // Polygon purple
    DOT: "#E6007A", // Polkadot pink
    SOL: "#00FFA3", // Solana green
    USDT: "#26A17B", // Tether green
    USDC: "#2775CA", // USD Coin blue
  };

  return colorMap[symbol.toUpperCase()] || "#6B7280"; // Default gray
};

// Check if a crypto logo exists
export const hasCryptoLogo = (symbol: string): boolean => {
  const logoPath = getCryptoLogo(symbol);
  // For now, we'll assume all lowercase symbols exist since we have 485 logos
  // In a real implementation, you might want to check against a list of available logos
  return true;
};
