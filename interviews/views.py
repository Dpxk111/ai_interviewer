from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
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
    generate_interview_twiml, generate_transcript_from_audio
)
from twilio.twiml.voice_response import VoiceResponse

def validate_api_key(request):
    """Validate API key from request headers"""
    api_key = request.headers.get('X-API-Key')
    if not api_key or api_key != settings.API_KEY:
        return False
    return True

class JobDescriptionCreateView(APIView):
    """Create a job description and generate questions"""
    permission_classes = [AllowAny]
    
    def post(self, request):
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

class JobDescriptionListView(APIView):
    """List all job descriptions"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        if not validate_api_key(request):
            return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)
        
        job_descriptions = JobDescription.objects.all().order_by('-created_at')
        serializer = JobDescriptionSerializer(job_descriptions, many=True)
        return Response(serializer.data)

class CandidateCreateView(APIView):
    """Create a candidate with resume upload"""
    permission_classes = [AllowAny]
    
    def post(self, request):
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

class CandidateListView(APIView):
    """List all candidates"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        if not validate_api_key(request):
            return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)
        
        candidates = Candidate.objects.all().order_by('-created_at')
        serializer = CandidateSerializer(candidates, many=True)
        return Response(serializer.data)

class InterviewCreateView(APIView):
    """Create an interview session"""
    permission_classes = [AllowAny]
    
    def post(self, request):
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

class InterviewListView(APIView):
    """List all interviews"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        if not validate_api_key(request):
            return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)
        
        interviews = Interview.objects.all().order_by('-created_at')
        serializer = InterviewSerializer(interviews, many=True, context={'request': request})
        return Response(serializer.data)

class InterviewTriggerView(APIView):
    """Trigger the interview call"""
    permission_classes = [AllowAny]
    
    def post(self, request, interview_id):
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

class InterviewResultsView(APIView):
    """Get interview results with scores and recommendations"""
    permission_classes = [AllowAny]
    
    def get(self, request, interview_id):
        if not validate_api_key(request):
            return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            interview = get_object_or_404(Interview, id=interview_id)
            
            # Track evaluation progress
            evaluation_results = {
                'transcripts_generated': 0,
                'answers_scored': 0,
                'evaluation_completed': False,
                'errors': []
            }
            
            print(f"Step 1: Generating transcripts for interview {interview_id}")
            for question in interview.questions.all():
                answer = question.answers.first()
                if answer and answer.audio_file:
                    if not answer.transcript:
                        try:
                            print(f"Generating transcript for question {question.question_number}")
                            transcript = generate_transcript_from_audio(answer)
                            if transcript:
                                evaluation_results['transcripts_generated'] += 1
                                print(f"✓ Transcript generated for question {question.question_number}")
                            else:
                                evaluation_results['errors'].append(f"Failed to generate transcript for question {question.question_number}")
                        except Exception as e:
                            error_msg = f"Error generating transcript for question {question.question_number}: {str(e)}"
                            evaluation_results['errors'].append(error_msg)
                            print(f"✗ {error_msg}")
                    else:
                        print(f"✓ Transcript already exists for question {question.question_number}")
            
            print(f"Step 2: Scoring answers for interview {interview_id}")
            for question in interview.questions.all():
                answer = question.answers.first()
                # if answer and answer.transcript and (answer.score is None or not answer.feedback):
                try:
                    print(f"Scoring answer for question {question.question_number}")
                    score, feedback = score_answer(
                        question.question_text,
                        answer.transcript,
                        interview.candidate.resume_text
                    )
                    
                    answer.score = score
                    answer.feedback = feedback
                    answer.save()
                    
                    evaluation_results['answers_scored'] += 1
                    print(f"✓ Answer scored for question {question.question_number}: {score}/10")
                except Exception as e:
                    error_msg = f"Error scoring answer for question {question.question_number}: {str(e)}"
                    evaluation_results['errors'].append(error_msg)
                    print(f"✗ {error_msg}")
            
            print(f"Step 3: Generating final recommendation for interview {interview_id}")
            if interview.status == 'completed':
                try:
                    recommendation = generate_final_recommendation(interview)
                    interview.recommendation = recommendation
                    interview.save()
                    evaluation_results['evaluation_completed'] = True
                    print(f"✓ Final recommendation generated")
                except Exception as e:
                    error_msg = f"Error generating final recommendation: {str(e)}"
                    evaluation_results['errors'].append(error_msg)
                    print(f"✗ {error_msg}")
            
            total_questions = interview.questions.count()
            answered_questions = 0
            scored_questions = 0
            
            for question in interview.questions.all():
                answer = question.answers.first()
                if answer and answer.transcript:
                    answered_questions += 1
                if answer and answer.score is not None:
                    scored_questions += 1
            
                evaluation_results['evaluation_completed'] = True
            else:
                print(f"⚠ Evaluation incomplete: {scored_questions}/{answered_questions}/{total_questions} questions scored/answered/total")
            
            # Step 5: Serialize and return results
            serializer = InterviewResultSerializer(interview, context={'request': request})
            response_data = serializer.data
            
            # Add evaluation metadata to response
            response_data['evaluation_metadata'] = {
                'total_questions': total_questions,
                'answered_questions': answered_questions,
                'scored_questions': scored_questions,
                'transcripts_generated': evaluation_results['transcripts_generated'],
                'answers_scored': evaluation_results['answers_scored'],
                'evaluation_completed': evaluation_results['evaluation_completed'],
                'errors': evaluation_results['errors'] if evaluation_results['errors'] else None
            }
            
            print(f"Interview results ready: {scored_questions}/{total_questions} questions evaluated")
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            error_msg = f"Error getting results: {str(e)}"
            print(f"✗ {error_msg}")
            return Response(
                {'error': error_msg}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class TwilioWebhookTwiMLView(View):
    """Generate TwiML for the interview call"""
    
    def post(self, request, interview_id):
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

@method_decorator(csrf_exempt, name='dispatch')
class TwilioWebhookAnswerView(View):
    """Handle recorded answer from Twilio"""
    
    def post(self, request, interview_id, question_id):
        try:
            print(f"Answer webhook called for interview: {interview_id}, question: {question_id}")
            
            interview = get_object_or_404(Interview, id=interview_id)
            question = get_object_or_404(Question, id=question_id, interview=interview)
            
            # Get recording URL from Twilio
            recording_url = request.POST.get('RecordingUrl')
            recording_duration = request.POST.get('RecordingDuration')
            
            print(f"Recording URL: {recording_url}")
            print(f"Recording Duration: {recording_duration}")
            
            if recording_url:
                try:
                    response = requests.get(
                        recording_url,
                        auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                    )
                    if response.status_code == 200:
                        # Save audio file
                        from django.core.files.base import ContentFile
                        
                        # Check content type and set appropriate extension
                        content_type = response.headers.get('content-type', '')
                        if 'audio/wav' in content_type or 'audio/x-wav' in content_type:
                            file_extension = 'wav'
                        elif 'audio/mp3' in content_type:
                            file_extension = 'mp3'
                        elif 'audio/mpeg' in content_type:
                            file_extension = 'mp3'
                        else:
                            # Default to wav, but log the content type
                            file_extension = 'mp3'
                            print(f"Unknown content type: {content_type}, defaulting to .wav")
                        
                        audio_file = ContentFile(response.content, name=f"answer_{question_id}.{file_extension}")
                        print(f"Audio file created: {audio_file.name}, size: {len(response.content)} bytes, content-type: {content_type}")
                        
                        # Create or update answer
                        answer, created = Answer.objects.get_or_create(question=question)
                        answer.audio_file = audio_file
                        
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

@method_decorator(csrf_exempt, name='dispatch')
class TwilioWebhookStatusView(View):
    """Handle call status updates from Twilio"""
    
    def post(self, request, interview_id):
        try:
            interview = get_object_or_404(Interview, id=interview_id)
            call_status = request.POST.get('CallStatus')
            
            if call_status == 'completed':
                for question in interview.questions.all():
                    answer = question.answers.first()
                    if answer and answer.transcript and not answer.score:
                        
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
class TestTwiMLView(APIView):
    """Test TwiML generation"""
    permission_classes = [AllowAny]
    
    def get(self, request):
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

class AudioFilesListView(APIView):
    """List all audio files with their URLs"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        if not validate_api_key(request):
            return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            # Get all answers that have audio files
            answers = Answer.objects.filter(audio_file__isnull=False).exclude(audio_file='')
            
            audio_files = []
            for answer in answers:
                audio_url = None
                if answer.audio_file:
                    audio_url = request.build_absolute_uri(answer.audio_file.url)
                
                audio_files.append({
                    'id': answer.id,
                    'interview_id': answer.question.interview.id,
                    'candidate_name': answer.question.interview.candidate.name,
                    'candidate_email': answer.question.interview.candidate.email,
                    'question_number': answer.question.question_number,
                    'question_text': answer.question.question_text,
                    'audio_url': audio_url,
                    'audio_duration': answer.audio_duration,
                    'file_name': answer.audio_file.name if answer.audio_file else None,
                    'file_size': answer.audio_file.size if answer.audio_file else None,
                    'created_at': answer.created_at,
                    'transcript': answer.transcript,
                    'score': answer.score,
                    'feedback': answer.feedback
                })
            
            # Sort by creation date (newest first)
            audio_files.sort(key=lambda x: x['created_at'], reverse=True)
            
            return Response({
                'total_count': len(audio_files),
                'audio_files': audio_files
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Error listing audio files: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AudioFilesByInterviewView(APIView):
    """List all audio files for a specific interview"""
    permission_classes = [AllowAny]
    
    def get(self, request, interview_id):
        if not validate_api_key(request):
            return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            interview = get_object_or_404(Interview, id=interview_id)
            
            answers = Answer.objects.filter(
                question__interview=interview,
                audio_file__isnull=False
            ).exclude(audio_file='')
            
            audio_files = []
            for answer in answers:
                audio_url = None
                if answer.audio_file:
                    audio_url = request.build_absolute_uri(answer.audio_file.url)
                
                audio_files.append({
                    'id': answer.id,
                    'question_number': answer.question.question_number,
                    'question_text': answer.question.question_text,
                    'audio_url': audio_url,
                    'audio_duration': answer.audio_duration,
                    'file_name': answer.audio_file.name if answer.audio_file else None,
                    'file_size': answer.audio_file.size if answer.audio_file else None,
                    'created_at': answer.created_at,
                    'transcript': answer.transcript,
                    'score': answer.score,
                    'feedback': answer.feedback
                })
            
            # Sort by question number
            audio_files.sort(key=lambda x: x['question_number'])
            
            return Response({
                'interview_id': interview.id,
                'candidate_name': interview.candidate.name,
                'candidate_email': interview.candidate.email,
                'total_audio_files': len(audio_files),
                'audio_files': audio_files
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Error listing audio files: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TwilioAnswerWebhookView(View):
    """Handle recorded answers and move to the next question"""
    
    def post(self, request, interview_id, question_id):
        try:
            print(f"Answer webhook called for interview {interview_id}, question {question_id}")
            
            # Get interview & question
            interview = Interview.objects.get(id=interview_id)
            current_question = Question.objects.get(id=question_id)
            
            # Get Twilio recording URL
            recording_url = request.POST.get("RecordingUrl")
            print(f"Recording URL: {recording_url}")
            
            # Transcribe audio using OpenAI
            transcript = None
            score = None
            try:
                # transcript_response = openai.audio.transcriptions.create(
                #     model="gpt-4o-mini-transcribe",  # Whisper model
                #     file=requests.get(recording_url + ".mp3", stream=True).raw
                # )
                # transcript = transcript_response.text.strip()
                from .utils import process_wav_to_transcript
                transcript = process_wav_to_transcript(recording_url + ".mp3")
                print(f"Transcript: {transcript}")

                # Evaluate transcript (score 1–10)
                eval_prompt = f"""
                Question: {current_question.question_text}
                Candidate's Answer: {transcript}

                Evaluate the answer on a scale of 1 to 10 (10 being excellent, 1 being poor).
                Only return the number.
                """
                eval_response = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an HR assistant scoring candidate answers."},
                        {"role": "user", "content": eval_prompt}
                    ],
                    max_tokens=5,
                    temperature=0.0
                )
                score = int(eval_response.choices[0].message.content.strip())
                print(f"Score: {score}")

            except Exception as e:
                print(f"Transcription/Scoring failed: {e}")

            # Save answer
            Answer.objects.create(
                interview=interview,
                question=current_question,
                audio_url=recording_url,
                transcript=transcript,
                score=score
            )
            
            response = VoiceResponse()
            
            # Get next question
            next_question = (
                interview.questions.filter(question_number__gt=current_question.question_number)
                .order_by("question_number")
                .first()
            )
            
            if next_question:
                # Ask next question
                response.say(f"Question {next_question.question_number}: {next_question.question_text}", voice="alice")
                response.pause(length=1)
                
                # Record next answer
                next_action = f"/api/webhook/interview/{interview.id}/answer/{next_question.id}/"
                response.record(
                    action=next_action,
                    maxLength=120,
                    playBeep=True,
                    trim="trim-silence"
                )
            else:
                # No more questions → end call
                response.say("Thank you for completing the interview. Goodbye!", voice="alice")
                response.hangup()
            
            return HttpResponse(str(response), content_type="application/xml")
        
        except Exception as e:
            print(f"Error in answer webhook: {str(e)}")
            response = VoiceResponse()
            response.say("An error occurred. Please try again later.", voice="alice")
            return HttpResponse(str(response), content_type="application/xml")

class DebugTranscriptionView(APIView):
    """Debug endpoint to test transcription functionality"""
    permission_classes = [AllowAny]
    
    def post(self, request, answer_id):
        if not validate_api_key(request):
            return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            answer = get_object_or_404(Answer, id=answer_id)
            
            # Run debug function
            from .utils import debug_audio_file, generate_transcript_from_audio, test_assemblyai_connection
            
            # Test AssemblyAI connection
            connection_ok, connection_msg = test_assemblyai_connection()
            
            # Debug audio file
            debug_audio_file(answer)
            
            # Try to generate transcript
            transcript = generate_transcript_from_audio(answer)
            
            return Response({
                'success': True,
                'transcript': transcript,
                'message': 'Transcription process completed',
                'assemblyai_connection': {
                    'status': connection_ok,
                    'message': connection_msg
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EvaluateInterviewView(APIView):
    """Manually trigger complete evaluation for an interview (transcripts + scoring + recommendation)"""
    permission_classes = [AllowAny]
    
    def post(self, request, interview_id):
        if not validate_api_key(request):
            return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            interview = get_object_or_404(Interview, id=interview_id)
            
            # Track evaluation progress
            evaluation_results = {
                'transcripts_generated': 0,
                'answers_scored': 0,
                'recommendation_generated': False,
                'errors': []
            }
            
            # Step 1: Generate transcripts for all answers that need them
            print(f"Step 1: Generating transcripts for interview {interview_id}")
            for question in interview.questions.all():
                answer = question.answers.first()
                if answer and answer.audio_file:
                    if not answer.transcript:
                        try:
                            print(f"Generating transcript for question {question.question_number}")
                            transcript = generate_transcript_from_audio(answer)
                            if transcript:
                                evaluation_results['transcripts_generated'] += 1
                                print(f"✓ Transcript generated for question {question.question_number}")
                            else:
                                evaluation_results['errors'].append(f"Failed to generate transcript for question {question.question_number}")
                        except Exception as e:
                            error_msg = f"Error generating transcript for question {question.question_number}: {str(e)}"
                            evaluation_results['errors'].append(error_msg)
                            print(f"✗ {error_msg}")
                    else:
                        print(f"✓ Transcript already exists for question {question.question_number}")
            
            # Step 2: Score all answers that have transcripts
            print(f"Step 2: Scoring answers for interview {interview_id}")
            for question in interview.questions.all():
                answer = question.answers.first()
                if answer and answer.transcript:
                    try:
                        print(f"Scoring answer for question {question.question_number}")
                        score, feedback = score_answer(
                            question.question_text,
                            answer.transcript,
                            interview.candidate.resume_text
                        )
                        
                        # Update the answer
                        answer.score = score
                        answer.feedback = feedback
                        answer.save()
                        
                        evaluation_results['answers_scored'] += 1
                        print(f"✓ Answer scored for question {question.question_number}: {score}/10")
                    except Exception as e:
                        error_msg = f"Error scoring answer for question {question.question_number}: {str(e)}"
                        evaluation_results['errors'].append(error_msg)
                        print(f"✗ {error_msg}")
            
            # Step 3: Generate final recommendation
            print(f"Step 3: Generating final recommendation for interview {interview_id}")
            try:
                recommendation = generate_final_recommendation(interview)
                interview.recommendation = recommendation
                interview.save()
                evaluation_results['recommendation_generated'] = True
                print(f"✓ Final recommendation generated")
            except Exception as e:
                error_msg = f"Error generating final recommendation: {str(e)}"
                evaluation_results['errors'].append(error_msg)
                print(f"✗ {error_msg}")
            
            # Step 4: Calculate statistics
            total_questions = interview.questions.count()
            answered_questions = 0
            scored_questions = 0
            total_score = 0
            
            for question in interview.questions.all():
                answer = question.answers.first()
                if answer and answer.transcript:
                    answered_questions += 1
                if answer and answer.score is not None:
                    scored_questions += 1
                    total_score += answer.score
            
            average_score = total_score / scored_questions if scored_questions > 0 else 0
            
            return Response({
                'success': True,
                'interview_id': interview.id,
                'candidate_name': interview.candidate.name,
                'evaluation_summary': {
                    'total_questions': total_questions,
                    'answered_questions': answered_questions,
                    'scored_questions': scored_questions,
                    'average_score': round(average_score, 2),
                    'transcripts_generated': evaluation_results['transcripts_generated'],
                    'answers_scored': evaluation_results['answers_scored'],
                    'recommendation_generated': evaluation_results['recommendation_generated'],
                    'errors': evaluation_results['errors'] if evaluation_results['errors'] else None
                },
                'message': f'Evaluation completed: {scored_questions}/{total_questions} questions scored, avg score: {average_score:.2f}/10'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)