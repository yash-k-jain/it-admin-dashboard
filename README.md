# FastAPI Backend with MongoDB

Complete backend implementation for the assignment in the supplied specification.

## Features

- User registration and bcrypt password hashing
- JWT access tokens in HTTP-only cookies
- Refresh-token rotation
- Login/logout
- `/me`
- Forgot/reset password
- Optional SMTP email delivery
- Change password
- User profile management
- USER and IT_ADMIN roles
- IT Admin user search/list/detail/update/delete
- Activate/deactivate/block users
- Admin password reset
- Admin dashboard statistics
- Audit logging
- Login-attempt rate limiting
- System settings
- Health endpoint
- Swagger/OpenAPI
- Validation and structured HTTP errors
- Docker and Docker Compose
- Pytest tests
- Required MongoDB collections

## MongoDB collections

The application uses:

- users
- roles (role definitions can be represented here if you want a separate role catalog)
- refresh_tokens
- password_reset_tokens
- audit_logs
- login_attempts
- system_settings

## Local setup

1. Create a virtual environment:
   `python -m venv .venv`

2. Activate it.

3. Install:
   `pip install -r requirements.txt`

4. Copy `.env.example` to `.env` and set `JWT_SECRET`.

5. Start MongoDB.

6. Run:
   `uvicorn app.main:app --reload`

7. Open:
   `http://localhost:8000/docs`

## Docker

Copy `.env.example` to `.env`, set `JWT_SECRET`, then:

`docker compose up --build`

## Creating the first IT Admin

Public registration deliberately forces new accounts to `USER`, preventing privilege escalation.

After registering a normal account, promote it directly in MongoDB:

```javascript
use intern-dseu
db.users.updateOne(
  { email: "admin@example.com" },
  { $set: { role: "IT_ADMIN" } }
)
```

Then log in again to receive an access token containing the IT_ADMIN role.

## API overview

### Authentication

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/change-password`
- `POST /api/v1/auth/forgot-password`
- `POST /api/v1/auth/reset-password`
- `POST /api/v1/auth/logout`

### User

- `GET /api/v1/users/profile`
- `PATCH /api/v1/users/profile`

### IT Admin

- `GET /api/v1/admin/users`
- `GET /api/v1/admin/users/{user_id}`
- `PATCH /api/v1/admin/users/{user_id}`
- `POST /api/v1/admin/users/{user_id}/reset-password`
- `DELETE /api/v1/admin/users/{user_id}`
- `GET /api/v1/admin/dashboard`
- `GET /api/v1/admin/audit-logs`

### System

- `GET /api/v1/system/settings`
- `PUT /api/v1/system/settings/{key}`

### Health

- `GET /api/v1/health`

## Important security notes

- Never commit `.env`.
- Use a strong random `JWT_SECRET`.
- Set `COOKIE_SECURE=true` behind HTTPS.
- For production, restrict CORS to the exact frontend origin.
- Do not allow public registration to choose an admin role.
- Password reset responses intentionally do not reveal whether an email exists.
- Refresh tokens are stored hashed and rotated on use.
- Reset tokens are one-time and expire automatically through MongoDB TTL indexes.
