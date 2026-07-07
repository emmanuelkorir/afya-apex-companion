# Afya Apex Companion – Implementation Roadmap

This roadmap is designed so that **each phase builds on the previous one**. By the end, you'll have a production-ready architecture where Telegram, FastAPI, Supabase, Prisma, and Playwright work together cleanly.

---

# Phase 1 – Foundation

### Objective

Establish the project structure, configuration, and development environment.

### Tasks

- [ ] Organize project folders.
- [ ] Configure `uv`.
- [ ] Configure environment variables.
- [ ] Configure logging.
- [ ] Configure settings management.
- [ ] Configure Prisma.
- [ ] Configure Supabase.
- [ ] Create database connection.
- [ ] Verify migrations work.
- [ ] Configure Playwright.
- [ ] Configure Telegram Bot SDK.

### Deliverables

- Stable project structure.
- Environment variables working.
- Database connected.
- Telegram bot running.
- Playwright launches successfully.

---

# Phase 2 – Browser & EMR Client

### Objective

Build a reusable Playwright client that can automate the EMR.

### Tasks

- [ ] Create `BrowserManager`.
- [ ] Implement browser lifecycle.
- [ ] Implement browser context management.
- [ ] Implement page management.
- [ ] Create `LoginService`.
- [ ] Implement EMR login.
- [ ] Handle double-login requirement.
- [ ] Wait for authentication completion.
- [ ] Save storage state.
- [ ] Restore storage state.

### Deliverables

- BrowserManager.
- LoginService.
- Working login.
- Session restoration.

---

# Phase 3 – Database Layer

### Objective

Persist users and browser sessions.

### Tasks

- [ ] Create User model.
- [ ] Create EMRSession model.
- [ ] Create repositories.
- [ ] UserRepository.
- [ ] SessionRepository.
- [ ] CRUD operations.
- [ ] Session serialization.
- [ ] Session restoration.

### Deliverables

- Users stored.
- Sessions stored.
- Prisma repositories complete.

---

# Phase 4 – Authentication System

### Objective

Authenticate Telegram users before allowing EMR access.

### Tasks

- [ ] Create AuthenticationService.
- [ ] Check if Telegram user exists.
- [ ] Auto-register new users.
- [ ] Add approval workflow.
- [ ] Reject unauthorized users.
- [ ] Restore Playwright session.
- [ ] Validate restored session.
- [ ] Re-login if expired.
- [ ] Save updated session.

### Deliverables

- Full authentication pipeline.
- Automatic session management.

---

# Phase 5 – FastAPI Backend

### Objective

Create the application's central backend.

### Tasks

- [ ] Create FastAPI application.
- [ ] Dependency Injection.
- [ ] Startup events.
- [ ] Shutdown events.
- [ ] Health endpoint.
- [ ] Authentication middleware.
- [ ] Error handling.
- [ ] API versioning.
- [ ] Logging middleware.

### Deliverables

- Production-ready backend.

---

# Phase 6 – Telegram Integration

### Objective

Use Telegram as the user interface.

### Tasks

- [ ] Configure bot.
- [ ] Register handlers.
- [ ] Create command routing.
- [ ] Connect to FastAPI services.
- [ ] Implement `/start`.
- [ ] Implement `/help`.
- [ ] Implement `/login`.
- [ ] Handle errors.
- [ ] Improve user messages.

### Deliverables

- Fully functioning Telegram interface.

---

# Phase 7 – EMR Navigation

### Objective

Create reusable page objects.

### Tasks

- [ ] DashboardPage.
- [ ] PatientSearchPage.
- [ ] PatientDetailsPage.
- [ ] LaboratoryPage.
- [ ] PharmacyPage.
- [ ] AdmissionsPage.
- [ ] TheatrePage.
- [ ] BillingPage.

### Deliverables

- Page Object Model complete.

---

# Phase 8 – Core EMR Features

### Objective

Expose useful EMR functionality.

### Tasks

- [ ] Search patient.
- [ ] Open patient.
- [ ] Patient demographics.
- [ ] Visits.
- [ ] Admissions.
- [ ] Laboratory.
- [ ] Imaging.
- [ ] Prescriptions.
- [ ] Billing.
- [ ] Clinical notes.

### Deliverables

- Working EMR automation.

---

# Phase 9 – Business Services

### Objective

Move Playwright logic out of handlers.

### Tasks

- [ ] PatientService.
- [ ] LaboratoryService.
- [ ] PharmacyService.
- [ ] AdmissionService.
- [ ] ImagingService.
- [ ] NotificationService.

### Deliverables

- Clean service layer.

---

# Phase 10 – Telegram Commands

### Objective

Expose EMR features through Telegram.

### Tasks

- [ ] `/patient`
- [ ] `/visit`
- [ ] `/lab`
- [ ] `/admit`
- [ ] `/prescription`
- [ ] `/notes`
- [ ] `/billing`
- [ ] `/logout`

### Deliverables

- Fully interactive Telegram assistant.

---

# Phase 11 – Authorization

### Objective

Control who can use the application.

### Tasks

- [ ] Admin role.
- [ ] Doctor role.
- [ ] Nurse role.
- [ ] Read-only users.
- [ ] User approval.
- [ ] User suspension.
- [ ] Audit logging.

### Deliverables

- Secure user management.

---

# Phase 12 – Reliability

### Objective

Make automation resilient.

### Tasks

- [ ] Retry failed operations.
- [ ] Detect expired sessions.
- [ ] Automatic re-login.
- [ ] Browser recovery.
- [ ] Timeout handling.
- [ ] Graceful shutdown.
- [ ] Session cleanup.

### Deliverables

- Reliable automation.

---

# Phase 13 – Observability

### Objective

Monitor and debug the system.

### Tasks

- [ ] Structured logging.
- [ ] Request logging.
- [ ] Browser logs.
- [ ] Error tracking.
- [ ] Performance metrics.
- [ ] Health monitoring.

### Deliverables

- Production monitoring.

---

# Phase 14 – Testing

### Objective

Ensure correctness and prevent regressions.

### Tasks

- [ ] Unit tests.
- [ ] Repository tests.
- [ ] Login tests.
- [ ] Session tests.
- [ ] Telegram tests.
- [ ] FastAPI tests.
- [ ] Playwright integration tests.

### Deliverables

- Comprehensive automated test suite.

---

# Phase 15 – Deployment

### Objective

Deploy the application reliably.

### Tasks

- [ ] Environment configuration.
- [ ] Dockerfile.
- [ ] Docker Compose.
- [ ] CI/CD pipeline.
- [ ] Production secrets.
- [ ] Reverse proxy.
- [ ] HTTPS.
- [ ] Backups.

### Deliverables

- Production deployment.

---

# Final Architecture

```text
                    Telegram
                        │
                        ▼
               python-telegram-bot
                        │
                        ▼
                    FastAPI API
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
 Authentication     Business       User Services
    Service         Services
         │              │
         ▼              ▼
     EMR Client     Prisma ORM
         │              │
         ▼              ▼
 Browser Manager   Supabase PostgreSQL
         │
         ▼
  Playwright Pages
         │
         ▼
     Apex EMR
```
