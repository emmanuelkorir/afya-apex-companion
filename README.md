# Afya Apex Companion

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://core.telegram.org/bots)

**Your AI-powered assistant for the Afya Apex EMR – right inside Telegram.**

Afya Apex Companion is a Telegram bot that gives healthcare professionals secure, conversational access to the Afya Apex Electronic Medical Records system. It automates the browser-based EMR using Playwright, manages user sessions, and exposes key clinical workflows through simple chat commands.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Database Setup](#database-setup)
  - [Running the Application](#running-the-application)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Telegram-native interface** – all interactions happen through familiar Telegram commands.
- **Automated EMR login & session management** – logs into the Afya Apex web portal, handles dual-login, stores and restores sessions securely.
- **Role-based access control** – admin, doctor, nurse, and read-only roles with approval workflows.
- **Core clinical workflows** – search patients, view demographics, visits, lab results, prescriptions, admissions, billing, and clinical notes.
- **Resilient browser automation** – retry logic, automatic re-login on session expiry, graceful error handling.
- **Real-time observability** – structured logging, request tracing, performance metrics, and health monitoring.
- **Production-ready deployment** – Docker, Docker Compose, CI/CD pipeline, HTTPS, and database backups.

---

## Tech Stack

| Layer                  | Technology                                                                        |
| ---------------------- | --------------------------------------------------------------------------------- |
| **Bot interface**      | [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) |
| **Backend API**        | [FastAPI](https://fastapi.tiangolo.com/)                                          |
| **Browser automation** | [Playwright](https://playwright.dev/python/)                                      |
| **Database**           | [Supabase](https://supabase.com/) (PostgreSQL)                                    |
| **ORM**                | [Prisma Client Python](https://github.com/RobertCraigie/prisma-client-py)         |
| **Package manager**    | [uv](https://github.com/astral-sh/uv)                                             |
| **Logging**            | `structlog` / standard `logging`                                                  |
| **Containerization**   | Docker, Docker Compose                                                            |

---

## Architecture

```mermaid
graph TD
    TG[Telegram User] --> Bot[python-telegram-bot]
    Bot --> API[FastAPI Backend]
    API --> Auth[Authentication Service]
    API --> Biz[Business Services]
    API --> UserSvc[User Services]
    Auth --> EMRClient[EMR Client]
    Biz --> EMRClient
    Biz --> Prisma[Prisma ORM]
    UserSvc --> Prisma
    EMRClient --> BrowserMgr[Browser Manager]
    BrowserMgr --> Pages[Playwright Page Objects]
    Pages --> AfyaApexEMR[Apex EMR Web App]
    Prisma --> DB[(PostgreSQL)]
```
