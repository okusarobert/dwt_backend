/**
 * Currency formatting utilities for proper UGX and other currency display
 */

export interface CurrencyFormatterOptions {
  minimumFractionDigits?: number;
  maximumFractionDigits?: number;
  notation?: 'standard' | 'compact' | 'scientific' | 'engineering';
  compactDisplay?: 'short' | 'long';
}

export class CurrencyFormatter {
  private static formatters: Map<string, Intl.NumberFormat> = new Map();

  private static getFormatter(
    currency: string, 
    locale: string = 'en-UG',
    options: CurrencyFormatterOptions = {}
  ): Intl.NumberFormat {
    const key = `${currency}_${locale}_${JSON.stringify(options)}`;
    
    if (!this.formatters.has(key)) {
      const formatter = new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: options.minimumFractionDigits ?? (currency === 'UGX' ? 0 : 2),
        maximumFractionDigits: options.maximumFractionDigits ?? (currency === 'UGX' ? 0 : 2),
        notation: options.notation,
        compactDisplay: options.compactDisplay,
      });
      this.formatters.set(key, formatter);
    }
    
    return this.formatters.get(key)!;
  }

  /**
   * Format amount as UGX currency
   */
  static formatUGX(amount: number, options: CurrencyFormatterOptions = {}): string {
    try {
      const formatter = this.getFormatter('UGX', 'en-UG', options);
      return formatter.format(amount);
    } catch (error) {
      // Fallback formatting if UGX is not supported
      const formatted = new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
        notation: options.notation,
        compactDisplay: options.compactDisplay,
      }).format(amount);
      return `UGX ${formatted}`;
    }
  }

  /**
   * Format amount as USD currency
   */
  static formatUSD(amount: number, options: CurrencyFormatterOptions = {}): string {
    const formatter = this.getFormatter('USD', 'en-US', options);
    return formatter.format(amount);
  }

  /**
   * Format amount with generic currency
   */
  static formatCurrency(
    amount: number, 
    currency: string, 
    locale?: string,
    options: CurrencyFormatterOptions = {}
  ): string {
    try {
      const formatter = this.getFormatter(currency, locale, options);
      return formatter.format(amount);
    } catch (error) {
      // Fallback to basic formatting
      const formatted = new Intl.NumberFormat(locale || 'en-US', {
        minimumFractionDigits: options.minimumFractionDigits ?? 2,
        maximumFractionDigits: options.maximumFractionDigits ?? 2,
        notation: options.notation,
        compactDisplay: options.compactDisplay,
      }).format(amount);
      return `${currency} ${formatted}`;
    }
  }

  /**
   * Format amount as compact currency (e.g., UGX 1.2K, UGX 1.5M)
   */
  static formatCompact(amount: number, currency: string = 'UGX'): string {
    const options: CurrencyFormatterOptions = {
      notation: 'compact',
      compactDisplay: 'short',
      maximumFractionDigits: 1
    };

    if (currency === 'UGX') {
      return this.formatUGX(amount, options);
    } else if (currency === 'USD') {
      return this.formatUSD(amount, options);
    } else {
      return this.formatCurrency(amount, currency, undefined, options);
    }
  }

  /**
   * Format percentage with proper locale
   */
  static formatPercentage(value: number, decimals: number = 2): string {
    return new Intl.NumberFormat('en-US', {
      style: 'percent',
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value / 100);
  }

  /**
   * Format number without currency symbol
   */
  static formatNumber(amount: number, decimals: number = 2): string {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(amount);
  }

  /**
   * Parse currency string back to number
   */
  static parseCurrency(currencyString: string): number {
    // Remove currency symbols and spaces, then parse
    const cleaned = currencyString.replace(/[^\d.-]/g, '');
    return parseFloat(cleaned) || 0;
  }

  /**
   * Get currency symbol for a given currency code
   */
  static getCurrencySymbol(currency: string): string {
    try {
      const formatter = new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      });
      
      // Format a small number and extract just the symbol
      const formatted = formatter.format(0);
      return formatted.replace(/[\d\s]/g, '');
    } catch (error) {
      return currency;
    }
  }
}

// Convenience functions for common use cases
export const formatUGX = (amount: number, options?: CurrencyFormatterOptions) => 
  CurrencyFormatter.formatUGX(amount, options);

export const formatUSD = (amount: number, options?: CurrencyFormatterOptions) => 
  CurrencyFormatter.formatUSD(amount, options);

export const formatCompact = (amount: number, currency?: string) => 
  CurrencyFormatter.formatCompact(amount, currency);

export const formatPercentage = (value: number, decimals?: number) => 
  CurrencyFormatter.formatPercentage(value, decimals);

export const formatNumber = (amount: number, decimals?: number) => 
  CurrencyFormatter.formatNumber(amount, decimals);

/**
 * Format crypto amounts with appropriate decimal places
 */
export const formatCryptoAmount = (amount: number, symbol: string): string => {
  let decimals = 2;
  
  // Set appropriate decimal places for different cryptos
  switch (symbol.toUpperCase()) {
    case 'ETH':
    case 'BTC':
      decimals = 6;
      break;
    case 'USDT':
    case 'USDC':
      decimals = 2;
      break;
    case 'TRX':
      decimals = 2;
      break;
    case 'BNB':
    case 'SOL':
      decimals = 4;
      break;
    default:
      decimals = 6; // Default to 6 for crypto amounts
  }
  
  return CurrencyFormatter.formatNumber(amount, decimals);
};
