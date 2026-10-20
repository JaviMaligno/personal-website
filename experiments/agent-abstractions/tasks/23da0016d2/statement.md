# Currency-precision-aware amount helpers

Amounts are stored as integers in minor units, and the shared amount utilities
always assume two decimal places. The currency list already records how many
decimal places each currency uses (e.g. 0 for JPY, KRW and IRR, 2 for USD, EUR and
GBP; the first entry is "None", with code `''` and 2 decimal places): every entry
of the exported `currencies` list has a numeric, non-negative `decimalPlaces`
field, and that must stay so. But nothing exposes it to the amount helpers. Add
helpers that take a currency code into account.

## Required behaviour

1. **Decimal places of a currency.** The shared currencies module (the one that
   exports the `currencies` list and `getCurrency`) exports
   `getDecimalPlaces(currencyCode: string): number`, returning the currency's
   number of decimal places: 0 for JPY, KRW and IRR, 2 for USD, EUR and GBP, 2 for
   `''` (None), and 2 for an unknown code such as `XYZ`.

2. **Formatting with a currency.** The shared utility
   `integerToCurrencyWithDecimal(integerAmount)` gains an optional second argument,
   a currency code. When it is given, the integer is formatted with that currency's
   number of decimal places, using the current number format (separators) otherwise
   unchanged. With the `comma-dot` format: `(1234, '')` → `'12.34'`,
   `(1234, 'USD')` → `'12.34'`, `(1234, 'JPY')` → `'1,234'`,
   `(1234, 'IRR')` → `'1,234'`, `(1234, 'XYZ')` → `'12.34'`. Without the argument
   the behaviour is exactly as today (`1234` → `'12.34'`, `1200` → `'12.00'`).

3. **Encoding with a currency.** The same shared utility module exports
   `amountToCurrencyInteger(amount: number, code: string): number`, converting a
   decimal amount to the stored integer using the currency's decimal places:
   `(12.34, 'USD')` → `1234`, `(12.34, '')` → `1234`, `(1234, 'JPY')` → `1234`,
   `(1234, 'IRR')` → `1234`. Encoding then formatting with the same currency
   round-trips the amount.

Existing helpers and their callers are otherwise unchanged.
