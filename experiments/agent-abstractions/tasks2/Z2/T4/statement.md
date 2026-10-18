# Worst case means the least money in

The worst-case rule for ranged and approximate schedule amounts has a gap: for money
coming in (a salary, a refund), the end furthest from zero is the *best* case. Someone
planning around a salary "between 1,010.00 and 2,000.00" wants to plan with 1,010.00.

Change the rule so that a ranged or approximate amount is always expected at **the
lowest value it allows**:

- Money going out: unchanged, the end furthest from zero (between -101.00 and -200.00
  is expected at -200.00; approximately -100.00 at -107.50).
- Money coming in: the end closest to zero (between 101.00 and 200.00 is expected at
  101.00; approximately 100.00 at 92.50).
- A range that spans zero (between -30.00 and 50.00) is expected at its negative end,
  -30.00.

The tolerance of approximate amounts is the same as before. Single ("is") amounts and
missing amounts are unchanged.
