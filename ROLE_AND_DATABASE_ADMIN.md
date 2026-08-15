# TeluAI v20 — Ownership and Database Administration

## Roles

- `owner`: highest TeluAI application role. Can manage users/admins, account activation, deletion, and all admin/database views.
- `admin`: approved administrator. Can review Melimi learning and inspect database/application information. Cannot change roles or modify the owner.
- `user`: normal account.

Render account ownership and TeluAI application ownership are separate concepts. The Render account controls infrastructure; the TeluAI `owner` role controls application administration.

## First owner setup

1. Deploy the v20 code.
2. Set `TELUAI_OWNER_EMAIL` in the Render Web Service Environment to the exact email you will use for the owner account.
3. Register that account normally.
4. Log in as that account.
5. Call `POST /auth/bootstrap-owner` once (the request uses the authenticated session).
6. Confirm `/auth/me` returns `role: owner`.
7. Remove `TELUAI_OWNER_EMAIL` from Render after successful bootstrap.

The bootstrap endpoint refuses to create a second owner.

## Admin management

The owner can promote an existing user to `admin`, demote an admin to `user`, disable/enable accounts, or delete non-owner accounts from `/admin`.

Admins can:
- review pending Melimi learning
- approve/reject candidates
- view database statistics
- view a language database snapshot
- view audit logs

Admins cannot:
- promote themselves
- change user roles
- modify/demote the owner
- deactivate/delete the owner

## Database management

The `/admin` dashboard exposes application-level database management only. It does not expose raw SQL or PostgreSQL credentials.

The database view includes:
- user counts
- conversation/message counts
- Melimi roots/documents/affixes/rules/examples
- pending learning count
- feedback/usage/audit counts
- user list and status
- recent Melimi roots/rules
- audit log

PostgreSQL credentials remain in Render environment configuration and must not be given to normal TeluAI admins.
