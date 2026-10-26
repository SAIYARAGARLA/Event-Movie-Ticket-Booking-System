# Event & Movie Ticket Booking System (FastAPI)

A modular backend for event and movie ticket booking built with FastAPI, SQLAlchemy, MySQL, Alembic, Redis, JWT authentication, mock payments, QR-coded PDF tickets, WebSockets, email utilities, waitlists, cancellations, refunds, and reports.

> **Project status:**
The Event & Movie Ticket Booking System is developed using Python, FastAPI, MySQL, SQLAlchemy, Alembic, and Redis.
It includes authentication, seat management, booking, simulated payments, QR-code tickets, PDF generation, and reporting.
Core booking and payment workflows have been tested, and API documentation is available through Swagger UI.


## 1. Features

- JWT-based authentication and role-based access control
- Admin, Organizer, Customer, and Staff workflows
- Venue, screen, and seat management
- Event and show creation and management
- Redis-based seat locks and caching/rate-limiting functionality
- Booking and simulated payment success/failure
- HMAC-signed QR codes and PDF ticket generation
- Ticket scanning and duplicate-scan validation
- WebSocket-based seat-map updates
- Cancellation, refunds, waitlists, and reports
- Alembic database migrations
- SMTP email utility and scheduled jobs

## 2. Technology stack

- Python
- FastAPI and Uvicorn
- SQLAlchemy and Alembic
- MySQL 8+
- Redis 6+
- JWT authentication and bcrypt password hashing
- PDF and QR-code generation
- WebSockets

Use the Python version and dependency versions supported by the project's `requirements.txt`. Python 3.11 or 3.12 is a reasonable starting point if all dependencies support it.

## 3. Prerequisites

Install and configure:

1. Python
2. MySQL Server and MySQL Workbench
3. Redis-compatible service, such as Redis or Memurai on Windows
4. Git
5. VS Code (recommended)

Ensure MySQL and Redis are running before starting the application.

## 4. Installation on Windows

Open PowerShell in the project root—the directory containing `requirements.txt` and `alembic.ini`.

```powershell
# Create a virtual environment if one does not already exist
py -m venv .venv

# Activate it
.\.venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If the virtual environment already exists, activate it rather than creating another one.

## 5. Environment configuration

Copy the example environment file if it exists:

```powershell
Copy-Item .env.example .env
```

If `.env.example` is not present, create `.env` using the configuration variables referenced by the application settings.

Configure the database connection, Redis URL, JWT signing secret, QR/HMAC signing secret, and SMTP settings as required by the project.

Example values below are placeholders, not working credentials:

```dotenv
DATABASE_URL=<your-mysql-connection-string>
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=<your-long-random-secret>
QR_SECRET_KEY=<your-long-random-secret>

SMTP_HOST=<your-smtp-host>
SMTP_PORT=587
SMTP_USERNAME=<your-smtp-username>
SMTP_PASSWORD=<your-smtp-app-password>
SMTP_FROM_EMAIL=<your-sender-email>
SMTP_USE_TLS=true
```

**Important:** These names are illustrative. Match them to the exact variable names used in your application's configuration files. Do not overwrite working settings with these placeholders.

Never commit `.env`, real passwords, JWTs, SMTP credentials, or signing secrets to GitHub.

## 6. MySQL setup

Create the development database in MySQL Workbench:

```sql
CREATE DATABASE ticket_booking_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
```

Update your application's database configuration with the correct MySQL username, password, host, port, and database name.

The database name above is an example. Use the name configured in your project.

## 7. Redis setup

Start your Redis-compatible service.

If Redis CLI is available, verify connectivity with:

```powershell
redis-cli ping
```

Expected response:

```text
PONG
```

For Memurai or another Windows-compatible Redis service, use its configured service and CLI commands.

Redis supports functionality such as temporary seat locks and other configured caching or rate-limiting operations. Seat locks use an expiry so abandoned locks can eventually be released.

If Redis is unavailable, some operations may fail. The seat-lock implementation is expected to return a service-unavailable response when Redis is required but unavailable.

## 8. Database migrations with Alembic

Migration files are part of the project and should be committed to GitHub.

From the project root, activate the virtual environment and run:

```powershell
alembic current
alembic heads
alembic history
alembic upgrade head
```

These commands inspect the current database revision, available migration heads, migration history, and apply pending migrations.

To create a migration after changing SQLAlchemy models:

```powershell
alembic revision --autogenerate -m "describe schema change"
```

Review the generated migration before applying it:

```powershell
alembic upgrade head
```

**Do not generate another initial migration just to follow this README.** If the existing migration files are present, inspect and use them. Generate a new revision only when an actual schema change requires one.

The application should use Alembic for schema management rather than relying on SQLAlchemy `create_all()`.

## 9. Run the application

From the directory containing the `app` package:

```powershell
python -m uvicorn app.main:app --reload
```

Open:

- Swagger UI: http://127.0.0.1:8000/docs
- Seat-map test page: http://127.0.0.1:8000/seat-map-test

Keep the server terminal open while testing. Use a separate terminal for Git commands or other maintenance tasks.

## 10. Initial admin and test accounts

Public registration is intended for Customer and Organizer roles. Admin accounts should be created through the project's authorized local bootstrap procedure, not through an exposed public admin-registration endpoint.

For a fresh local database, follow the project's existing admin-creation procedure and use the password-hashing utility defined in `app.auth.security`.

Do not run a bootstrap script that creates duplicate accounts in a database already containing an administrator.

### Local test accounts

Use only local development accounts. Record the account email and role for each test account, and use the password you actually set for that account.

| Role | Purpose |
|---|---|
| Admin | Approve organizers, create venue resources, and create staff accounts |
| Organizer | Create and manage events and shows |
| Customer | Lock seats, create bookings, and make simulated payments |
| Staff | Scan tickets for the assigned venue |

For a fresh setup, create the accounts using the supported registration and admin/staff creation flows. Ensure the Organizer is approved and the Staff account is assigned to the relevant venue.

Do not publish real passwords or access tokens in this README or in screenshots. If fixed local test credentials are required by your mentor, provide them separately through an appropriate submission channel and ensure they are development-only.

## 11. End-to-end testing workflow

1. Start MySQL and Redis.
2. Apply pending Alembic migrations.
3. Start the FastAPI server and open Swagger.
4. Register an Organizer and Customer.
5. Create or verify an Admin account and log in.
6. As Admin, create a venue and screen, create seats, and approve the Organizer.
7. As Organizer, create an event and show, and configure prices for active seat categories.
8. As Customer, inspect available seats, lock seats, and create a booking.
9. Test a successful simulated payment and a failed simulated payment.
10. For a successful payment, download the generated PDF ticket and verify its QR code.
11. As Staff assigned to the venue, test the ticket scan endpoint with the ticket's QR token.
12. Scan the same ticket again and verify that duplicate scanning is rejected as expected.
13. Test the seat map in two browser tabs and verify the WebSocket connection and update messages.
14. Test cancellation, refund, waitlist, and report flows supported by the current implementation.

Use future show times and valid ticket-scanning windows when testing ticket validation.

## 12. API route reference

The following are the main routes documented by the project. Check Swagger for the exact request bodies, parameters, permissions, and response schemas.

- **Authentication:** `/auth/register`, `/auth/login`, `/auth/me`
- **Admin:** `/admin/organizers/{user_id}/approve`, `/admin/staff`
- **Venues and seats:** `/venues`, `/venues/{venue_id}/screens`, `/screens/{screen_id}/seats/bulk`, `/screens/{screen_id}/layout`, `/seats/{seat_id}/status`
- **Events and shows:** `/events`, `/events/{event_id}`, `/events/{event_id}/shows`, `/shows/{show_id}`, `/shows/{show_id}/cancel`
- **Seat availability and locks:** `/shows/{show_id}/seats`, `/shows/{show_id}/lock-seats`
- **Bookings and payments:** `/bookings`, `/bookings/create`, `/bookings/{booking_id}`, `/bookings/{booking_id}/pay`
- **Tickets:** `/bookings/{booking_id}/ticket`, `/tickets/scan`
- **Cancellation and waitlist:** `/bookings/{booking_id}/cancel`, `/bookings/{booking_id}/refunds`, `/shows/{show_id}/waitlist`, `/waitlist/{waitlist_id}`
- **Reports:** `/reports/admin-dashboard`, `/reports/event-sales`, `/reports/occupancy`, `/reports/top-events`, `/reports/refunds`

Use Swagger to confirm the HTTP method for each endpoint. For example, some booking creation routes require a query parameter such as `show_id`.

## 13. WebSocket testing

The documented WebSocket route is:

```text
ws://localhost:8000/ws/shows/{show_id}/seats?token={access_token}
```

Replace `{show_id}` with a valid show ID and `{access_token}` with a valid access token. Treat tokens as secrets.

### Browser-based test

1. Open `/seat-map-test`.
2. Enter the show ID and an appropriate access token.
3. Connect to the WebSocket.
4. Open the same page in a second browser tab and connect to the same show.
5. Perform a supported seat-lock or booking action.
6. Check whether both tabs receive the expected seat-map update.

The initial seat map being sent on connection does not, by itself, prove that live broadcasts work. Verify that the relevant mutation paths publish updates and that both clients receive them.

If updates are missing, inspect the WebSocket implementation and event broadcasts before claiming real-time synchronization is fully verified.

## 14. SMTP configuration

For Gmail SMTP, use an App Password where supported; do not use your normal account password.

Configure the SMTP host, port, sender, username, app password, and TLS options according to the application's configuration.

For Gmail, the usual SMTP host is `smtp.gmail.com` and the submission port is commonly `587` with STARTTLS.

If SMTP settings are blank, the current utility may log that email was skipped. Confirm this behavior in the implementation and check the server logs when testing email-related workflows.

Never commit SMTP credentials.

## 15. Security and assumptions

- Access tokens have a configured expiry; the current project documentation specifies 30 minutes.
- Passwords are stored using bcrypt hashing.
- Redis seat locks use an expiry to prevent abandoned locks from lasting indefinitely.
- Payment processing is simulated; real payment-gateway integration is not implemented.
- QR payloads are signed using HMAC-SHA256.
- Ticket PDFs are generated by the application.
- Confirm timezone handling when creating shows, checking booking windows, and validating scans.
- Use development-only data and credentials.
- Never include real customer information, payment details, access tokens, or environment secrets in screenshots or source control.

## 16. Known limitations and verification status

The following areas require integration testing or further verification before claiming complete behavior:

- Bulk refunds and waitlist notifications when a show is cancelled
- WebSocket broadcasts across all seat-lock, payment, and cancellation paths
- Scheduled reminder jobs
- Rules concerning a single empty seat between occupied seats
- Filtering and sorting edge cases
- Seat-map consistency between confirmed bookings and displayed availability

The seat-layout endpoint should be checked against confirmed bookings. If a confirmed seat is displayed as available, investigate and resolve the inconsistency before presenting the layout as correct.

## 17. Submission screenshots

Include screenshots captured from your own running application for:

1. Swagger API responses
2. Successful mock payment
3. Failed mock payment
4. Generated PDF ticket with QR code
5. Successful ticket scan
6. Repeated ticket scan returning the expected duplicate-scan response
7. Live seat-map updates in two browser tabs

Keep screenshots in a clearly named folder, for example `screenshots/`. Do not include real customer data, passwords, access tokens, or SMTP credentials.

## 18.## Screenshots

Project screenshots demonstrating API documentation, database migrations, booking workflows, payment results, and generated tickets are available in the `screenshots/` folder. 

## 19. GitHub submission checklist

Before pushing the project:

- Confirm that the application source code is included.
- Confirm that the existing Alembic migration files are included.
- Confirm that `requirements.txt`, `README.md`, and any safe example configuration file are included.
- Exclude `.env`, virtual environments, caches, generated PDFs, local logs, and private credentials.
- Check `git status` and review the staged changes before committing.
- Verify that no real passwords, signing secrets, or tokens are included in the commit.

After these checks, commit and push the final project to the intended GitHub repository.
