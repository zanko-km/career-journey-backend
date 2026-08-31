# Authorization Model

## How roles work

Every authenticated user is **always** granted the base `EMPLOYEE` role,
regardless of what's in the `employee_role` table (see
`app/core/current_user.py`). Additional roles (`MANAGER`, `HRBP`,
`HR_MANAGER`) are looked up from `employee_role` and appended on top. This
means:

- A user can hold multiple roles simultaneously (e.g. a MANAGER is always
  also an EMPLOYEE for their own self-service actions).
- Every endpoint restricted to `EMPLOYEE` is implicitly available to
  everyone, including MANAGER/HRBP/HR_MANAGER acting on their own record.
- `HR_MANAGER` is treated as a strict superset of `HRBP` everywhere in this
  codebase — every endpoint that lists `HRBP` in its allowed roles also
  lists `HR_MANAGER`, and every `HRBP`-scoped visibility check
  (`require_employee_scope`, `require_team_scope`) passes `HR_MANAGER`
  through unconditionally, with no team-assignment restriction.

## Two layers of access control

Most endpoints combine two checks:

1. **Role check** (`require_roles(...)`) — is the caller's role allowed to
   call this endpoint at all?
2. **Scope check** (`require_employee_scope(...)` /
   `require_team_scope(...)`) — is the caller allowed to act on *this
   specific* employee/team? E.g. a MANAGER passes the role check for
   `POST /employees/{id}/competencies`, but the scope check then confirms
   they're actually that employee's manager (walking the management
   hierarchy) before allowing the write.

Both layers matter — a role appearing in "allowed roles" below does not by
itself mean unrestricted access; check the scope note for each capability.

---

## EMPLOYEE

Every authenticated user has these, for their own record only.

| Capability | Endpoint |
|---|---|
| Change own password | `POST /auth/change-password` |
| View own upcoming meetings/onboarding actions | `GET /employees/{id}/onboarding/actions?withinDays=N` |
| Respond to (confirm attendance for) any meeting they're invited to | `POST /meetings/{id}/respond` |
| Confirm a meeting was held | `POST /meetings/{id}/confirm-held` |
| View onboarding feedback written about them | `GET /employees/{id}/onboarding/feedback` |
| View tasks set for them during onboarding | `GET /employees/{id}/onboarding/actions` |
| View their assigned competencies | `GET /employees/{id}/competencies` |
| Submit self-assessment scores once a review has started | `POST /competency-cycles/{cycle_id}/self-assessment` |
| View their own radar chart (after manager assessment is complete) | `GET /competency-cycles/{cycle_id}/radar-data` |
| View/fill their own IDP (checkbox + comment per competency) | `GET`/`POST /competency-cycles/{cycle_id}/idp` |
| Organize a meeting with: their direct manager, their team's manager, their assigned HRBP, or the HR Manager | `POST /meetings` |
| Submit their own continue/exit onboarding decision (see note below) | `POST /employees/{id}/onboarding/employee-decision` |

## MANAGER

Has all EMPLOYEE capabilities, plus, for their **direct reports**
(`Employee.manager_id == self`):

| Capability | Endpoint |
|---|---|
| View direct reports (list) and their full profiles | `GET /employees`, `GET /employees/{id}` |
| View onboarding feedback HRBP wrote about a direct report (month 1) | `GET /employees/{id}/onboarding/feedback` |
| Set a direct report's month-2 onboarding tasks | `POST /employees/{id}/onboarding/actions` |
| Organize meetings with direct reports | `POST /meetings` |
| Confirm a meeting was held | `POST /meetings/{id}/confirm-held` |
| Submit manager-assessment scores for a direct report's competency cycle | `POST /competency-cycles/{cycle_id}/manager-assessment` |
| View a direct report's radar chart | `GET /competency-cycles/{cycle_id}/radar-data` |
| Assign competencies to a direct report | `POST /employees/{id}/competencies` |
| Submit the manager-side onboarding decision (see note below) | `POST /employees/{id}/onboarding/manager-decision` |

> **"Team" scope note:** MANAGER's scope everywhere above is the direct
> `manager_id` hierarchy, **not** the formal `Team` entity
> (`Team.team_manager_id`). Those are two different concepts in this
> codebase — see `app/models/team.py` vs `Employee.manager_id`. If your
> org chart ever needs a MANAGER to see a formally-assigned `Team` they
> lead but don't directly manage every member of, that's a deliberate gap
> today, not a bug — it was a scoped decision (confirmed with product) to
> keep "team" = direct reports for MANAGER-scoped endpoints.

## HRBP

Has all EMPLOYEE capabilities, plus, for employees in their
**assigned teams** (`HrbpTeamAssignment`):

| Capability | Endpoint |
|---|---|
| Create a new employee, in a team they're assigned to | `POST /employees` (`username` must be globally unique — enforced by a DB constraint, returns 409 on conflict) |
| Start/define an employee's onboarding path | `POST /employees/{id}/onboarding` |
| Define each month's onboarding phase | `POST /employees/{id}/onboarding/phases` |
| Set month-1 tasks; write post-meeting feedback (auto-notifies the employee's manager) | `POST /employees/{id}/onboarding/actions`, `POST /employees/{id}/onboarding/feedback` |
| Fill in month-2 tasks if the manager missed the end-of-day deadline (triggered by the scheduled `check-month2-tasks-deadline` job — see `docs/DEPLOYMENT.md` §4) | `POST /employees/{id}/onboarding/actions` |
| Assign competencies to an employee (e.g. month-3 "next PR" competencies) | `POST /employees/{id}/competencies` |
| Record the final continue/exit decision, including exit type (RESIGNATION/TERMINATION) — see note below | `PATCH /employees/{id}/status` |
| Start a performance review; **always** schedules a mandatory meeting with the employee and their manager and notifies both | `POST /competency-cycles/{cycle_id}/start-review` |
| Write comments/tasks on an employee's IDP | `POST /competency-cycles/{cycle_id}/idp` |
| View any team member's radar chart | `GET /competency-cycles/{cycle_id}/radar-data` |
| View the teams they're assigned to (and which HRBPs are on each) | `GET /teams` |
| View full profile of anyone in an assigned team | `GET /employees/{id}` |
| Organize meetings with anyone in an assigned team | `POST /meetings` |

## HR_MANAGER

Has **all HRBP capabilities, unrestricted** (no team-assignment scoping —
`require_employee_scope`/`require_team_scope` pass HR_MANAGER through
unconditionally), plus:

| Capability | Endpoint |
|---|---|
| View every team (not just assigned ones), with each team's HRBP list | `GET /teams` |
| Assign / unassign an HRBP to a team | `POST /teams/{id}/hrbps`, `DELETE /teams/{id}/hrbps/{hrbp_id}` |
| View any employee's full profile, org-wide | `GET /employees/{id}` |
| Organize a meeting with anyone — any HRBP, any Employee, any Manager, org-wide | `POST /meetings` |

---

## The onboarding continue/exit decision: two independent paths

There are deliberately two ways an onboarding's final continue/exit outcome
gets recorded, and they're kept **consistent but not merged**:

1. **HRBP direct authority** — `PATCH /employees/{id}/status`. HRBP or
   HR_MANAGER sets `Employee.status` directly (with a required `exitType` if
   EXITED). If the employee has an open `Onboarding`
   (`IN_PROGRESS`/`FINAL_DECISION_PENDING`), it's finalized to match
   (`EXITED`/`COMPLETED`) in the same call. **This always wins** — once
   HRBP acts, `Onboarding.status` moves off `FINAL_DECISION_PENDING`, which
   causes path 2 below to reject with 409 if attempted afterward.
2. **Mutual consent** — `POST /employees/{id}/onboarding/employee-decision`
   (EMPLOYEE) and `POST /employees/{id}/onboarding/manager-decision`
   (MANAGER/HR_MANAGER). Each party records their own preference; once both
   say CONTINUE (or either says EXIT), the onboarding auto-finalizes the
   same way. Only usable while `Onboarding.status == FINAL_DECISION_PENDING`.

If an employee/manager recorded a preference via path 2 before HRBP acts
via path 1, that individual preference (`Onboarding.employee_decision` /
`manager_decision`) is preserved as a historical record even if HRBP's
final call overrides it — this is intentional (an audit trail of "what the
employee said" vs. "what was ultimately decided"), not a bug.

## Known deliberate gaps (not oversights)

- **Meeting confirmation is meeting-scoped, not phase-scoped.**
  `POST /meetings/{id}/respond` and `POST /meetings/{id}/confirm-held` work
  identically regardless of which onboarding month/phase the meeting
  belongs to. Phase-specific business rules (e.g. "the month-1 meeting must
  have been held before advancing to month 2") live in the endpoints that
  consume that state (`notify-manager-after-hrbp`,
  `check-month2-tasks-deadline`), which read `Meeting.onboarding_month`
  directly — there's no need for separate per-phase respond/confirm
  endpoints.
- **`GET /health` has no DB check** — see `docs/DEPLOYMENT.md` §6.
