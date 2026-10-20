# Posting a scheduled transaction early and then redating it makes the schedule come due again

When I pay a bill ahead of its due date, I use "Post transaction" on the upcoming
schedule occurrence and then change the posted transaction's date to the day I
actually paid (today, or a few days before the due date). As soon as I move the
date earlier, the schedule behaves as if that occurrence had never been paid: it
shows up again as upcoming/due, and for a schedule that posts its transactions
automatically, a second transaction for the same occurrence is created when the
due date arrives. I end up with two transactions for one bill and have to delete
or zero one of them by hand.

Steps to reproduce (schedule set to "automatically add transaction"):

1. Create a monthly schedule whose next occurrence is a few days in the future.
2. Post that upcoming occurrence early.
3. Change the date of the posted transaction to an earlier date (today, or any
   day before the occurrence's due date).
4. When the due date arrives, the schedule posts the same occurrence again.

## Required behaviour

- A transaction that is linked to a schedule and was posted for an occurrence
  keeps counting as the payment of that occurrence after its date is moved
  earlier than the occurrence's due date. In particular this holds for the
  schedule's first occurrence, which has no earlier occurrence before it.
- The schedule therefore does not come due again for that occurrence, and a
  schedule that posts transactions automatically does not post a second
  transaction for it, neither on the due date nor afterwards.
- Once that occurrence is settled the schedule moves on to its following
  occurrence as usual (for a monthly schedule due on the 5th, the next date
  becomes the 5th of the next month), and that following occurrence is still
  posted normally when it comes due.
- A transaction that paid a *previous* occurrence must not be mistaken for the
  payment of the next one: if last month's occurrence was paid on its own date,
  this month's occurrence is still due and is still posted automatically.
