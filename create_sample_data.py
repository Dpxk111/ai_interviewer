#!/usr/bin/env python
"""
Create sample data for AI Interview Screener testing
"""

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_screener.settings')
django.setup()

from interviews.models import JobDescription, Candidate, Interview, Question

def create_sample_data():
    """Create sample data for testing"""
    print("🚀 Creating Sample Data for AI Interview Screener")
    print("=" * 50)
    
    try:
        # Create Job Description
        print("📝 Creating Job Description...")
        job_description = JobDescription.objects.create(
            title="Python Developer",
            description="""
            We are looking for a skilled Python Developer to join our team.
            
            Requirements:
            - 3+ years of experience with Python
            - Experience with Django, Flask, or similar frameworks
            - Knowledge of databases (PostgreSQL, MySQL)
            - Experience with REST APIs
            - Git version control
            - Agile development methodologies
            
            Responsibilities:
            - Develop and maintain web applications
            - Write clean, maintainable code
            - Collaborate with cross-functional teams
            - Participate in code reviews
            - Debug and fix issues
            """,
            questions=[
                "Tell me about your experience with Python and Django.",
                "Describe a challenging project you worked on recently.",
                "How do you handle debugging complex issues?",
                "What's your experience with database design?",
                "How do you stay updated with new technologies?",
                "Describe a time when you had to work under pressure."
            ]
        )
        print(f"✅ Job Description created: {job_description.title}")
        
        # Create Candidate
        print("\n👤 Creating Candidate...")
        candidate = Candidate.objects.create(
            name="John Doe",
            email="john.doe@example.com",
            phone="+919876543210",
            resume_text="""
            John Doe
            Python Developer
            
            Experience:
            - Senior Python Developer at TechCorp (2020-2023)
            - Python Developer at StartupXYZ (2018-2020)
            
            Skills:
            - Python, Django, Flask
            - PostgreSQL, MySQL
            - REST APIs, Git
            - Docker, AWS
            
            Education:
            - B.Tech in Computer Science
            """
        )
        print(f"✅ Candidate created: {candidate.name} ({candidate.phone})")
        
        # Create Interview
        print("\n🎯 Creating Interview...")
        interview = Interview.objects.create(
            job_description=job_description,
            candidate=candidate,
            status='pending'
        )
        print(f"✅ Interview created: {interview.id}")
        
        # Create Questions
        print("\n❓ Creating Questions...")
        for i, question_text in enumerate(job_description.questions, 1):
            Question.objects.create(
                interview=interview,
                question_text=question_text,
                question_number=i
            )
        print(f"✅ Created {len(job_description.questions)} questions")
        
        print("\n" + "=" * 50)
        print("🎉 Sample Data Created Successfully!")
        print("=" * 50)
        print(f"📋 Job Description ID: {job_description.id}")
        print(f"👤 Candidate ID: {candidate.id}")
        print(f"🎯 Interview ID: {interview.id}")
        print(f"❓ Questions: {interview.questions.count()}")
        
        print("\n💡 You can now test the system with:")
        print(f"   POST /api/interviews/{interview.id}/trigger/")
        print(f"   GET /api/interviews/{interview.id}/results/")
        
        return interview
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_existing_data():
    """Check if data already exists"""
    jd_count = JobDescription.objects.count()
    candidate_count = Candidate.objects.count()
    interview_count = Interview.objects.count()
    
    if jd_count > 0 or candidate_count > 0 or interview_count > 0:
        print("⚠️  Data already exists in the database:")
        print(f"   Job Descriptions: {jd_count}")
        print(f"   Candidates: {candidate_count}")
        print(f"   Interviews: {interview_count}")
        
        response = input("\nDo you want to create additional sample data? (y/n): ")
        return response.lower() == 'y'
    
    return True

if __name__ == "__main__":
    if check_existing_data():
        create_sample_data()
    else:
        print("Skipping sample data creation.")
