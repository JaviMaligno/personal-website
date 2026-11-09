is_staff(email: str) -> bool
is_closed(account: dict) -> bool
due_date(account: dict) -> date
classify(account: dict, today: date) -> dict | None      # internal candidate: account_id, action, due (date), closed flag
apply_cap(candidates: list[dict], cap: int = DELETE_CAP) -> tuple[list[dict], list[dict]]   # (kept, dropped)
build_action(candidate: dict) -> dict                    # final output: account_id, action, due (ISO str), approved_by
plan_purge(accounts: list[dict], today: date) -> list[dict]