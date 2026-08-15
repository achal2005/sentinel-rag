# Account Management

This document covers the account model — organizations, members, roles, and teams — and the lifecycle operations for managing them: inviting people, changing roles, enforcing security policies, transferring ownership, and closing an account.

---

## The account model `[acct-01]`

Meridian has three levels:

- **Organization** — the top-level account. It owns all services, resources, API keys, billing, and members. Every user acts *within* an organization.
- **Member** — a user who belongs to an organization, with a **role** that determines what they can do.
- **Team** *(Team and Enterprise plans)* — a named group of members you can grant access to a subset of services, so you don't manage permissions person-by-person.

A single user can belong to multiple organizations and switches between them with the organization picker in the dashboard.

---

## Roles and permissions `[acct-02]`

Meridian uses role-based access control. The built-in roles:

| Role | Can do | Cannot do |
|---|---|---|
| **Owner** | Everything, including billing, deleting the org, transferring ownership | — |
| **Admin** | Manage services, deployments, members, API keys, webhooks | Change billing plan, delete the org, transfer ownership |
| **Developer** | Deploy, view services and logs, manage env vars for permitted services | Manage members, view billing, manage org-wide keys |
| **Billing** | View and manage billing, invoices, payment methods | Deploy or change services |
| **Viewer** | Read-only access to services, deployments, and logs | Any write action |

- An organization always has **at least one Owner**.
- On **Team/Enterprise**, permissions can be scoped further via **Teams** (see below), so a Developer might have write access to some services and read-only to others.
- API keys carry **scopes** rather than roles; a key never exceeds the permissions implied by its scopes regardless of who created it. See [api-keys.md](./api-keys.md#scopes-and-least-privilege-key-04).

---

## Inviting members `[acct-03]`

Owners and Admins can invite people:

1. **Settings → Members → Invite**.
2. Enter the email address and choose a role (and team, if applicable).
3. The invitee receives an email link valid for **7 days**.
4. They accept, sign in (or sign up), and join with the assigned role.

**API:**
```bash
curl https://api.meridian.io/v1/members \
  -H "Authorization: Bearer msk_live_xxxxxxxxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{ "email": "dev@example.com", "role": "developer" }'
```

Requires the `members:write` scope. Pending invitations appear under **Settings → Members → Pending** and can be resent or revoked.

---

## Changing roles and removing members `[acct-04]`

- **Change a role:** **Settings → Members → {member} → Change role**, or `PATCH /v1/members/{id}`.
- **Remove a member:** **Settings → Members → {member} → Remove**, or `DELETE /v1/members/{id}`. The person immediately loses all access; their personal access tokens are invalidated. Any organization API keys they created **keep working** (keys belong to the org, not the person) — review and rotate them if the departure is sensitive. See [api-keys.md](./api-keys.md#revoking-a-key-key-07).
- You cannot remove or demote the **last Owner**; promote someone else first.

---

## Teams `[acct-05]`

*(Team and Enterprise plans)* Teams let you grant access to a subset of services at once.

1. **Settings → Teams → Create team** (e.g. `payments`, `frontend`).
2. Add members and give the team a role **on specific services**.
3. A member's effective permission on a service is the **most permissive** of their org role and any team grants.

Teams keep permissions manageable as the org grows: add a new hire to the right teams and they get exactly the access those teams have.

---

## Organization settings `[acct-06]`

Under **Settings → Organization**, Owners and Admins can manage:

- **Name and slug** — the display name and the URL identifier (`dashboard.meridian.io/{slug}`). Changing the slug changes dashboard URLs but not API IDs.
- **Default region** — the region pre-selected when creating new services (see [deployments.md](./deployments.md#regions-dep-03)).
- **Verified domains** — used for SSO and email-domain capture (see [authentication.md](./authentication.md#single-sign-on-sso-auth-04)).
- **Members, Teams, API keys, Webhooks, Billing** — as covered in their respective docs.

Resource IDs (`svc_…`, `dep_…`, `key_…`) are **stable** and never change, even if you rename the org or its slug.

---

## Enforcing security policies `[acct-07]`

Owners and Admins can raise the security floor for everyone:

- **Require MFA** — every member must have a second factor enrolled to access the org. Members without MFA are prompted to enroll at next sign-in and blocked until they do. See [authentication.md](./authentication.md#multi-factor-authentication-mfa-auth-03).
- **Require SSO** — force sign-in through your identity provider for all members on a verified domain, disabling password login for them.
- **Session lifetime** — shorten the default 14-day session for the whole org.
- **API key restrictions** — require IP allowlists on new keys, or restrict who may create org-wide keys.

**Break-glass access:** when **Require SSO** is enabled, at least one Owner retains a recovery login path (a dedicated recovery code flow) so an IdP outage can't lock the whole organization out. Store these recovery codes offline.

---

## Transferring ownership `[acct-08]`

To hand off an organization (for example, when the original creator leaves):

1. The current Owner goes to **Settings → Members → {member} → Transfer ownership** (target must already be a member).
2. Confirm with a re-authentication step (password or MFA).
3. The target becomes an Owner; the previous Owner is downgraded to Admin unless you keep them as a co-Owner.

An organization can have multiple Owners; adding a second Owner before anyone leaves is the safest practice.

---

## Audit log `[acct-09]`

*(Team and Enterprise plans)* Every administrative action — member added/removed, role changed, key created/revoked, policy changed, billing updated — is recorded in the **audit log** under **Settings → Audit log**, with the actor, timestamp, IP, and affected resource. Export it as CSV, or stream it via the audit events available in [webhooks.md](./webhooks.md). Use it for incident review and compliance evidence.

---

## Closing an account `[acct-10]`

An Owner can close an organization under **Settings → Organization → Close organization**:

1. All services are stopped and scheduled for deletion.
2. A final invoice is issued for outstanding usage (see [billing.md](./billing.md)).
3. Data is deleted per the retention schedule in [security.md](./security.md#data-retention-and-deletion-sec-08).

Export your data, invoices, and any environment variables you need **before** closing — deletion is irreversible after the retention window. Removing *yourself* from an org you don't own is done via **Leave organization** instead.

---

## Frequently asked questions `[acct-11]`

**I removed a teammate. Do the API keys they created still work?**
Yes — API keys belong to the **organization**, not the person, so they keep working. Their personal access tokens are invalidated immediately. Rotate any org keys they created if the departure is sensitive. See [Changing roles and removing members](#changing-roles-and-removing-members-acct-04).

**How do I hand over an organization I own?**
Use **Settings → Members → Transfer ownership** (target must already be a member) and confirm with re-authentication. Adding a second Owner *before* anyone leaves is the safest practice. See [Transferring ownership](#transferring-ownership-acct-08).

**Can I require everyone in my org to use MFA?**
Yes. Owners/Admins can require MFA (and SSO) org-wide; members are blocked until they enroll. See [Enforcing security policies](#enforcing-security-policies-acct-07).

**Who can see billing and invoices?**
Only **Owner** and **Billing** roles. Developers and Viewers cannot view billing. See [Roles and permissions](#roles-and-permissions-acct-02).

**Why can't I remove the last Owner?**
An organization must always have at least one Owner. Promote another member to Owner first, then change or remove the original. See [Changing roles and removing members](#changing-roles-and-removing-members-acct-04).

**What if our identity provider goes down and everyone's locked out?**
When **Require SSO** is enabled, at least one Owner keeps a break-glass recovery login. Store those recovery codes offline. See [Enforcing security policies](#enforcing-security-policies-acct-07).

---

## Related documents

- [authentication.md](./authentication.md) — sign-in, MFA, SSO.
- [api-keys.md](./api-keys.md) — keys, scopes, and ownership.
- [billing.md](./billing.md) — who can manage billing.
- [security.md](./security.md) — data retention and deletion.
