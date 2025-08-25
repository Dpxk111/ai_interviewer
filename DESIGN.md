# AI Interview Screener - Design Document

## Overview

The AI Interview Screener is a Django-based backend system that automates the interview process using AI-generated questions, Twilio for voice calls, and OpenAI for scoring and recommendations. The system provides a complete workflow from job description to interview results.

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client API    │    │   Django Backend│    │   Twilio Voice  │
│                 │    │                 │    │                 │
│ • Job Descriptions│    │ • REST API      │    │ • TTS Questions │
│ • Candidates    │◄──►│ • OpenAI Integration│◄──►│ • Record Answers│
│ • Interviews    │    │ • File Processing│    │ • Webhooks      │
│ • Results       │    │ • Database       │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   OpenAI API    │
                       │                 │
                       │ • Question Gen  │
                       │ • Answer Scoring│
                       │ • Recommendations│
                       └─────────────────┘
```

### Technology Stack

- **Backend Framework**: Django 5.1 with Django REST Framework
- **Database**: SQLite (can be upgraded to PostgreSQL for production)
- **AI Integration**: OpenAI GPT-3.5-turbo for question generation and scoring
- **Voice Communication**: Twilio for phone calls, TTS, and recording
- **File Processing**: PyPDF2 and python-docx for resume parsing
- **Authentication**: API key-based authentication
- **Deployment**: PythonAnywhere compatible

## Data Design

### Core Entities

1. **JobDescription**
   - Stores job title, description, and AI-generated questions
   - Questions are stored as JSON array for flexibility

2. **Candidate**
   - Stores candidate information (name, email, phone)
   - Handles resume upload and text extraction
   - Phone numbers validated and formatted to E.164

3. **Interview**
   - Links job description and candidate
   - Tracks interview status and Twilio call information
   - Stores final scores and recommendations

4. **Question**
   - Individual questions for each interview
   - Ordered by question number
   - Links to answers

5. **Answer**
   - Stores recorded audio files and transcripts
   - Contains AI-generated scores and feedback
   - Links to questions

### Database Schema

```
JobDescription (1) ──── (1) Interview (1) ──── (1) Candidate
       │                        │
       │                        │
       │                        ▼
       │                ┌──────────────┐
       │                │   Question   │
       │                │              │
       │                └──────────────┘
       │                        │
       │                        ▼
       │                ┌──────────────┐
       │                │    Answer    │
       │                │              │
       │                └──────────────┘
       │
       └─── questions (JSON array)
```

## AI Usage Points

### 1. Question Generation
- **Input**: Job description text
- **Model**: GPT-3.5-turbo
- **Prompt**: Structured prompt requesting 5-7 relevant interview questions
- **Output**: JSON array of questions
- **Fallback**: Pre-defined generic questions if AI fails

### 2. Answer Scoring
- **Input**: Question text, candidate answer transcript, resume context
- **Model**: GPT-3.5-turbo
- **Prompt**: Scoring rubric with 1-10 scale and feedback requirements
- **Output**: JSON with score and feedback
- **Context**: Uses resume text for additional context

### 3. Final Recommendation
- **Input**: All questions, answers, scores, and average score
- **Model**: GPT-3.5-turbo
- **Prompt**: HR professional recommendation format
- **Output**: 2-3 sentence recommendation
- **Purpose**: Overall candidate evaluation

## System Flow

### 1. Job Description Creation
```
Client → POST /api/job-descriptions/create/
         ↓
    Extract title & description
         ↓
    OpenAI: Generate questions
         ↓
    Store in database
         ↓
    Return job description with questions
```

### 2. Candidate Registration
```
Client → POST /api/candidates/create/
         ↓
    Validate phone number (E.164)
         ↓
    Parse resume (PDF/DOCX)
         ↓
    Extract text content
         ↓
    Store candidate data
         ↓
    Return candidate info
```

### 3. Interview Creation
```
Client → POST /api/interviews/create/
         ↓
    Link job description & candidate
         ↓
    Create Question objects
         ↓
    Initialize interview session
         ↓
    Return interview details
```

### 4. Interview Execution
```
Client → POST /api/interviews/{id}/trigger/
         ↓
    Validate phone whitelist
         ↓
    Create Twilio call
         ↓
    Generate TwiML for questions
         ↓
    Initiate phone call
         ↓
    Return call status
```

### 5. Call Flow (Twilio)
```
Twilio → GET /api/webhook/interview/{id}/twiml/
         ↓
    Generate TwiML with questions
         ↓
    For each question:
         ├── TTS: Read question
         ├── Record: Capture answer
         └── POST: /api/webhook/interview/{id}/answer/{qid}/
         ↓
    Store audio recordings
         ↓
    POST: /api/webhook/interview/{id}/status/
         ↓
    Process recordings & score answers
         ↓
    Generate final recommendation
```

### 6. Results Retrieval
```
Client → GET /api/interviews/{id}/results/
         ↓
    Check interview completion
         ↓
    Generate recommendation (if needed)
         ↓
    Return structured results:
         ├── Questions & answers
         ├── Individual scores
         ├── Audio file URLs
         ├── Final score
         └── Recommendation
```

## Security Features

### 1. API Authentication
- API key required for all endpoints
- Header-based authentication: `X-API-Key`
- Configurable key in environment variables

### 2. Phone Number Whitelisting
- Only whitelisted numbers can receive calls
- Prevents unauthorized call charges
- Configurable list in environment variables

### 3. Input Validation
- Phone number format validation (E.164)
- File type validation for resumes
- Content length limits

### 4. File Security
- Secure file upload handling
- Unique file naming with UUIDs
- Media directory isolation

## Scalability Considerations

### 1. Database
- SQLite for development, PostgreSQL for production
- Indexed foreign keys for performance
- JSON fields for flexible question storage

### 2. File Storage
- Local storage for development
- Cloud storage (AWS S3) for production
- Audio file cleanup policies

### 3. API Performance
- Django REST Framework optimizations
- Database query optimization
- Caching for frequently accessed data

### 4. Twilio Integration
- Webhook reliability with retry logic
- Call status monitoring
- Error handling for failed calls

## Error Handling

### 1. AI Service Failures
- Fallback to generic questions
- Graceful degradation of scoring
- Error logging and monitoring

### 2. Twilio Failures
- Call status monitoring
- Webhook error handling
- Retry mechanisms for failed operations

### 3. File Processing
- Multiple format support (PDF, DOCX)
- Error handling for corrupted files
- Graceful fallbacks

## Monitoring and Logging

### 1. Application Logs
- Django logging configuration
- Error tracking and alerting
- Performance monitoring

### 2. Call Analytics
- Call success/failure rates
- Duration tracking
- Quality metrics

### 3. AI Performance
- Question generation success rates
- Scoring accuracy monitoring
- API usage tracking

## Future Enhancements

### 1. Advanced Features
- Multi-language support
- Custom question templates
- Advanced analytics dashboard
- Integration with ATS systems

### 2. AI Improvements
- Fine-tuned models for specific industries
- Sentiment analysis of answers
- Personality assessment
- Cultural fit evaluation

### 3. Platform Extensions
- Mobile app integration
- Video interview support
- Real-time collaboration features
- Advanced scheduling system
