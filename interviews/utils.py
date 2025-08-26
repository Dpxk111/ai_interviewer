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
import random

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
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert HR professional who creates relevant interview questions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        questions_text = response.choices[0].message.content.strip()
        questions = json.loads(questions_text)
        ls = [5, 6, 7]
        number_of_questions = random.choice(ls)
        return questions[:number_of_questions]
        
    except Exception as e:
        print(f"Error generating questions: {e}")
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
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert interviewer evaluating candidate responses."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.3
        )
        
        result_text = response.choices[0].message.content.strip()
        result = json.loads(result_text)
        print(result, "=========\n\n\n\n\n\n")
        return result.get('score', 5), result.get('feedback', 'No feedback available')
        
    except Exception as e:
        print(f"Error scoring answer: {e}")
        return 10, str(e)


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
                    'answer': answer.transcript or "No transcript available",
                    'score': answer.score if answer.score is not None else "Not evaluated"
                })
                if answer.score is not None:
                    total_score += answer.score
                    answer_count += 1
        
        if answer_count == 0:
            return "No answers provided for evaluation."
        
        avg_score = total_score / answer_count
        
        prompt = f"""
        You are evaluating an interview based on transcripts.

        Average Score: {avg_score:.2f}/10
        Total Questions Answered: {answer_count}

        Here are the interview transcripts with scores:
        {json.dumps(questions_answers, indent=2)}

        Based on the above, provide a final recommendation in 2-3 sentences 
        on whether the candidate should proceed to the next round.
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
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
        
        print(f"TwiML URL: {twiml_url} \n\n")
        print(f"Status callback URL: {status_callback_url} \n\n")
        
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


import os
import requests
from django.conf import settings

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

# Validate AssemblyAI API key
if not ASSEMBLYAI_API_KEY:
    print("WARNING: ASSEMBLYAI_API_KEY not found in environment variables")

def test_assemblyai_connection():
    """Test if AssemblyAI API is accessible"""
    try:
        if not ASSEMBLYAI_API_KEY:
            return False, "AssemblyAI API key not configured"
        
        # Test with a simple API call
        response = requests.get(
            "https://api.assemblyai.com/v2/transcript",
            headers={"authorization": ASSEMBLYAI_API_KEY},
            params={"limit": 1}
        )
        
        if response.status_code == 200:
            return True, "AssemblyAI API connection successful"
        elif response.status_code == 401:
            return False, "AssemblyAI API key is invalid"
        else:
            return False, f"AssemblyAI API error: {response.status_code}"
            
    except Exception as e:
        return False, f"AssemblyAI API connection failed: {str(e)}"

def validate_audio_file(file_path):
    """Validate that a file is a valid audio file"""
    try:
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "File is empty"
        
        if file_size < 1024:  # Less than 1KB
            return False, "File is too small to be valid audio"
        
        # Try to load with pydub to validate it's audio
        try:
            sound = AudioSegment.from_file(file_path)
            if len(sound) < 100:  # Less than 100ms
                return False, "Audio duration is too short"
            return True, f"Valid audio file: {len(sound)}ms, {sound.channels} channels, {sound.frame_rate}Hz"
        except Exception as e:
            return False, f"Not a valid audio file: {str(e)}"
            
    except Exception as e:
        return False, f"Error validating file: {str(e)}"  



from pydub import AudioSegment
import requests
import time

def convert_to_wav_local(input_path, output_path):
    """Convert any audio file to WAV PCM16 16kHz mono"""
    try:
        print(f"Converting {input_path} to {output_path}")
        
        # Check if input file exists and has content
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        file_size = os.path.getsize(input_path)
        if file_size == 0:
            raise ValueError(f"Input file is empty: {input_path}")
        
        print(f"Input file size: {file_size} bytes")
        
        # Try to load the audio file
        sound = AudioSegment.from_file(input_path)
        print(f"Audio loaded - duration: {len(sound)}ms, channels: {sound.channels}, frame_rate: {sound.frame_rate}")
        
        # Convert to mono, 16kHz, 16-bit
        sound = sound.set_channels(1).set_frame_rate(16000).set_sample_width(2)
        print(f"Converted audio - duration: {len(sound)}ms, channels: {sound.channels}, frame_rate: {sound.frame_rate}")
        
        # Export to WAV
        sound.export(output_path, format="wav")
        
        # Verify output file
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"Successfully converted to {output_path} (size: {os.path.getsize(output_path)} bytes)")
            return output_path
        else:
            raise ValueError(f"Output file creation failed: {output_path}")
            
    except Exception as e:
        print(f"Error in convert_to_wav_local: {e}")
        import traceback
        traceback.print_exc()
        raise

def convert_to_mp3_local(input_path, output_path):
    """Convert any audio file to MP3 format"""
    try:
        print(f"Converting {input_path} to MP3: {output_path}")
        
        # Check if input file exists and has content
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        file_size = os.path.getsize(input_path)
        if file_size == 0:
            raise ValueError(f"Input file is empty: {input_path}")
        
        print(f"Input file size: {file_size} bytes")
        
        # Try to load the audio file
        sound = AudioSegment.from_file(input_path)
        print(f"Audio loaded - duration: {len(sound)}ms, channels: {sound.channels}, frame_rate: {sound.frame_rate}")
        
        # Convert to mono, 44.1kHz for better compatibility
        sound = sound.set_channels(1).set_frame_rate(44100)
        print(f"Converted audio - duration: {len(sound)}ms, channels: {sound.channels}, frame_rate: {sound.frame_rate}")
        
        # Export to MP3 with good quality
        sound.export(output_path, format="mp3", bitrate="128k")
        
        # Verify output file
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"Successfully converted to MP3: {output_path} (size: {os.path.getsize(output_path)} bytes)")
            return output_path
        else:
            raise ValueError(f"MP3 file creation failed: {output_path}")
            
    except Exception as e:
        print(f"Error in convert_to_mp3_local: {e}")
        import traceback
        traceback.print_exc()
        raise

def generate_transcript_from_audio(answer_obj):
    """Generate transcript using AssemblyAI."""
    try:
        if not ASSEMBLYAI_API_KEY:
            print("ERROR: AssemblyAI API key not configured")
            return None
            
        if not answer_obj.audio_file:
            return None

        # Return existing transcript if available
        if answer_obj.transcript:
            return answer_obj.transcript

        audio_path = answer_obj.audio_file.path
        
        print(f"Processing audio file: {audio_path}")
        print(f"File exists: {os.path.exists(audio_path)}")
        print(f"File size: {os.path.getsize(audio_path) if os.path.exists(audio_path) else 'N/A'}")

        is_valid, validation_msg = validate_audio_file(audio_path)
        if not is_valid:
            print(f"Audio file validation failed: {validation_msg}")
            debug_audio_file(answer_obj)
            return None
        
        print(f"Audio file validation passed: {validation_msg}")

        # Convert to MP3 format
        mp3_path = audio_path.rsplit('.', 1)[0] + "_converted.mp3"
        try:
            convert_to_mp3_local(audio_path, mp3_path)
            print(f"Converted to MP3: {mp3_path}")
        except Exception as e:
            print(f"Error converting audio: {e}")
            # Try uploading original file if conversion fails
            mp3_path = audio_path

        # Upload to AssemblyAI
        try:
            with open(mp3_path, "rb") as f:
                upload_response = requests.post(
                    "https://api.assemblyai.com/v2/upload",
                    headers={"authorization": ASSEMBLYAI_API_KEY},
                    files={"file": f}
                )
            
            if upload_response.status_code != 200:
                print(f"Upload failed: {upload_response.status_code} - {upload_response.text}")
                return None
                
            audio_url = upload_response.json()["upload_url"]
            print(f"Uploaded to AssemblyAI: {audio_url}")
        except Exception as e:
            print(f"Error uploading to AssemblyAI: {e}")
            return None

        # Request transcription
        try:
            transcript_response = requests.post(
                "https://api.assemblyai.com/v2/transcript",
                headers={"authorization": ASSEMBLYAI_API_KEY},
                json={"audio_url": audio_url}
            )
            
            if transcript_response.status_code != 200:
                print(f"Transcription request failed: {transcript_response.status_code} - {transcript_response.text}")
                return None
                
            transcript_id = transcript_response.json()["id"]
            print(f"Transcription ID: {transcript_id}")
        except Exception as e:
            print(f"Error requesting transcription: {e}")
            return None

        # Poll until transcription is done
        max_attempts = 60  # 5 minutes max
        attempts = 0
        
        while attempts < max_attempts:
            try:
                status_response = requests.get(
                    f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                    headers={"authorization": ASSEMBLYAI_API_KEY}
                ).json()

                print(f"Transcription status: {status_response.get('status')}")

                if status_response["status"] == "completed":
                    transcript_text = status_response["text"]
                    if transcript_text:
                        # Save transcript in DB
                        answer_obj.transcript = transcript_text
                        answer_obj.save(update_fields=["transcript"])
                        print(f"Transcript saved: {transcript_text[:100]}...")
                        return transcript_text
                    else:
                        print("Transcription completed but no text returned")
                        return None

                elif status_response["status"] == "error":
                    error_msg = status_response.get('error', 'Unknown error')
                    print(f"AssemblyAI error: {error_msg}")
                    
                    # Check for specific transcoding error
                    if "Transcoding failed" in error_msg and "application/octet-stream" in error_msg:
                        print("Detected audio format issue. Trying fallback method...")
                        return generate_transcript_fallback(answer_obj, audio_path)
                    
                    return None

                attempts += 1
                time.sleep(3)

            except Exception as e:
                print(f"Error polling transcription status: {e}")
                attempts += 1
                time.sleep(3)

        print("Transcription polling timed out")
        return None

    except Exception as e:
        print(f"Error generating transcript with AssemblyAI: {e}")
        import traceback
        traceback.print_exc()
        
        # Try fallback method - upload original file directly
        print("Trying fallback method with original file...")
        try:
            return generate_transcript_fallback(answer_obj, audio_path)
        except Exception as fallback_error:
            print(f"Fallback method also failed: {fallback_error}")
            return None
    finally:
        # Clean up temporary MP3 file if it was created
        try:
            if 'mp3_path' in locals() and mp3_path != audio_path and os.path.exists(mp3_path):
                os.remove(mp3_path)
                print(f"Cleaned up temporary file: {mp3_path}")
        except Exception as e:
            print(f"Error cleaning up temporary file: {e}")

def generate_transcript_fallback(answer_obj, audio_path):
    """Fallback method to generate transcript using original file"""
    try:
        print(f"Using fallback method with file: {audio_path}")
        
        # Upload original file directly to AssemblyAI
        with open(audio_path, "rb") as f:
            upload_response = requests.post(
                "https://api.assemblyai.com/v2/upload",
                headers={"authorization": ASSEMBLYAI_API_KEY},
                files={"file": f}
            )
        
        if upload_response.status_code != 200:
            print(f"Fallback upload failed: {upload_response.status_code} - {upload_response.text}")
            return None
            
        audio_url = upload_response.json()["upload_url"]
        print(f"Fallback upload successful: {audio_url}")

        # Request transcription with different parameters
        transcript_response = requests.post(
            "https://api.assemblyai.com/v2/transcript",
            headers={"authorization": ASSEMBLYAI_API_KEY},
            json={
                "audio_url": audio_url,
                "auto_chapters": False,
                "speaker_labels": False,
                "punctuate": True,
                "format_text": True
            }
        )
        
        if transcript_response.status_code != 200:
            print(f"Fallback transcription request failed: {transcript_response.status_code} - {transcript_response.text}")
            return None
            
        transcript_id = transcript_response.json()["id"]
        print(f"Fallback transcription ID: {transcript_id}")

        # Poll until transcription is done
        max_attempts = 30  # 2.5 minutes max for fallback
        attempts = 0
        
        while attempts < max_attempts:
            try:
                status_response = requests.get(
                    f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                    headers={"authorization": ASSEMBLYAI_API_KEY}
                ).json()

                print(f"Fallback transcription status: {status_response.get('status')}")

                if status_response["status"] == "completed":
                    transcript_text = status_response["text"]
                    if transcript_text:
                        # Save transcript in DB
                        answer_obj.transcript = transcript_text
                        answer_obj.save(update_fields=["transcript"])
                        print(f"Fallback transcript saved: {transcript_text[:100]}...")
                        return transcript_text
                    else:
                        print("Fallback transcription completed but no text returned")
                        return None

                elif status_response["status"] == "error":
                    error_msg = status_response.get('error', 'Unknown error')
                    print(f"Fallback AssemblyAI error: {error_msg}")
                    return None

                attempts += 1
                time.sleep(3)

            except Exception as e:
                print(f"Error polling fallback transcription status: {e}")
                attempts += 1
                time.sleep(3)

        print("Fallback transcription polling timed out")
        return None

    except Exception as e:
        print(f"Error in fallback transcription: {e}")
        import traceback
        traceback.print_exc()
        return None

def debug_audio_file(answer_obj):
    """Debug function to analyze audio file issues"""
    try:
        if not answer_obj.audio_file:
            print("No audio file attached to answer")
            return
        
        audio_path = answer_obj.audio_file.path
        print(f"\n=== Audio File Debug Info ===")
        print(f"File path: {audio_path}")
        print(f"File exists: {os.path.exists(audio_path)}")
        
        if os.path.exists(audio_path):
            print(f"File size: {os.path.getsize(audio_path)} bytes")
            print(f"File permissions: {oct(os.stat(audio_path).st_mode)[-3:]}")
            
            # Check file header
            with open(audio_path, 'rb') as f:
                header = f.read(16)
                print(f"File header (hex): {header.hex()}")
                
                # Check for common audio file signatures
                if header.startswith(b'RIFF'):
                    print("Detected WAV file signature")
                elif header.startswith(b'ID3') or header.startswith(b'\xff\xfb'):
                    print("Detected MP3 file signature")
                elif header.startswith(b'OggS'):
                    print("Detected OGG file signature")
                else:
                    print("Unknown file format")
        
        # Try to validate with pydub
        is_valid, validation_msg = validate_audio_file(audio_path)
        print(f"Pydub validation: {validation_msg}")
        
        print("=== End Debug Info ===\n")
        
    except Exception as e:
        print(f"Error in debug_audio_file: {e}")
        import traceback
        traceback.print_exc()


def process_wav_to_transcript(wav_file_path, output_mp3_path=None):
    """
    Convert a WAV file to MP3 and generate transcript using AssemblyAI.
    
    Args:
        wav_file_path (str): Path to the input WAV file
        output_mp3_path (str, optional): Path for the output MP3 file. 
                                       If None, will create in same directory as WAV file
    
    Returns:
        dict: Dictionary containing:
            - 'success' (bool): Whether the process was successful
            - 'transcript' (str): The generated transcript text
            - 'mp3_path' (str): Path to the converted MP3 file
            - 'error' (str): Error message if failed
            - 'processing_time' (float): Time taken for the entire process
    """
    import time
    start_time = time.time()
    
    try:
        # Validate input file
        if not os.path.exists(wav_file_path):
            return {
                'success': False,
                'transcript': None,
                'mp3_path': None,
                'error': f'Input WAV file not found: {wav_file_path}',
                'processing_time': time.time() - start_time
            }
        
        if not wav_file_path.lower().endswith('.wav'):
            return {
                'success': False,
                'transcript': None,
                'mp3_path': None,
                'error': f'Input file is not a WAV file: {wav_file_path}',
                'processing_time': time.time() - start_time
            }
        
        # Check AssemblyAI API key
        if not ASSEMBLYAI_API_KEY:
            return {
                'success': False,
                'transcript': None,
                'mp3_path': None,
                'error': 'AssemblyAI API key not configured',
                'processing_time': time.time() - start_time
            }
        
        print(f"Processing WAV file: {wav_file_path}")
        
        # Generate MP3 output path if not provided
        if output_mp3_path is None:
            output_mp3_path = wav_file_path.rsplit('.', 1)[0] + "_converted.mp3"
        
        # Step 1: Convert WAV to MP3
        print("Step 1: Converting WAV to MP3...")
        try:
            convert_to_mp3_local(wav_file_path, output_mp3_path)
            print(f"✓ WAV to MP3 conversion successful: {output_mp3_path}")
        except Exception as e:
            return {
                'success': False,
                'transcript': None,
                'mp3_path': None,
                'error': f'Failed to convert WAV to MP3: {str(e)}',
                'processing_time': time.time() - start_time
            }
        
        # Step 2: Upload MP3 to AssemblyAI
        print("Step 2: Uploading MP3 to AssemblyAI...")
        try:
            with open(output_mp3_path, "rb") as f:
                upload_response = requests.post(
                    "https://api.assemblyai.com/v2/upload",
                    headers={"authorization": ASSEMBLYAI_API_KEY},
                    files={"file": f}
                )
            
            if upload_response.status_code != 200:
                return {
                    'success': False,
                    'transcript': None,
                    'mp3_path': output_mp3_path,
                    'error': f'AssemblyAI upload failed: {upload_response.status_code} - {upload_response.text}',
                    'processing_time': time.time() - start_time
                }
                
            audio_url = upload_response.json()["upload_url"]
            print(f"✓ MP3 uploaded to AssemblyAI: {audio_url}")
        except Exception as e:
            return {
                'success': False,
                'transcript': None,
                'mp3_path': output_mp3_path,
                'error': f'Failed to upload to AssemblyAI: {str(e)}',
                'processing_time': time.time() - start_time
            }
        
        # Step 3: Request transcription
        print("Step 3: Requesting transcription...")
        try:
            transcript_response = requests.post(
                "https://api.assemblyai.com/v2/transcript",
                headers={"authorization": ASSEMBLYAI_API_KEY},
                json={
                    "audio_url": audio_url,
                    "auto_chapters": False,
                    "speaker_labels": False,
                    "punctuate": True,
                    "format_text": True
                }
            )
            
            if transcript_response.status_code != 200:
                return {
                    'success': False,
                    'transcript': None,
                    'mp3_path': output_mp3_path,
                    'error': f'Transcription request failed: {transcript_response.status_code} - {transcript_response.text}',
                    'processing_time': time.time() - start_time
                }
                
            transcript_id = transcript_response.json()["id"]
            print(f"✓ Transcription requested, ID: {transcript_id}")
        except Exception as e:
            return {
                'success': False,
                'transcript': None,
                'mp3_path': output_mp3_path,
                'error': f'Failed to request transcription: {str(e)}',
                'processing_time': time.time() - start_time
            }
        
        # Step 4: Poll for transcription completion
        print("Step 4: Waiting for transcription to complete...")
        max_attempts = 60  # 5 minutes max
        attempts = 0
        
        while attempts < max_attempts:
            try:
                status_response = requests.get(
                    f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                    headers={"authorization": ASSEMBLYAI_API_KEY}
                ).json()

                status = status_response.get('status')
                print(f"Transcription status: {status}")

                if status == "completed":
                    transcript_text = status_response.get("text", "")
                    if transcript_text:
                        print(f"✓ Transcription completed successfully")
                        print(f"Transcript: {transcript_text[:100]}...")
                        
                        return {
                            'success': True,
                            'transcript': transcript_text,
                            'mp3_path': output_mp3_path,
                            'error': None,
                            'processing_time': time.time() - start_time
                        }
                    else:
                        return {
                            'success': False,
                            'transcript': None,
                            'mp3_path': output_mp3_path,
                            'error': 'Transcription completed but no text returned',
                            'processing_time': time.time() - start_time
                        }

                elif status == "error":
                    error_msg = status_response.get('error', 'Unknown error')
                    return {
                        'success': False,
                        'transcript': None,
                        'mp3_path': output_mp3_path,
                        'error': f'AssemblyAI transcription error: {error_msg}',
                        'processing_time': time.time() - start_time
                    }

                attempts += 1
                time.sleep(3)  # Wait 3 seconds between polls

            except Exception as e:
                print(f"Error polling transcription status: {e}")
                attempts += 1
                time.sleep(3)
        
        # If we get here, polling timed out
        return {
            'success': False,
            'transcript': None,
            'mp3_path': output_mp3_path,
            'error': 'Transcription polling timed out after 5 minutes',
            'processing_time': time.time() - start_time
        }
        
    except Exception as e:
        return {
            'success': False,
            'transcript': None,
            'mp3_path': output_mp3_path if 'output_mp3_path' in locals() else None,
            'error': f'Unexpected error: {str(e)}',
            'processing_time': time.time() - start_time
        }
    finally:
        # Clean up temporary MP3 file if it was created in the same directory
        try:
            if ('output_mp3_path' in locals() and 
                output_mp3_path and 
                os.path.exists(output_mp3_path) and
                output_mp3_path.endswith('_converted.mp3')):
                os.remove(output_mp3_path)
                print(f"Cleaned up temporary MP3 file: {output_mp3_path}")
        except Exception as e:
            print(f"Warning: Could not clean up temporary MP3 file: {e}")


def test_assemblyai_connection():
    """Test AssemblyAI API connection"""
    try:
        if not ASSEMBLYAI_API_KEY:
            return False, "AssemblyAI API key not configured"
        
        # Make a simple API call to test connection
        response = requests.get(
            "https://api.assemblyai.com/v2/transcript",
            headers={"authorization": ASSEMBLYAI_API_KEY}
        )
        
        if response.status_code == 200:
            return True, "AssemblyAI connection successful"
        else:
            return False, f"AssemblyAI connection failed: {response.status_code} - {response.text}"
            
    except Exception as e:
        return False, f"AssemblyAI connection error: {str(e)}"