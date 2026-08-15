# TeluAI v20 — Owner/Admin/User + Database Management

## Added
- Proper application roles: `owner`, `admin`, `user`.
- Secure session-based role authorization; admin endpoints no longer depend on `ADMIN_TOKEN`.
- One-time owner bootstrap using `TELUAI_OWNER_EMAIL`.
- Owner-only user role management.
- Owner-only user activation/deactivation and deletion.
- Admin/owner database statistics.
- Admin/owner user listing.
- Admin/owner language database snapshot.
- Admin/owner audit-log viewing.
- Admin/owner Melimi learning approval/rejection.
- Audit records for role, activation, deletion, owner bootstrap, and learning-review actions.
- `users.is_active` for account control.
- PostgreSQL migration `002_roles_and_admin.sql`.
- Updated admin dashboard to use the authenticated session instead of an admin token.

## Role policy
- `owner`: highest application role; can manage users and admins.
- `admin`: approved administrator; can review Melimi learning and inspect application/database information.
- `user`: normal account; no administration access.

The owner cannot demote/deactivate/delete their own account through the application.
Admins cannot promote themselves, modify the owner, or change user roles.

## Owner setup
1. Register your account normally.
2. Set `TELUAI_OWNER_EMAIL` in Render to exactly that email.
3. Log in as that account.
4. POST `/auth/bootstrap-owner` once (the admin UI can be opened after the role is established).
5. Remove `TELUAI_OWNER_EMAIL` from Render after successful bootstrap.

`DATABASE_URL` remains the production PostgreSQL connection variable.
