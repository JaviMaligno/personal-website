# Partial category updates through the API fail unless the name is included

Updating a category through the API with only some of its fields is supposed to
work: `api/category-update` takes an `id` and a partial `fields` object. In
practice, any update that leaves out `name` is rejected with a
`TypeError: Cannot read properties of undefined (reading 'trim')`. For example,
moving a category to another group:

```js
// api/category-update
{ id: categoryId, fields: { group_id: otherGroupId } }
// -> TypeError: Cannot read properties of undefined (reading 'trim')
```

The same happens for an update that only changes `hidden`, or any other single
field. Including the current name alongside the real change works around it.

Category groups have the same problem: `api/category-group-update` with only
`{ hidden: true }` fails with
`TypeError: Cannot read properties of undefined (reading 'toUpperCase')`.

## Expected behaviour

- A partial update of a category or of a category group succeeds whether or not
  `name` is included.
- Only the fields that were passed change. Everything else stored for the
  category or group keeps its value: the name, the group it belongs to, whether
  it is an income category/group, whether it is hidden, and any other stored
  settings the request does not mention. The changes recorded for sync for that
  update cover only the fields that were passed, so an update made on one device
  never re-writes fields that another device may have changed.
- When a name is passed, the existing behaviour stays: a category's new name is
  trimmed of surrounding whitespace, and renaming a category group to a name
  another group already has (case-insensitively) is still rejected.
