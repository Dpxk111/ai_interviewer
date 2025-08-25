#!/usr/bin/env python
"""
Debug script for AI Interview Screener
Run this to check all critical components
"""

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_screener.settings')
django.setup()

from interviews.models import JobDescription, Candidate, Interview, Question
from interviews.utils import generate_interview_twiml, create_twilio_call
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse

def check_environment():
    """Check if all required environment variables are set"""
    print("🔍 Checking Environment Variables...")
    
    required_vars = [
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN', 
        'TWILIO_PHONE_NUMBER',
        'OPENAI_API_KEY',
        'BASE_URL',
        'API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = getattr(settings, var, None)
        if not value:
            missing_vars.append(var)
            print(f"❌ {var}: NOT SET")
        else:
            # Mask sensitive values
            if 'KEY' in var or 'TOKEN' in var or 'SID' in var:
                masked_value = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '***'
                print(f"✅ {var}: {masked_value}")
            else:
                print(f"✅ {var}: {value}")
    
    if missing_vars:
        print(f"\n❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    else:
        print("\n✅ All environment variables are set")
        return True

def check_twilio_connection():
    """Test Twilio connection"""
    print("\n🔍 Testing Twilio Connection...")
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # Try to get account info
        account = client.api.accounts(settings.TWILIO_ACCOUNT_SID).fetch()
        print(f"✅ Twilio connection successful")
        print(f"   Account: {account.friendly_name}")
        print(f"   Status: {account.status}")
        return True
    except Exception as e:
        print(f"❌ Twilio connection failed: {e}")
        return False

def check_database():
    """Check database and sample data"""
    print("\n🔍 Checking Database...")
    
    try:
        # Check if we have any data
        jd_count = JobDescription.objects.count()
        candidate_count = Candidate.objects.count()
        interview_count = Interview.objects.count()
        question_count = Question.objects.count()
        
        print(f"✅ Database connection successful")
        print(f"   Job Descriptions: {jd_count}")
        print(f"   Candidates: {candidate_count}")
        print(f"   Interviews: {interview_count}")
        print(f"   Questions: {question_count}")
        
        # Check latest interview
        if interview_count > 0:
            latest_interview = Interview.objects.latest('created_at')
            print(f"\n📋 Latest Interview:")
            print(f"   ID: {latest_interview.id}")
            print(f"   Status: {latest_interview.status}")
            print(f"   Candidate: {latest_interview.candidate.name} ({latest_interview.candidate.phone})")
            print(f"   Questions: {latest_interview.questions.count()}")
            
            # Check if questions exist
            questions = latest_interview.questions.all()
            if questions.exists():
                print(f"   ✅ Questions found:")
                for i, q in enumerate(questions[:3], 1):
                    print(f"      {i}. {q.question_text[:50]}...")
                if questions.count() > 3:
                    print(f"      ... and {questions.count() - 3} more")
            else:
                print(f"   ❌ No questions found for this interview")
                return False
        else:
            print("   ⚠️  No interviews found in database")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

def test_twiml_generation():
    """Test TwiML generation for latest interview"""
    print("\n🔍 Testing TwiML Generation...")
    
    try:
        interview = Interview.objects.latest('created_at')
        print(f"Testing TwiML for interview: {interview.id}")
        
        twiml = generate_interview_twiml(interview)
        
        if twiml and '<?xml' in twiml:
            print("✅ TwiML generated successfully")
            print(f"   Length: {len(twiml)} characters")
            print(f"   Contains questions: {'Question' in twiml}")
            print(f"   Contains record action: {'record' in twiml.lower()}")
            return True
        else:
            print("❌ TwiML generation failed - invalid output")
            return False
            
    except Exception as e:
        print(f"❌ TwiML generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_twilio_call_creation():
    """Test Twilio call creation (without actually making the call)"""
    print("\n🔍 Testing Twilio Call Creation...")
    
    try:
        interview = Interview.objects.latest('created_at')
        print(f"Testing call creation for interview: {interview.id}")
        
        # Test the call creation function
        call_sid = create_twilio_call(interview)
        
        if call_sid:
            print(f"✅ Call creation successful")
            print(f"   Call SID: {call_sid}")
            return True
        else:
            print("❌ Call creation failed - no call SID returned")
            return False
            
    except Exception as e:
        print(f"❌ Call creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all checks"""
    print("🚀 AI Interview Screener - Debug Report")
    print("=" * 50)
    
    checks = [
        ("Environment Variables", check_environment),
        ("Twilio Connection", check_twilio_connection),
        ("Database", check_database),
        ("TwiML Generation", test_twiml_generation),
        ("Call Creation", test_twilio_call_creation),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} check failed with exception: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All checks passed! Your system should be working correctly.")
        print("\n💡 If you're still getting errors, check:")
        print("   1. Django logs for detailed error messages")
        print("   2. Twilio webhook logs in your Twilio console")
        print("   3. Network connectivity to your server")
    else:
        print("⚠️  Some checks failed. Please fix the issues above before testing calls.")
        print("\n🔧 Common fixes:")
        print("   1. Set missing environment variables")
        print("   2. Check Twilio credentials")
        print("   3. Ensure BASE_URL is correct and accessible")
        print("   4. Create sample data if database is empty")

if __name__ == "__main__":
    main()
