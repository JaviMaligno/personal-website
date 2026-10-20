# Revisión de las tareas 4556e9e244 y 81ea158cf6

Las dos tareas se pueden resolver con el enunciado tal como está y ninguna filtra la implementación de forma relevante. Solo propongo retoques menores.

TASK 4556e9e244
SOLVABLE: yes. El test oculto exige lo siguiente:
- `simplefin-batch-sync` con `setSyncingMode('offline')`.
- En la primera sincronización sin categoría salen 2 `newTransactions`, que son el saldo inicial más la transacción.
- En la segunda, con `category: 'provider-category'`:
  - 0 `newTransactions` y 0 `matchedTransactions`.
  - Exactamente 3 mensajes CRDT, todos del dataset `accounts`, con las columnas `balance_current`, `bank_sync_status` y `last_sync`.
  - Ningún mensaje del dataset `transactions`.
  - `category` igual a `null`.

Todo se deduce del enunciado:
- «only changes … current balance, sync status, last sync time» fija las tres columnas.
- «must not modify the stored transaction» implica `matchedTransactions` vacío, porque esa lista solo incluye transacciones que cambian.
- «category stays empty» implica `null`.

El número exacto de 3 mensajes depende del comportamiento que el repositorio ya tiene: uno por columna. Tampoco hace falta saber que la «sync history» es la tabla `messages_crdt`, porque cualquier corrección que descarte la categoría inválida produce el mismo efecto. No hay casos límite sin cubrir que se vayan a evaluar, como categorías con tombstone.

LEAK: no, salvo un detalle leve. La frase «When bank sync normalises the transactions returned by a provider» apunta hacia `normalizeBankSyncTransactions`, pero no nombra la función ni el fichero, ni dice cómo obtener los ids. Es aceptable.

FIX: ninguno. Opcionalmente se puede cambiar «When bank sync normalises the transactions returned by a provider, a provider category is kept only if…» por «When bank sync imports provider transactions, a provider category is kept only if…».

TASK 81ea158cf6
SOLVABLE: yes. Comprobé el ejemplo contra los tests:
- Mes actual 2024-02 y objetivo 2024-04: se promedian 2024-01, 2023-12 y 2023-11, lo que da 600.
- Con 100 más gastados en 2023-12, el resultado es -633,33, que se redondea a 633.
- El test «first activity month», que hace `setBudget` en 2023-12, da 600 igual. No distingue implementaciones, así que no exige nada adicional.

Los tests de template se pueden deducir del enunciado porque fija la firma y los argumentos exactos:
- Hacen mock de `./actions` con `getCategoryAverage` y comprueban `toHaveBeenCalledWith({ month: templateContext.month, maxMonths: numMonths, categoryId })`.
- El mes se pasa sin cambiar, tanto 2024-01 como 2024-03.
- El resultado se convierte en positivo: el mock devuelve -(200/3) y se espera 67, con el redondeo que ya existe.

Hay tres riesgos que el enunciado no hace explícitos:
1. **Mes actual.** Los tests fijan `global.currentMonth`. El agente tiene que usar `monthUtils.currentMonth()` y no `new Date()`. Es la convención del repositorio, pero el enunciado no la menciona.
2. **Imports en el contexto de templates.** El mock de `./actions` sustituye el módulo entero y solo expone `getCategoryAverage`, `getSheetValue`, `getSheetBoolean` e `isTrackingBudget`. Si `category-template-context.ts` importa cualquier otro helper nuevo desde `./actions`, ese helper llega como `undefined`. Además, `getCategoryAverage` tiene que importarse directamente desde `./actions` y no a través de un re-export.
3. **Valores positivos.** «turn it into a positive amount» no dice si se niega el valor o se toma el valor absoluto. No afecta a los tests porque todos los mocks devuelven negativos.

LEAK: no, salvo detalles leves. La firma completa de `getCategoryAverage` y la obligación de que el template la llame con `month` sin cambiar son necesarias, porque los tests las verifican con `toHaveBeenCalledWith`. Hay dos frases que se acercan a la implementación, pero ambas sirven para definir el comportamiento:
- «the same per-month "spent" value the budget sheet already exposes» insinúa la celda `sum-amount-<id>`, pero es necesaria para definir qué significa «spent».
- La definición de «first activity month» («has a budgeted amount recorded, or has a (non-deleted) transaction in an on-budget account») describe la consulta SQL.

El cambio de texto en la UI no se evalúa con tests unitarios; solo afecta a los e2e y a las capturas visuales.

FIX: dos ediciones mínimas.
- Añadir en el punto 1: «"current month" is the app's notion of the current month (the one tests can override), not the system clock».
- Añadir en el punto 6: «the template module must import `getCategoryAverage` directly from the budget actions module and must not depend on any other new export from it».
