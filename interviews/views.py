from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import json
import requests
from .models import JobDescription, Candidate, Interview, Question, Answer
from .serializers import (
    JobDescriptionSerializer, CandidateSerializer, InterviewSerializer,
    InterviewCreateSerializer, InterviewResultSerializer
)
from .utils import (
    generate_questions_from_jd, parse_resume, score_answer, generate_final_recommendation,
    validate_phone_number, is_whitelisted_number, create_twilio_call,
    generate_interview_twiml
)
from twilio.twiml.voice_response import VoiceResponse

def validate_api_key(request):
    """Validate API key from request headers"""
    api_key = request.headers.get('X-API-Key')
    print(api_key, "=========", settings.API_KEY)
    if not api_key or api_key != settings.API_KEY:
        return False
    return True

@api_view(['POST'])
@permission_classes([AllowAny])
def create_job_description(request):
    """Create a job description and generate questions"""
    if not validate_api_key(request):
        return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        title = request.data.get('title')
        description = request.data.get('description')
        
        if not title or not description:
            return Response(
                {'error': 'Title and description are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate questions using OpenAI
        questions = generate_questions_from_jd(description)
        
        # Create job description
        job_description = JobDescription.objects.create(
            title=title,
            description=description,
            questions=questions
        )
        
        serializer = JobDescriptionSerializer(job_description)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Error creating job description: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def create_candidate(request):
    """Create a candidate with resume upload"""
    if not validate_api_key(request):
        return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        name = request.data.get('name')
        email = request.data.get('email')
        phone = request.data.get('phone')
        resume = request.FILES.get('resume')
        
        if not name or not email or not phone:
            return Response(
                {'error': 'Name, email, and phone are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate and format phone number
        formatted_phone = validate_phone_number(phone)
        if not formatted_phone:
            return Response(
                {'error': 'Invalid phone number format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse resume if provided
        resume_text = ""
        if resume:
            resume_text = parse_resume(resume)
        
        # Create candidate
        candidate = Candidate.objects.create(
            name=name,
            email=email,
            phone=formatted_phone,
            resume=resume,
            resume_text=resume_text
        )
        
        serializer = CandidateSerializer(candidate)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Error creating candidate: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def create_interview(request):
    """Create an interview session"""
    if not validate_api_key(request):
        return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        serializer = InterviewCreateSerializer(data=request.data)
        if serializer.is_valid():
            interview = serializer.save()
            
            # Create Question objects from job description
            job_description = interview.job_description
            for i, question_text in enumerate(job_description.questions, 1):
                Question.objects.create(
                    interview=interview,
                    question_text=question_text,
                    question_number=i
                )
            
            serializer = InterviewSerializer(interview)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response(
            {'error': f'Error creating interview: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def trigger_interview(request, interview_id):
    """Trigger the interview call"""
    if not validate_api_key(request):
        return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        print(f"Triggering interview: {interview_id}")
        interview = get_object_or_404(Interview, id=interview_id)
        print(f"Interview found: {interview.id}")
        print(f"Candidate phone: {interview.candidate.phone}")
        
        # Check if phone number is whitelisted
        is_whitelisted = is_whitelisted_number(interview.candidate.phone)
        print(f"Phone whitelisted: {is_whitelisted}")
        
        if not is_whitelisted:
            return Response(
                {'error': 'Phone number not whitelisted for testing'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if questions exist
        questions = interview.questions.all()
        print(f"Questions found: {questions.count()}")
        
        if not questions.exists():
            return Response(
                {'error': 'No questions found for this interview'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create Twilio call
        print("Creating Twilio call...")
        call_sid = create_twilio_call(interview)
        print(f"Call SID: {call_sid}")
        
        if not call_sid:
            return Response(
                {'error': 'Failed to create call'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Update interview status
        interview.status = 'in_progress'
        interview.twilio_call_sid = call_sid
        interview.save()
        
        return Response({
            'message': 'Interview call initiated',
            'call_sid': call_sid,
            'status': interview.status
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error triggering interview: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(
            {'error': f'Error triggering interview: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def get_interview_results(request, interview_id):
    """Get interview results with scores and recommendations"""
    if not validate_api_key(request):
        return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        interview = get_object_or_404(Interview, id=interview_id)
        
        # If interview is completed, generate final recommendation
        if interview.status == 'completed' and not interview.recommendation:
            recommendation = generate_final_recommendation(interview)
            interview.recommendation = recommendation
            interview.save()
        
        serializer = InterviewResultSerializer(interview, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Error getting results: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# Webhook views for Twilio
@csrf_exempt
@require_http_methods(["POST"])
def twilio_webhook_twiml(request, interview_id):
    """Generate TwiML for the interview call"""
    try:
        print(f"TwiML webhook called for interview: {interview_id}")
        
        # Check if interview exists
        try:
            interview = get_object_or_404(Interview, id=interview_id)
            print(f"Interview found: {interview.id}")
        except Exception as e:
            print(f"Interview not found: {e}")
            error_response = VoiceResponse()
            error_response.say("Interview not found. Please check the interview ID.", voice='alice')
            return HttpResponse(str(error_response), content_type='text/xml; charset=utf-8')
        
        # Check if questions exist
        questions = interview.questions.all()
        if not questions.exists():
            print("No questions found for interview")
            error_response = VoiceResponse()
            error_response.say("No questions found for this interview. Please contact support.", voice='alice')
            return HttpResponse(str(error_response), content_type='text/xml; charset=utf-8')
        
        print(f"Generating TwiML for {questions.count()} questions")
        twiml = generate_interview_twiml(interview)
        
        print("TwiML generated successfully")
        print(f"TwiML length: {len(twiml)} characters")
        
        # Ensure proper XML header and content type
        if not twiml.startswith('<?xml'):
            twiml = '<?xml version="1.0" encoding="UTF-8"?>\n' + twiml
        
        return HttpResponse(twiml, content_type='text/xml; charset=utf-8')
        
    except Exception as e:
        print(f"Error in TwiML webhook: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return a simple error TwiML
        error_response = VoiceResponse()
        error_response.say("We are sorry, an application error has occurred. Please try again later.", voice='alice')
        return HttpResponse(str(error_response), content_type='text/xml; charset=utf-8')

@csrf_exempt
@require_http_methods(["POST"])
def twilio_webhook_answer(request, interview_id, question_id):
    """Handle recorded answer from Twilio"""
    try:
        print(f"Answer webhook called for interview: {interview_id}, question: {question_id}")
        
        interview = get_object_or_404(Interview, id=interview_id)
        question = get_object_or_404(Question, id=question_id, interview=interview)
        
        # Get recording URL from Twilio
        recording_url = request.POST.get('RecordingUrl')
        recording_duration = request.POST.get('RecordingDuration')
        
        print(f"Recording URL: {recording_url}")
        print(f"Recording Duration: {recording_duration}")
        
        # Download and save the recording
        if recording_url:
            try:
                response = requests.get(recording_url)
                if response.status_code == 200:
                    # Save audio file
                    from django.core.files.base import ContentFile
                    audio_file = ContentFile(response.content, name=f"answer_{question_id}.wav")
                    
                    # Create or update answer
                    answer, created = Answer.objects.get_or_create(question=question)
                    answer.audio_file = audio_file
                    
                    # Save recording duration if available
                    if recording_duration:
                        try:
                            answer.audio_duration = int(recording_duration)
                        except (ValueError, TypeError):
                            pass
                    
                    answer.save()
                    print(f"Audio file saved for question {question_id}, duration: {recording_duration}")
                else:
                    print(f"Failed to download recording: {response.status_code}")
            except Exception as e:
                print(f"Error downloading recording: {e}")
        
        # Find the next question
        current_question_number = question.question_number
        next_question = interview.questions.filter(question_number__gt=current_question_number).order_by('question_number').first()
        
        response = VoiceResponse()
        
        if next_question:
            # There are more questions
            print(f"Moving to next question: {next_question.id}")
            response.say("Thank you for your answer. Moving to the next question.", voice='alice')
            response.pause(length=1)
            
            # Ask the next question
            question_text = f"Question {next_question.question_number}: {next_question.question_text}"
            response.say(question_text, voice='alice')
            response.pause(length=1)
            
            # Record the next answer
            response.record(
                action=f"/api/webhook/interview/{interview.id}/answer/{next_question.id}/",
                maxLength=120,  # 2 minutes max
                playBeep=True,
                trim='trim-silence'
            )
        else:
            # No more questions, end the interview
            print("No more questions, ending interview")
            response.say("Thank you for completing all the questions. We'll review your responses and get back to you soon. Goodbye!", voice='alice')
        
        twiml = str(response)
        if not twiml.startswith('<?xml'):
            twiml = '<?xml version="1.0" encoding="UTF-8"?>\n' + twiml
        
        return HttpResponse(twiml, content_type='text/xml; charset=utf-8')
        
    except Exception as e:
        print(f"Error in answer webhook: {str(e)}")
        import traceback
        traceback.print_exc()
        
        error_response = VoiceResponse()
        error_response.say("We are sorry, an error occurred while processing your answer. Please try again later.", voice='alice')
        return HttpResponse(str(error_response), content_type='text/xml; charset=utf-8')

@csrf_exempt
@require_http_methods(["POST"])
def twilio_webhook_status(request, interview_id):
    """Handle call status updates from Twilio"""
    try:
        interview = get_object_or_404(Interview, id=interview_id)
        call_status = request.POST.get('CallStatus')
        
        if call_status == 'completed':
            # Process all answers and generate scores
            for question in interview.questions.all():
                answer = question.answers.first()
                if answer and answer.transcript and not answer.score:
                    # Score the answer
                    score, feedback = score_answer(
                        question.question_text, 
                        answer.transcript, 
                        interview.candidate.resume_text
                    )
                    answer.score = score
                    answer.feedback = feedback
                    answer.save()
            
            # Update interview status
            interview.status = 'completed'
            interview.save()
        
        return HttpResponse('OK', content_type='text/plain')
        
    except Exception as e:
        return HttpResponse('Error', content_type='text/plain')

# Additional utility endpoints
@api_view(['GET'])
@permission_classes([AllowAny])
def list_job_descriptions(request):
    """List all job descriptions"""
    if not validate_api_key(request):
        return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)
    
    job_descriptions = JobDescription.objects.all().order_by('-created_at')
    serializer = JobDescriptionSerializer(job_descriptions, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def list_candidates(request):
    """List all candidates"""
    if not validate_api_key(request):
        return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)
    
    candidates = Candidate.objects.all().order_by('-created_at')
    serializer = CandidateSerializer(candidates, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def list_interviews(request):
    """List all interviews"""
    if not validate_api_key(request):
        return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)
    
    interviews = Interview.objects.all().order_by('-created_at')
    serializer = InterviewSerializer(interviews, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def test_twiml(request):
    """Test TwiML generation"""
    try:
        response = VoiceResponse()
        response.say("Hello, this is a test call. If you can hear this, TwiML generation is working correctly.", voice='alice')
        twiml = str(response)
        
        # Ensure proper XML header
        if not twiml.startswith('<?xml'):
            twiml = '<?xml version="1.0" encoding="UTF-8"?>\n' + twiml
        
        return HttpResponse(twiml, content_type='text/xml; charset=utf-8')
    except Exception as e:
        error_response = VoiceResponse()
        error_response.say(f"Error: {str(e)}", voice='alice')
        return HttpResponse(str(error_response), content_type='text/xml; charset=utf-8')
