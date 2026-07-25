# InternTrack

InternTrack is a Django web application for managing internship and job applications from one place. It helps users track opportunities, manage resumes and cover letters, review ATS fit against job descriptions, and stay on top of follow-ups through dashboard notifications.

## Features

- User registration, login, logout, password reset, and profile management
- Internship/job application tracking with status, company, role, location, salary, deadline, interview date, and notes
- Search, filtering, sorting, pagination, and recently viewed applications
- Personal dashboard with application counts and Chart.js-ready analytics data
- Resume, cover letter, and document upload management with file type and size validation
- Resume versioning for uploaded resumes
- ATS checker using semantic similarity, TF-IDF fallback scoring, keyword coverage, and improvement suggestions
- Follow-up reminder scheduling, snoozing, completion tracking, and notification history
- Optional email notifications through environment-based SMTP configuration
- Django admin statistics view for staff users

## Tech Stack

- Python
- Django 5.2
- SQLite for local development
- Django Templates
- Bootstrap-style server-rendered UI
- scikit-learn, NLTK, PyPDF2, python-docx
- sentence-transformers, transformers, and PyTorch for semantic resume matching

## Project Structure

```text
InternTrack/
|-- accounts/        # Authentication, registration, password reset, and user profiles
|-- applications/    # Job application CRUD, filters, sorting, and follow-up scheduling hooks
|-- dashboard/       # Dashboard analytics, notifications, and admin stats
|-- documents/       # Document uploads, resume versioning, and ATS analysis
|-- interntrack/     # Project settings, root URLs, WSGI/ASGI config
|-- static/          # Custom CSS and static assets
|-- templates/       # Shared and app-specific Django templates
|-- manage.py
|-- requirements.txt
`-- README.md
```

## Getting Started

### Prerequisites

- Python 3.11 or later recommended
- pip
- Git

### Installation

1. Clone the repository:

```bash
git clone https://github.com/<your-username>/InternTrack.git
cd InternTrack
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Windows:

```bash
.venv\Scripts\activate
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root:

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=webmaster@localhost
```

For local development, the console email backend is enough. Configure SMTP values only when you want real password-reset or notification emails.

5. Apply database migrations:

```bash
python manage.py migrate
```

6. Create an admin user:

```bash
python manage.py createsuperuser
```

7. Start the development server:

```bash
python manage.py runserver
```

Open the app at `http://127.0.0.1:8000/`.

## Main Routes

| Route | Description |
| --- | --- |
| `/` | Home page |
| `/accounts/register/` | Create a user account |
| `/accounts/login/` | Log in |
| `/accounts/profile/` | View profile |
| `/accounts/profile/edit/` | Edit profile |
| `/applications/` | View and manage applications |
| `/applications/add/` | Add an application |
| `/documents/` | View uploaded documents |
| `/documents/upload/` | Upload a resume, cover letter, or other document |
| `/documents/ats/` | Run ATS analysis |
| `/dashboard/` | Application dashboard |
| `/dashboard/notifications/` | Notification center |
| `/admin/` | Django admin |

## ATS Checker Notes

The ATS checker extracts text from PDF, DOC, and DOCX resumes, compares the resume against a pasted job description, and returns:

- Overall match score
- Semantic similarity score
- Skill coverage score
- Matched and missing technical keywords
- Resume improvement suggestions

The semantic model uses `sentence-transformers/all-MiniLM-L6-v2`. On first use, the model may need to be downloaded by the `sentence-transformers` package. If the semantic model cannot load, the app falls back to TF-IDF-based scoring.

## Development Commands

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
python manage.py test
```

## GitHub Notes

The repository is configured to ignore local-only files such as:

- `.env`
- `.venv/`
- `db.sqlite3`
- `media/`
- Python cache files
- IDE settings

Do not commit secrets, uploaded documents, local databases, or generated media files.

## Security Notes

This project currently uses development-friendly Django settings. Before deploying publicly:

- Move `SECRET_KEY` into an environment variable
- Set `DEBUG=False`
- Configure `ALLOWED_HOSTS`
- Use a production database
- Configure static and media file hosting
- Use secure email credentials through environment variables
- Review file upload storage and access controls

## License

No license has been added yet. Add a license before publishing if you want others to know how they may use or contribute to the project.
