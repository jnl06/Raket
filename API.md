# Raket API

JSON API under `/api/`, built with plain Django (no extra packages). It backs the desktop
screens in the Figma file: Home, Jobs, Job Page, Post Jobs, Manage posted jobs, Manage
applicants, Applied jobs, Log in and Sign up.

## Conventions

- **Auth:** Django session cookies. Call `GET /api/auth/csrf/` once on page load, then send the
  returned token on every `POST/PATCH/PUT/DELETE` as the `X-CSRFToken` header.
- **Bodies:** JSON (`Content-Type: application/json`). Only `POST /api/me/` also accepts
  `multipart/form-data` (needed to upload a resume — Django doesn't parse multipart on PATCH).
- **Errors:** every error is `{"error": {"code", "message", "fields"?}}`. `fields` maps a field
  name to a list of messages (use it to show inline form errors). Status codes: `400` validation,
  `401` not signed in, `403` wrong role / not the owner, `404`, `405`, `409` state conflict.
- **Lists:** `?page=` and `?page_size=` (max 50). Response includes
  `pagination: {count, page, page_size, num_pages, shown, has_next, has_previous}` — use
  `shown`/`count` for "Showing 9 of 10 applicants".
- **Roles:** `job_seeker` (worker) and `job_provider` (household), chosen at sign-up.
- **Money:** pesos; `payment: {currency:"PHP", amount, max_amount|null, period:"day|hour|job"}`.

## Auth & profile

| Method & path | Who | Notes |
|---|---|---|
| `GET /api/auth/csrf/` | anyone | Sets the CSRF cookie, returns `{csrfToken}` |
| `POST /api/auth/register/` | anyone | `{role, full_name, email, phone, password, confirm_password, agree_terms}` → 201 `{user}` and signs in |
| `POST /api/auth/login/` | anyone | `{email, password, remember_me}`. Without `remember_me` the session ends when the browser closes |
| `POST /api/auth/logout/` | signed in | |
| `POST /api/auth/password-reset/` | anyone | `{email}`; always 200. Emails a link to `{FRONTEND_URL}/reset-password/?uid=…&token=…` (console backend in dev) |
| `POST /api/auth/password-reset/confirm/` | anyone | `{uid, token, new_password}` |
| `GET /api/me/` | signed in | Current user + profile |
| `PATCH /api/me/` | signed in | Any of `full_name, phone, location, bio, skills (list|csv), availability (["full_time","part_time","one_time"])`, `remove_resume` |
| `POST /api/me/` | signed in | Same fields as multipart; include a `resume` file (.pdf/.doc/.docx, ≤ 5 MB) |
| `GET /api/me/resume/` | signed in | Download own resume |

## Jobs (Home, Jobs list, Job Page, Post Jobs)

| Method & path | Who | Notes |
|---|---|---|
| `GET /api/categories/` | anyone | Categories with open-job counts, most popular first (Home "Popular searches"); also the option lists for dropdowns (`employment_types`, `durations`, `schedules`, `pay_periods`) |
| `GET /api/jobs/` | anyone | Active, not-yet-past jobs. Params: `q`, `category`, `employment_type`, `duration` (`all` = no filter), `location`, `sort` = `relevance` (default) `newest` `oldest` `pay_high` `pay_low` `work_date` |
| `GET /api/jobs/{id}/` | anyone | Full Job Page data: `qualifications` (from `requirements`, one per line), `experience`, `industry`, `how_to_apply`, `roles_open`, `my_application`, `is_owner`. Closed jobs are 404 except to the owner and applicants |
| `POST /api/jobs/` | provider | Create. Requires `confirm: true`. Fields: `title, category, description, location, work_date, work_schedule, estimated_payment, number_of_workers` + optional `max_payment, pay_period, requirements, employment_type, duration, experience, industry, how_to_apply` |
| `PATCH /api/jobs/{id}/` | owner | Partial update (omitted fields keep their values) |
| `POST /api/jobs/{id}/close/` | owner | Stop accepting applicants |
| `POST /api/jobs/{id}/repost/` | owner | Copy into a new active post; body may override fields (send a new `work_date` if the old one has passed) |

## Household: Manage posted jobs & Manage applicants

| Method & path | Notes |
|---|---|
| `GET /api/me/jobs/` | `stats {total_jobs, active_jobs, closed_jobs, total_applicants}` (ignore filters) + rows with `applicant_count`. Params: `status` (`all|active|closed`), `q` (title/location), `sort` = `recent` `oldest` `work_date` `applicants` |
| `GET /api/jobs/{id}/applicants/` | Applicant cards (default 9 per page) + `job` header + status `counts`. Params: `status`, `q` (name). Contact email/phone appear only after the applicant is **hired** |
| `PATCH /api/applications/{id}/` | `{status: "hired" \| "rejected" \| "under_review"}`. Hiring is blocked once all roles are filled; filling the last role auto-closes the job. A hired application can't be rejected. Same status twice is a no-op |
| `GET /api/applications/{id}/resume/` | "View resume" — owner or applicant only. When the **owner** opens it, `submitted` → `under_review` |

## Worker: Apply & Applied jobs

| Method & path | Notes |
|---|---|
| `POST /api/jobs/{id}/apply/` | Seekers only. Optional `{cover_note}`. `409 already_applied` / `job_closed`; `403 own_job` |
| `GET /api/me/applications/` | `counts {total, submitted, under_review, hired, rejected}` for the summary cards / tabs, rows with job + household + daily pay + status. Params: `status`, `q` (job title, location or household name) |
| `DELETE /api/applications/{id}/` | Withdraw (not allowed once hired) |

Application statuses: `submitted`, `under_review`, `hired`, `rejected` (shown as "Not selected").

## Not included (yet)

- **Continue with Google** (needs OAuth client credentials — e.g. `django-allauth`).
- **Review and rating** (appears in the footer only; no screen designed).
- The existing server-rendered `/post-job/` page is unchanged and still works.
