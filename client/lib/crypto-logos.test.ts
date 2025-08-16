import {
  getCryptoLogo,
  createFallbackLogo,
  getCryptoColor,
} from "./crypto-logos";

// Simple test to verify crypto logo mapping
export function testCryptoLogos() {
  const testCases = [
    { symbol: "BTC", expected: "/crypto-logos/btc.svg" },
    { symbol: "ETH", expected: "/crypto-logos/eth.svg" },
    { symbol: "XRP", expected: "/crypto-logos/xrp.svg" },
    { symbol: "BNB", expected: "/crypto-logos/bnb.svg" },
    { symbol: "ADA", expected: "/crypto-logos/ada.svg" },
    { symbol: "MATIC", expected: "/crypto-logos/matic.svg" },
    { symbol: "DOT", expected: "/crypto-logos/dot.svg" },
    { symbol: "SOL", expected: "/crypto-logos/sol.svg" },
    { symbol: "USDT", expected: "/crypto-logos/usdt.svg" },
    { symbol: "USDC", expected: "/crypto-logos/usdc.svg" },
    { symbol: "UNKNOWN", expected: "/crypto-logos/generic.svg" },
  ];

  console.log("Testing crypto logo mapping:");
  testCases.forEach(({ symbol, expected }) => {
    const result = getCryptoLogo(symbol);
    const status = result === expected ? "✅" : "❌";
    console.log(`${status} ${symbol}: ${result}`);
  });

  console.log("\nTesting crypto color mapping:");
  const colorTestCases = [
    { symbol: "BTC", expected: "#F7931A" },
    { symbol: "ETH", expected: "#627EEA" },
    { symbol: "XRP", expected: "#23292F" },
    { symbol: "BNB", expected: "#F3BA2F" },
    { symbol: "ADA", expected: "#0033AD" },
    { symbol: "MATIC", expected: "#8247E5" },
    { symbol: "DOT", expected: "#E6007A" },
    { symbol: "SOL", expected: "#00FFA3" },
    { symbol: "USDT", expected: "#26A17B" },
    { symbol: "USDC", expected: "#2775CA" },
  ];

  colorTestCases.forEach(({ symbol, expected }) => {
    const result = getCryptoColor(symbol);
    const status = result === expected ? "✅" : "❌";
    console.log(`${status} ${symbol}: ${result}`);
  });

  console.log("\nTesting fallback logo generation:");
  const fallbackTest = createFallbackLogo("TEST");
  console.log(
    "Fallback logo generated:",
    fallbackTest.substring(0, 50) + "..."
  );
}

// Run test if this file is executed directly
if (typeof window !== "undefined") {
  testCryptoLogos();
}
