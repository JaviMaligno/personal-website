# Budget averages should only use complete months

The budget offers "set to N-month average" actions (for one category, and a bulk
3-month average for all categories) and an `average` budget template
(`#template average {number} months`). All of them currently average the spending
of the N months immediately before the target month, whatever those months are. That
gives misleading numbers in two situations:

- **Incomplete months.** When budgeting the current month or a future month, the
  months just before it include the current month (still in progress) or months that
  have not happened yet, whose spending is partial or zero.
- **Months before the category existed.** A category created recently gets averaged
  over months in which it had no activity at all, which drags the average down.

## Required behaviour

Introduce one shared way of computing a category's average spending and use it for
all three features.

1. **Which months count.** Start from the month before the target month. If that
   month is the current month or later, start instead from the month before the
   current month (the last complete month). Walk backwards from there, taking at most
   N months. Stop early (take fewer months) once you reach a month earlier than the
   category's *first activity month*. "Current month" is the application's own
   notion of the current month (the shared month utilities), not the system clock.
2. **First activity month** of a category = the earliest month, not later than the
   starting month from step 1, in which the category either has a budgeted amount
   recorded, or has a (non-deleted) transaction in an on-budget account. If the
   category has no activity at all, there is no lower bound.
3. **The average** is the sum of the category's spent amount (negative for spending)
   over the selected months, divided by the number of selected months, rounded to an
   integer.
   If no month is selected the average is 0.
4. Expose this as an exported async function of the server-side budget actions
   module (the module that already exports `setNMonthAvg` and `set3MonthAvg`):

   ```ts
   getCategoryAverage({ month, maxMonths, categoryId }: {
     month: string;      // target month, 'YYYY-MM'
     maxMonths: number;  // N
     categoryId: string;
   }): Promise<number>   // signed, rounded average as described above
   ```

5. **Set N-month average** for one category and the **bulk 3-month average** must use
   it (with `maxMonths` = N, respectively 3) and keep their current sign handling: for
   an expense category the budgeted amount is the negated average; income categories
   are handled as they are today.
6. **The `average` template** must obtain its average by calling
   `getCategoryAverage` with the template's own month (unchanged, the skipping of
   incomplete months is the helper's job), the template's number of months and the
   category id, and budget its absolute value (a negative average is negated, a
   positive one is used as is); the existing percentage / fixed adjustments and
   rounding then apply as before. The template code imports
   `getCategoryAverage` directly from that budget actions module and needs no other
   new export from it.

### Example

Current month 2024-02; a category spent 300 in 2023-11, 600 in 2023-12, 900 in
2024-01, 3000 in 2024-02 and 1200 in 2024-03. Setting the 3-month average for 2024-04
uses 2024-01, 2023-12 and 2023-11 (2024-03 and 2024-02 are not complete), so the
budget becomes 600. With an extra 100 spent in 2023-12 it becomes 633.

The read-only description of an average automation in the UI should say it uses the
last N *complete* months.
