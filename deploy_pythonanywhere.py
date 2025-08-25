#!/usr/bin/env python3
"""
Deployment script for AI Interview Screener on PythonAnywhere
This script helps set up the project on PythonAnywhere
"""

import os
import sys
import subprocess

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return None

def create_env_file():
    """Create .env file with template values"""
    env_content = """# Django Settings
SECRET_KEY=your-secret-key-here-change-this
DEBUG=False
ALLOWED_HOSTS=yourusername.pythonanywhere.com

# API Key for authentication
API_KEY=your-api-key-here-change-this

# OpenAI Settings
OPENAI_API_KEY=your-openai-api-key-here

# Twilio Settings
TWILIO_ACCOUNT_SID=your-twilio-account-sid-here
TWILIO_AUTH_TOKEN=your-twilio-auth-token-here
TWILIO_PHONE_NUMBER=+1234567890

# Whitelisted phone numbers for testing (comma-separated)
WHITELISTED_NUMBERS=+1234567890,+1987654321

# Base URL for webhooks (update with your PythonAnywhere domain)
BASE_URL=https://yourusername.pythonanywhere.com

# Redis URL (for Celery) - Optional for basic setup
REDIS_URL=redis://localhost:6379/0
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    print("✅ Created .env file template")
    print("⚠️  Please edit .env file with your actual credentials")

def main():
    print("🚀 AI Interview Screener - PythonAnywhere Deployment Helper")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("❌ Error: manage.py not found. Please run this script from the project root directory.")
        sys.exit(1)
    
    # Create .env file
    if not os.path.exists('.env'):
        create_env_file()
    else:
        print("✅ .env file already exists")
    
    # Install dependencies
    run_command("pip install -r requirements.txt", "Installing Python dependencies")
    
    # Run migrations
    run_command("python manage.py makemigrations", "Creating database migrations")
    run_command("python manage.py migrate", "Applying database migrations")
    
    # Collect static files
    run_command("python manage.py collectstatic --noinput", "Collecting static files")
    
    # Create media directory
    if not os.path.exists('media'):
        os.makedirs('media')
        print("✅ Created media directory")
    
    print("\n🎉 Deployment setup completed!")
    print("\n📋 Next steps:")
    print("1. Edit .env file with your actual credentials")
    print("2. Create a superuser: python manage.py createsuperuser")
    print("3. Configure your PythonAnywhere web app")
    print("4. Update your WSGI file to point to this project")
    print("5. Configure Twilio webhook URLs")
    print("\n📚 See README.md for detailed deployment instructions")

if __name__ == "__main__":
    main()
