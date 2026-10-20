# Expected amount in the API's schedule list

Scripts that read schedules through the API get each schedule's amount exactly as it
was entered (a number, or a `{ num1, num2 }` range) plus its operator. To know what a
schedule will actually post they have to re-implement Actual's rules themselves, and
they keep getting it wrong.

Add a field `expectedAmount` to each schedule returned by the API's schedule list: the
single amount Actual expects that schedule to post, in the same integer units as
`amount`. A ranged amount gives the end of the range furthest from zero (between
-101.00 and -200.00 gives -200.00), a single amount gives itself, and a schedule
without an amount gives 0.

The existing fields of the schedule list stay as they are.
