import os
import openai
from django.conf import settings
import PyPDF2
from docx import Document
import io
import re
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import requests
import json

# Initialize OpenAI client
openai.api_key = settings.OPENAI_API_KEY

# Initialize Twilio client
twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

def generate_questions_from_jd(job_description):
    """Generate interview questions from job description using OpenAI"""
    try:
        prompt = f"""
        Based on the following job description, generate 5-7 relevant interview questions.
        Focus on technical skills, experience, and behavioral questions.
        
        Job Description:
        {job_description}
        
        Return only a JSON array of questions, no additional text.
        Example format: ["Question 1", "Question 2", "Question 3"]
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert HR professional who creates relevant interview questions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        questions_text = response.choices[0].message.content.strip()
        # Extract JSON array from response
        questions = json.loads(questions_text)
        return questions[:7]  # Ensure max 7 questions
        
    except Exception as e:
        print(f"Error generating questions: {e}")
        # Fallback questions
        return [
            "Tell me about your relevant experience for this role.",
            "What are your key strengths that would benefit this position?",
            "Describe a challenging project you worked on.",
            "How do you handle tight deadlines and pressure?",
            "What are your career goals for the next few years?"
        ]

def parse_resume(file):
    """Parse resume file (PDF or DOCX) and extract text"""
    try:
        if file.name.lower().endswith('.pdf'):
            # Parse PDF
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text.strip()
        
        elif file.name.lower().endswith('.docx'):
            # Parse DOCX
            doc = Document(file)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        
        else:
            return ""
            
    except Exception as e:
        print(f"Error parsing resume: {e}")
        return ""

def score_answer(question, answer_transcript, resume_text=""):
    """Score a candidate's answer using OpenAI"""
    try:
        prompt = f"""
        Score the following answer to an interview question on a scale of 1-10.
        
        Question: {question}
        Answer: {answer_transcript}
        Resume Context: {resume_text[:500]}  # First 500 chars for context
        
        Provide:
        1. A score from 1-10
        2. Brief feedback (1-2 sentences)
        
        Return as JSON: {{"score": 8, "feedback": "Good answer with relevant examples"}}
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert interviewer evaluating candidate responses."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.3
        )
        
        result_text = response.choices[0].message.content.strip()
        result = json.loads(result_text)
        return result.get('score', 5), result.get('feedback', 'No feedback available')
        
    except Exception as e:
        print(f"Error scoring answer: {e}")
        return 5, "Unable to score answer"

def generate_final_recommendation(interview):
    """Generate final recommendation based on all answers"""
    try:
        questions_answers = []
        total_score = 0
        answer_count = 0
        
        for question in interview.questions.all():
            answer = question.answers.first()
            if answer:
                questions_answers.append({
                    'question': question.question_text,
                    'answer': answer.transcript,
                    'score': answer.score
                })
                total_score += answer.score or 0
                answer_count += 1
        
        if answer_count == 0:
            return "No answers provided for evaluation."
        
        avg_score = total_score / answer_count
        
        prompt = f"""
        Based on the interview responses, provide a final recommendation.
        
        Average Score: {avg_score}/10
        Total Questions Answered: {answer_count}
        
        Questions and Answers:
        {json.dumps(questions_answers, indent=2)}
        
        Provide a brief recommendation (2-3 sentences) on whether to proceed with the candidate.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an HR professional providing interview recommendations."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error generating recommendation: {e}")
        return "Unable to generate recommendation"

def validate_phone_number(phone):
    """Validate and format phone number to E.164"""
    try:
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        
        # Handle different formats
        if len(digits) == 10:
            # 10-digit number - add country code (assuming India)
            digits = '91' + digits
        elif len(digits) == 12 and digits.startswith('91'):
            # 12-digit number starting with 91 (India)
            pass
        elif len(digits) == 11 and digits.startswith('1'):
            # 11-digit number starting with 1 (US)
            pass
        elif len(digits) == 12 and digits.startswith('1'):
            # 12-digit number starting with 1 (US)
            pass
        elif phone.startswith('+'):
            # Already in E.164 format
            return phone
        else:
            print(f"Invalid phone number format: {phone}")
            return None
        
        return f"+{digits}"
    except Exception as e:
        print(f"Error validating phone number {phone}: {e}")
        return None

def is_whitelisted_number(phone):
    """Check if phone number is whitelisted for testing"""
    print(phone, "=========", settings.WHITELISTED_NUMBERS)
    # Allow all numbers if "*" is in the whitelist
    if "*" in settings.WHITELISTED_NUMBERS:
        return True
    return phone in settings.WHITELISTED_NUMBERS

def create_twilio_call(interview):
    """Create a Twilio call for the interview"""
    try:
        print(f"Creating Twilio call for interview {interview.id}")
        print(f"BASE_URL: {settings.BASE_URL}")
        print(f"TWILIO_PHONE_NUMBER: {settings.TWILIO_PHONE_NUMBER}")
        print(f"Candidate phone: {interview.candidate.phone}")
        
        # Generate TwiML for the interview
        twiml_url = f"{settings.BASE_URL}/api/webhook/interview/{interview.id}/twiml/"
        status_callback_url = f"{settings.BASE_URL}/api/webhook/interview/{interview.id}/status/"
        
        print(f"TwiML URL: {twiml_url}")
        print(f"Status callback URL: {status_callback_url}")
        
        call = twilio_client.calls.create(
            url=twiml_url,
            to=interview.candidate.phone,
            from_=settings.TWILIO_PHONE_NUMBER,
            record=True,
            status_callback=status_callback_url,
            status_callback_event=['completed']
        )
        
        print(f"Twilio call created successfully: {call.sid}")
        return call.sid
        
    except Exception as e:
        print(f"Error creating Twilio call: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_interview_twiml(interview):
    """Generate TwiML for the interview call"""
    try:
        print(f"Generating TwiML for interview {interview.id}")
        
        response = VoiceResponse()
        
        # Welcome message
        welcome_text = f"Hello {interview.candidate.name}, welcome to your AI interview. I'll be asking you several questions. Please answer each question clearly. Let's begin."
        print(f"Welcome message: {welcome_text}")
        response.say(welcome_text, voice='alice')
        
        # Get questions
        questions = interview.questions.all().order_by('question_number')
        print(f"Found {questions.count()} questions")
        
        if not questions.exists():
            response.say("No questions found for this interview. Please contact support.", voice='alice')
            return str(response)
        
        # Only add the first question to the initial TwiML
        # Subsequent questions will be handled by the answer webhook
        first_question = questions.first()
        print(f"Adding first question: {first_question.question_text[:50]}...")
        
        question_text = f"Question 1: {first_question.question_text}"
        response.say(question_text, voice='alice')
        response.pause(length=1)
        
        # Record answer for first question
        record_action = f"/api/webhook/interview/{interview.id}/answer/{first_question.id}/"
        print(f"Record action: {record_action}")
        
        response.record(
            action=record_action,
            maxLength=120,  # 2 minutes max
            playBeep=True,
            trim='trim-silence'
        )
        
        twiml_string = str(response)
        print(f"TwiML generated successfully, length: {len(twiml_string)}")
        
        return twiml_string
        
    except Exception as e:
        print(f"Error generating TwiML: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return a simple error TwiML
        error_response = VoiceResponse()
        error_response.say("We are sorry, an error occurred while generating the interview. Please try again later.", voice='alice')
        return str(error_response)
