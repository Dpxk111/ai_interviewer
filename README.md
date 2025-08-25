# AI Interview Screener

A Django-based backend system that conducts automated phone interviews using AI-generated questions, Twilio for voice calls, and OpenAI for scoring and recommendations.

## Features

- **JD → Questions**: Generate 5-7 relevant interview questions from job descriptions using OpenAI
- **Resume Upload**: Parse PDF/DOCX resumes and extract text for scoring context
- **Candidate Management**: Create candidates with E.164 formatted phone numbers
- **Real Phone Calls**: Place actual calls using Twilio with TTS questions and answer recording
- **AI Scoring**: Score individual answers and generate final recommendations
- **Security**: API key authentication and phone number whitelisting
- **Webhooks**: Handle Twilio callbacks for recordings and transcripts

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client API    │    │   Django Backend│    │   Twilio Voice  │
│                 │    │                 │    │                 │
│ • Job Descriptions│    │ • REST API      │    │ • TTS Questions │
│ • Candidates    │◄──►│ • OpenAI Integration│◄──►│ • Record Answers│
│ • Interviews    │    │ • File Processing│    │ • Webhooks      │
│ • Results       │    │ • Database       │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.8+
- Django 5.1+
- OpenAI API key
- Twilio account with voice capabilities
- Redis (optional, for Celery)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai_screener
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your actual credentials
   ```

4. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

## Environment Variables

Create a `.env` file with the following variables:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# API Key for authentication
API_KEY=your-api-key-here

# OpenAI Settings
OPENAI_API_KEY=your-openai-api-key-here

# Twilio Settings
TWILIO_ACCOUNT_SID=your-twilio-account-sid-here
TWILIO_AUTH_TOKEN=your-twilio-auth-token-here
TWILIO_PHONE_NUMBER=+1234567890

# Whitelisted phone numbers for testing (comma-separated)
WHITELISTED_NUMBERS=+1234567890,+1987654321

# Base URL for webhooks (update with your domain)
BASE_URL=https://your-domain.com

# Redis URL (for Celery)
REDIS_URL=redis://localhost:6379/0
```

## API Documentation

### Authentication

All API requests require an `X-API-Key` header:
```
X-API-Key: your-api-key-here
```

### Endpoints

#### 1. Create Job Description
```http
POST /api/job-descriptions/create/
Content-Type: application/json
X-API-Key: your-api-key

{
    "title": "Senior Python Developer",
    "description": "We are looking for a senior Python developer..."
}
```

#### 2. Create Candidate
```http
POST /api/candidates/create/
Content-Type: multipart/form-data
X-API-Key: your-api-key

{
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "resume": [file]
}
```

#### 3. Create Interview
```http
POST /api/interviews/create/
Content-Type: application/json
X-API-Key: your-api-key

{
    "job_description": "uuid-of-job-description",
    "candidate": "uuid-of-candidate"
}
```

#### 4. Trigger Interview Call
```http
POST /api/interviews/{interview_id}/trigger/
X-API-Key: your-api-key
```

#### 5. Get Interview Results
```http
GET /api/interviews/{interview_id}/results/
X-API-Key: your-api-key
```

### Response Format

#### Interview Results
```json
{
    "id": "uuid",
    "status": "completed",
    "final_score": 8.5,
    "recommendation": "Strong candidate with relevant experience...",
    "questions": [
        {
            "question_number": 1,
            "question_text": "Tell me about your experience...",
            "answer": {
                "transcript": "I have 5 years of experience...",
                "score": 9.0,
                "feedback": "Excellent answer with specific examples",
                "audio_url": "https://domain.com/media/answer_1.wav"
            }
        }
    ],
    "created_at": "2024-01-01T12:00:00Z"
}
```

## Deployment on PythonAnywhere

### 1. Upload Code
- Upload your code to PythonAnywhere
- Or clone from your Git repository

### 2. Set Up Virtual Environment
```bash
mkvirtualenv --python=/usr/bin/python3.9 ai_screener
pip install -r requirements.txt
```

### 3. Configure Environment
- Create `.env` file in your project directory
- Add all required environment variables

### 4. Database Setup
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic
```

### 5. Configure WSGI
Edit your WSGI file to point to your Django project:
```python
import os
import sys
path = '/home/yourusername/ai_screener'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'ai_screener.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 6. Set Up Web App
- Create a new web app on PythonAnywhere
- Set the source code to your project directory
- Configure the WSGI file path

### 7. Configure Twilio Webhooks
Update your Twilio webhook URLs to point to your PythonAnywhere domain:
- TwiML URL: `https://yourusername.pythonanywhere.com/api/webhook/interview/{interview_id}/twiml/`
- Status Callback: `https://yourusername.pythonanywhere.com/api/webhook/interview/{interview_id}/status/`

## Testing Workflow

1. **Create a job description** with title and description
2. **Add a candidate** with name, email, phone, and optional resume
3. **Create an interview** linking the job description and candidate
4. **Trigger the interview** to initiate the phone call
5. **Receive the call** and answer the AI-generated questions
6. **Get results** with scores, transcripts, and recommendations

## Security Features

- **API Key Authentication**: All endpoints require valid API key
- **Phone Number Whitelisting**: Only whitelisted numbers can receive calls
- **Input Validation**: Phone numbers validated and formatted to E.164
- **File Upload Security**: Secure file handling for resumes and audio

## File Structure

```
ai_screener/
├── ai_screener/          # Django project settings
├── interviews/           # Main app
│   ├── models.py        # Database models
│   ├── views.py         # API views
│   ├── serializers.py   # DRF serializers
│   ├── utils.py         # Utility functions
│   ├── urls.py          # URL patterns
│   └── admin.py         # Admin interface
├── media/               # Uploaded files
├── requirements.txt     # Python dependencies
├── manage.py           # Django management
└── README.md           # This file
```

## Troubleshooting

### Common Issues

1. **Twilio Call Fails**
   - Check Twilio credentials in `.env`
   - Verify phone number is whitelisted
   - Ensure webhook URLs are accessible

2. **OpenAI API Errors**
   - Verify OpenAI API key
   - Check API usage limits
   - Ensure proper JSON formatting in prompts

3. **File Upload Issues**
   - Check media directory permissions
   - Verify file size limits
   - Ensure supported file formats (PDF, DOCX)

### Logs
Check Django logs for detailed error information:
```bash
python manage.py runserver --verbosity=2
```

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review Django and Twilio documentation
3. Check API response codes and error messages

## License

This project is licensed under the MIT License.
