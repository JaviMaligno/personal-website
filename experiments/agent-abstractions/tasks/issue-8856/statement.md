# A category can be left without a group, and then it disappears

A category that has no group becomes unreachable: it no longer shows up when categories are listed (neither in the flat list nor under any group), so it cannot be found again to fix it, and its name stays taken.

Today this can happen through an ordinary category update. Creating a category already insists on a group, but updating one does not: an update through the API (`api/category-update`) that sets `group_id` to an empty string goes through and leaves the category with no group, and setting `group_id` to `null` is silently accepted as well. The app's own `category-update` handler (the one the UI uses, which receives the whole category with its `group`) has the same gap.

Please make category updates refuse to leave a category without a group:

- An update that sets the group to `null` or to an empty string, whether through `api/category-update` (`group_id`) or through the `category-update` handler (`group`), must be rejected with an error, just as creating a category without a group is.
- A rejected update must change nothing: the category keeps its original group, is still listed (in the flat list and under its group) and remains fully manageable afterwards (it can still be renamed, and deleted).
- Updates that do not mention the group at all (for example only renaming or hiding a category) must keep working and keep the category in its current group.
- Moving a category to another existing group through an update must keep working.
