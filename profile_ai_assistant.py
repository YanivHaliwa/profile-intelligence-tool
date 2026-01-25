#!/usr/bin/env python3
import json
import argparse
import sys
import os
import requests
from openai import OpenAI
#version 26.7.25

DEBUG = False
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_config.json')


def load_model_config():
    """Load model configuration from model_config.json"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)

        if DEBUG:
            print(f"Loaded config: active_provider={config.get('active_provider')}")

        return config
    except FileNotFoundError:
        print(f"Warning: {CONFIG_FILE} not found, using OpenAI defaults")
        return {
            "active_provider": "openai",
            "providers": {
                "openai": {"enabled": True, "model": "gpt-4o", "api_key_env": "OPENAI_API_KEY"}
            }
        }
    except json.JSONDecodeError as e:
        print(f"Error parsing {CONFIG_FILE}: {e}")
        sys.exit(1)

def load_profile_data(json_file):
    """Load and validate LinkedIn profile JSON data"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if DEBUG:
            print(f"Loaded JSON file: {json_file}")
            print(f"Top-level keys: {list(data.keys())}")
        
        return data
    except FileNotFoundError:
        print(f"Error: File '{json_file}' not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in '{json_file}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading file: {e}")
        sys.exit(1)

def format_profile_for_analysis(data):
    """Format the profile data into a readable text for ChatGPT analysis"""
    
    # Extract main profile info
    main_profile = data.get('main_profile', {})
    name = main_profile.get('name', 'Unknown')
    headline = main_profile.get('headline', 'Not available')
    location = main_profile.get('location', 'Not available')
    about = main_profile.get('about', 'Not available')
    
    # Build formatted text
    formatted_text = f"""LinkedIn Profile Analysis Request

=== BASIC INFORMATION ===
Name: {name}
Headline: {headline}
Location: {location}

=== ABOUT SECTION ===
{about}

=== PROFESSIONAL EXPERIENCE ===
"""
    
    # Experience
    experience = data.get('experience', [])
    if experience:
        for i, exp in enumerate(experience, 1):
            title = exp.get('title', 'Not available')
            company = exp.get('company', 'Not available')
            duration = exp.get('duration', 'Not available')
            description = exp.get('description', '')
            
            formatted_text += f"{i}. {title} at {company}\n"
            formatted_text += f"   Duration: {duration}\n"
            if description:
                formatted_text += f"   Description: {description}\n"
            formatted_text += "\n"
    else:
        formatted_text += "No experience data available\n\n"
    
    # Education
    formatted_text += "=== EDUCATION ===\n"
    education = data.get('education', [])
    if education:
        for i, edu in enumerate(education, 1):
            institution = edu.get('institution', 'Not available')
            degree = edu.get('degree', 'Not available')
            field = edu.get('field_of_study', '')
            duration = edu.get('duration', 'Not available')
            grade = edu.get('grade', '')
            
            formatted_text += f"{i}. {institution}\n"
            formatted_text += f"   Degree: {degree}"
            if field:
                formatted_text += f", {field}"
            formatted_text += f"\n   Duration: {duration}\n"
            if grade:
                formatted_text += f"   Grade: {grade}\n"
            formatted_text += "\n"
    else:
        formatted_text += "No education data available\n\n"
    
    # Skills
    formatted_text += "=== SKILLS ===\n"
    skills = data.get('skills', [])
    if skills:
        skill_names = [skill.get('name', '') for skill in skills if skill.get('name')]
        # Group skills and limit to avoid token overflow
        skill_list = ', '.join(skill_names[:30])  # Limit to first 30 skills
        formatted_text += f"{skill_list}\n"
        if len(skills) > 30:
            formatted_text += f"... and {len(skills) - 30} more skills\n"
        formatted_text += "\n"
    else:
        formatted_text += "No skills data available\n\n"
    
    # Projects
    formatted_text += "=== PROJECTS ===\n"
    projects = data.get('projects', [])
    if projects:
        for i, project in enumerate(projects, 1):
            name = project.get('name', 'Not available')
            description = project.get('description', '')
            duration = project.get('duration', 'Not available')
            
            formatted_text += f"{i}. {name}\n"
            formatted_text += f"   Duration: {duration}\n"
            if description and description != 'Not available':
                # Limit description length to avoid token overflow
                desc_text = description[:300] + "..." if len(description) > 300 else description
                formatted_text += f"   Description: {desc_text}\n"
            formatted_text += "\n"
    else:
        formatted_text += "No projects data available\n\n"
    
    # Certifications
    formatted_text += "=== CERTIFICATIONS ===\n"
    certifications = data.get('certifications', [])
    if certifications:
        for i, cert in enumerate(certifications, 1):
            name = cert.get('name', 'Not available')
            issuer = cert.get('issuer', 'Not available')
            issue_date = cert.get('issue_date', 'Not available')
            
            formatted_text += f"{i}. {name}\n"
            formatted_text += f"   Issuer: {issuer}\n"
            formatted_text += f"   Issue Date: {issue_date}\n\n"
    else:
        formatted_text += "No certifications data available\n\n"
    
    # Activity/Posts
    formatted_text += "=== ACTIVITY & POSTS ===\n"
    activity = data.get('activity', [])
    posts = data.get('posts', [])
    recent_activity = data.get('recent_activity', [])
    
    # Combine all activity sources
    all_posts = []
    if activity:
        all_posts.extend(activity)
    if posts:
        all_posts.extend(posts)
    if recent_activity:
        all_posts.extend(recent_activity)
    
    if all_posts:
        formatted_text += f"Total Posts/Activity: {len(all_posts)}\n\n"
        
        for i, post in enumerate(all_posts, 1):
            content = post.get('content', post.get('text', ''))
            date = post.get('date', post.get('time', 'Not available'))
            likes = post.get('likes', post.get('reactions', ''))
            comments = post.get('comments', '')
            reposts = post.get('reposts', '')
            post_type = post.get('type', 'Post')
            
            if content:
                # Show full content for analysis (don't truncate too much)
                content_text = content[:500] + "..." if len(content) > 500 else content
                formatted_text += f"{post_type} {i}: {content_text}\n"
                formatted_text += f"   Date: {date}\n"
                
                # Add engagement metrics
                engagement_parts = []
                if likes:
                    engagement_parts.append(f"{likes} likes")
                if comments:
                    engagement_parts.append(f"{comments}")
                if reposts:
                    engagement_parts.append(f"{reposts} reposts")
                
                if engagement_parts:
                    formatted_text += f"   Engagement: {', '.join(engagement_parts)}\n"
                formatted_text += "\n"
    else:
        formatted_text += "No activity/posts data available\n"
    
    formatted_text += "\n"
    
    return formatted_text

def analyze_with_chatgpt(profile_text, api_key, model='gpt-4o'):
    """Send profile data to ChatGPT for analysis"""

    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Create the analysis prompt
        system_prompt = """You are a professional LinkedIn profile analyzer and career consultant. 
Analyze the provided LinkedIn profile data and provide a comprehensive, professional summary in this EXACT order:

0. HEADLINE: One compelling, short line (max 10-12 words) that best defines this person - could be a professional tagline, a poetic sentence, or a catchy phrase that captures their essence and expertise

1. OVERALL RATING: Provide a comprehensive professional score out of 100 and detailed evaluation. Format it as:
   📊 OVERALL PROFESSIONAL RATING: [Score]/100
   
   Then provide a detailed breakdown explaining the score based on these 6 criteria with weighted importance:
   *  Professional experience depth and relevance: [Score]/25 (Most Important)
   *  Skills diversity and market demand: [Score]/20 (Very Important)
   *  Profile completeness and presentation quality: [Score]/15 (Important)
   *  Activity and thought leadership presence: [Score]/15 (Important)
   *  Education and certifications value: [Score]/15 (Important)
   *  Career trajectory and growth potential: [Score]/10 (Moderately Important)
   
   Calculate the total score by adding all 6 sections (Total: 100 points). Include specific strengths that contributed to the score and areas for improvement.

== SUMMARY ==
2. PROFESSIONAL SUMMARY: A 2-3 sentence overview of the person's career focus and expertise
3. KEY STRENGTHS: Top 3-4 professional strengths based on experience and skills
4. CAREER TRAJECTORY: Analysis of their career progression and growth
5. CAREER RECOMMENDATIONS: 2-3 actionable recommendations for career advancement

== DETAILS ==
6. ACTIVITY & THOUGHT LEADERSHIP: Analyze their LinkedIn posts and activity level in detail - what specific topics they post about, their expertise areas demonstrated through posts, quality of content, engagement levels (likes/comments/reposts), how well they communicate complex topics, their thought leadership in their field, and how their posts reflect their professional knowledge and industry involvement. If posts are in other languages, note the language and translate key concepts.
7. SKILLS ASSESSMENT: Evaluation of their technical and professional skills
8. PROJECTS HIGHLIGHTS: Most impressive or relevant projects (if any)
9. CERTIFICATIONS VALUE: Assessment of their certifications and professional development
10. EDUCATION BACKGROUND: Analysis of their educational qualifications

Please provide a structured, professional analysis that would be valuable for career planning, networking, or recruitment purposes. Use high reasoning effort to provide deep insights and comprehensive analysis. Follow the exact section order specified above."""

        user_prompt = f"""Please analyze this LinkedIn profile data and provide a comprehensive professional summary:

{profile_text}

Please structure your response clearly with the 11 sections mentioned in the system prompt, starting with a compelling HEADLINE, then the OVERALL RATING section with detailed score breakdown, then following the EXACT order: Summary sections (Professional Summary, Key Strengths, Career Trajectory, Career Recommendations), then Details sections (Activity, Skills, Projects, Certifications, Education)."""

        if DEBUG:
            print("Sending request to ChatGPT ...")
            print(f"Profile text length: {len(profile_text)} characters")
        
        # Make API call
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=2000,
            temperature=0.3
        )
        
        analysis = response.choices[0].message.content
        
        if DEBUG:
            print(f"Received response: {len(analysis)} characters")
        
        return analysis
        
    except Exception as e:
        print(f"Error calling ChatGPT API: {e}")
        print("\nPossible solutions:")
        print("1. Check your OpenAI API key")
        print("2. Ensure you have sufficient API credits")
        print("3. Check your internet connection")
        sys.exit(1)


def analyze_with_ollama(profile_text, model, base_url):
    """Send profile data to Ollama for local analysis"""

    # Same prompts as ChatGPT for consistency
    system_prompt = """You are a professional LinkedIn profile analyzer and career consultant.
Analyze the provided LinkedIn profile data and provide a comprehensive, professional summary in this EXACT order:

0. HEADLINE: One compelling, short line (max 10-12 words) that best defines this person - could be a professional tagline, a poetic sentence, or a catchy phrase that captures their essence and expertise

1. OVERALL RATING: Provide a comprehensive professional score out of 100 and detailed evaluation. Format it as:
   📊 OVERALL PROFESSIONAL RATING: [Score]/100

   Then provide a detailed breakdown explaining the score based on these 6 criteria with weighted importance:
   *  Professional experience depth and relevance: [Score]/25 (Most Important)
   *  Skills diversity and market demand: [Score]/20 (Very Important)
   *  Profile completeness and presentation quality: [Score]/15 (Important)
   *  Activity and thought leadership presence: [Score]/15 (Important)
   *  Education and certifications value: [Score]/15 (Important)
   *  Career trajectory and growth potential: [Score]/10 (Moderately Important)

   Calculate the total score by adding all 6 sections (Total: 100 points). Include specific strengths that contributed to the score and areas for improvement.

== SUMMARY ==
2. PROFESSIONAL SUMMARY: A 2-3 sentence overview of the person's career focus and expertise
3. KEY STRENGTHS: Top 3-4 professional strengths based on experience and skills
4. CAREER TRAJECTORY: Analysis of their career progression and growth
5. CAREER RECOMMENDATIONS: 2-3 actionable recommendations for career advancement

== DETAILS ==
6. ACTIVITY & THOUGHT LEADERSHIP: Analyze their LinkedIn posts and activity level in detail
7. SKILLS ASSESSMENT: Evaluation of their technical and professional skills
8. PROJECTS HIGHLIGHTS: Most impressive or relevant projects (if any)
9. CERTIFICATIONS VALUE: Assessment of their certifications and professional development
10. EDUCATION BACKGROUND: Analysis of their educational qualifications

Please provide a structured, professional analysis."""

    user_prompt = f"""Please analyze this LinkedIn profile data and provide a comprehensive professional summary:

{profile_text}

Please structure your response clearly with the 11 sections mentioned, starting with a compelling HEADLINE, then the OVERALL RATING section with detailed score breakdown."""

    try:
        if DEBUG:
            print(f"Sending request to Ollama at {base_url} using model {model}...")
            print(f"Profile text length: {len(profile_text)} characters")

        # Ollama API endpoint
        url = f"{base_url}/api/chat"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False
        }

        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()

        result = response.json()
        analysis = result.get('message', {}).get('content', '')

        if not analysis:
            print("Error: Empty response from Ollama")
            sys.exit(1)

        if DEBUG:
            print(f"Received response: {len(analysis)} characters")

        return analysis

    except requests.exceptions.ConnectionError:
        print(f"Error: Cannot connect to Ollama at {base_url}")
        print("\nPossible solutions:")
        print("1. Make sure Ollama is running: ollama serve")
        print("2. Check if the model is installed: ollama list")
        print(f"3. Pull the model if needed: ollama pull {model}")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("Error: Ollama request timed out (>5 minutes)")
        print("Try a smaller/faster model or check system resources")
        sys.exit(1)
    except Exception as e:
        print(f"Error calling Ollama API: {e}")
        sys.exit(1)


def analyze_profile(profile_text, config):
    """Analyze profile using enabled AI providers with fallback support.

    Logic:
    - Tries providers in order: openai, ollama
    - Uses only enabled providers (enabled: true)
    - If first provider fails, tries the next enabled one
    """
    providers = config.get('providers', {})

    # Get list of enabled providers in priority order
    provider_order = ['openai', 'ollama']
    enabled_providers = [p for p in provider_order if providers.get(p, {}).get('enabled', False)]

    if not enabled_providers:
        print("Error: No AI providers are enabled in model_config.json")
        print("Set 'enabled': true for at least one provider")
        sys.exit(1)

    last_error = None

    for provider_name in enabled_providers:
        provider_config = providers[provider_name]
        model = provider_config.get('model', '')

        try:
            if provider_name == 'openai':
                api_key = get_api_key(provider_config.get('api_key_env', 'OPENAI_API_KEY'))
                print(f"🤖 Analyzing profile with OpenAI ({model})...")
                return analyze_with_chatgpt(profile_text, api_key, model)

            elif provider_name == 'ollama':
                base_url = provider_config.get('base_url', 'http://localhost:11434')
                print(f"🤖 Analyzing profile with Ollama ({model})...")
                return analyze_with_ollama(profile_text, model, base_url)

        except SystemExit:
            # Re-raise if this is the last provider
            if provider_name == enabled_providers[-1]:
                raise
            # Otherwise try next provider
            print(f"⚠️  {provider_name} failed, trying next provider...")
            continue
        except Exception as e:
            last_error = str(e)
            if provider_name == enabled_providers[-1]:
                print(f"Error: All providers failed. Last error: {last_error}")
                sys.exit(1)
            print(f"⚠️  {provider_name} failed ({e}), trying next provider...")
            continue

    print("Error: All AI providers failed")
    sys.exit(1)


def get_api_key(env_var='OPENAI_API_KEY'):
    """Get OpenAI API key from environment variable or user input"""

    # Try environment variable first
    api_key = os.getenv(env_var)
    
    if api_key:
        if DEBUG:
            print("Using API key from environment variable OPENAI_API_KEY")
        return api_key
    
    # Ask user for API key
    print("OpenAI API key not found in environment variables.")
    print("Please enter your OpenAI API key:")
    api_key = input("> ").strip()
    
    if not api_key:
        print("Error: No API key provided")
        print("\nTo set up your API key:")
        print("1. Get your API key from: https://platform.openai.com/api-keys")
        print("2. Set environment variable: export OPENAI_API_KEY='your-key-here'")
        print("3. Or provide it when prompted")
        sys.exit(1)
    
    return api_key

def format_analysis_for_html(analysis_text):
    """Format the analysis text for better HTML display with color-coded scores"""
    
    # Define score thresholds for color coding
    score_thresholds = {
        'Professional experience depth and relevance': 12.5,  # Half of 25
        'Skills diversity and market demand': 10,  # Half of 20
        'Profile completeness and presentation quality': 7.5,  # Half of 15
        'Activity and thought leadership presence': 7.5,  # Half of 15
        'Education and certifications value': 7.5,  # Half of 15
        'Career trajectory and growth potential': 5  # Half of 10
    }
    
    import re
    
    lines = analysis_text.split('\n')
    html_parts = []
    
    # Find headline
    headline = ''
    for line in lines:
        if line.strip() and ('HEADLINE:' in line.upper() or line.strip().startswith('0.')):
            headline = re.sub(r'^(0\.\s*)?HEADLINE:\s*', '', line.strip(), flags=re.IGNORECASE)
            break
    
    if headline:
        html_parts.append(f'<div class="analysis-headline">{headline}</div>')
    
    # Parse sections
    current_section = None
    current_content = []
    in_summary = False
    in_details = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Skip headline since we already processed it
        if 'HEADLINE:' in line.upper() or line.startswith('0.'):
            continue
            
        # Check for section group markers
        if 'SUMMARY SECTIONS' in line.upper() or line.upper() == '== SUMMARY ==':
            if current_section and current_content:
                html_parts.append(format_section_html(current_section, current_content, score_thresholds, in_summary))
            html_parts.append('<div class="section-group-title">Summary</div>')
            in_summary = True
            in_details = False
            current_section = None
            current_content = []
            continue
            
        if 'DETAILS SECTIONS' in line.upper() or line.upper() == '== DETAILS ==':
            if current_section and current_content:
                html_parts.append(format_section_html(current_section, current_content, score_thresholds, in_summary))
            html_parts.append('<div class="section-group-title">Details</div>')
            in_summary = False
            in_details = True
            current_section = None
            current_content = []
            continue
        
        # Check for numbered section headers
        section_match = re.match(r'^(\d+)\.\s*([^:]+):\s*(.*)', line)
        if section_match:
            # Save previous section
            if current_section and current_content:
                html_parts.append(format_section_html(current_section, current_content, score_thresholds, in_summary))
            
            # Start new section
            current_section = section_match.group(2).strip()
            current_content = []
            
            # Add content if present on same line
            if section_match.group(3):
                current_content.append(section_match.group(3).strip())
        elif current_section and line:
            current_content.append(line)
    
    # Add last section
    if current_section and current_content:
        html_parts.append(format_section_html(current_section, current_content, score_thresholds, in_summary))
    
    return ''.join(html_parts)

def format_section_html(title, content_lines, score_thresholds, is_summary):
    """Format a single section as HTML"""
    import re
    
    # Get section icon
    icon_map = {
        'OVERALL RATING': 'fas fa-chart-bar',
        'PROFESSIONAL SUMMARY': 'fas fa-user-tie',
        'KEY STRENGTHS': 'fas fa-star',
        'CAREER TRAJECTORY': 'fas fa-chart-line',
        'CAREER RECOMMENDATIONS': 'fas fa-lightbulb',
        'ACTIVITY': 'fas fa-comments',
        'THOUGHT LEADERSHIP': 'fas fa-comments',
        'SKILLS ASSESSMENT': 'fas fa-cogs',
        'PROJECTS': 'fas fa-project-diagram',
        'CERTIFICATIONS': 'fas fa-certificate',
        'EDUCATION': 'fas fa-graduation-cap'
    }
    
    icon = 'fas fa-circle'
    for key, ico in icon_map.items():
        if key in title.upper():
            icon = ico
            break
    
    # Process content
    content_html = []
    
    for line in content_lines:
        # Handle overall professional rating line specially
        if 'OVERALL PROFESSIONAL RATING:' in line.upper():
            # Extract the score part
            rating_match = re.search(r'(\d+)/(\d+)', line)
            if rating_match:
                score = rating_match.group(1)
                max_score = rating_match.group(2)
                # Make the overall rating bold and centered with colorful score
                content_html.append(f'<div style="text-align: center; font-weight: bold; font-size: 1.1rem; margin: 0.5rem 0;">📊 OVERALL PROFESSIONAL RATING: <span style="color: #4a90a4; font-weight: bold;">{score}/{max_score}</span></div>')
                continue
        
        # Handle score lines with color coding
        score_colored = False
        for category, threshold in score_thresholds.items():
            pattern = rf'^[\*\-\•]?\s*{re.escape(category)}:\s*(\d+(?:\.\d+)?)/(\d+)'
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                score = float(match.group(1))
                max_score = int(match.group(2))
                color = '#28a745' if score > threshold else '#dc3545'  # Green if ABOVE half, red if AT or BELOW half
                content_html.append(f'<strong style="color: {color};">• {category}: {score}/{max_score}</strong>')
                score_colored = True
                break
        
        if not score_colored:
            # Convert * bullet points to HTML
            if line.startswith('*') or line.startswith('-') or line.startswith('•'):
                line = re.sub(r'^[\*\-\•]\s*', '• ', line)
                content_html.append(f'<strong>{line}</strong>')
            else:
                content_html.append(line)
    
    content = '<br>'.join(content_html)
    
    # Determine section class
    section_class = 'summary-section' if is_summary else 'activity-section'
    
    return f'''
    <div class="analysis-section {section_class}">
        <div class="section-title">
            <i class="{icon}"></i>
            {title}
        </div>
        <div class="section-content">{content}</div>
    </div>
    '''

def save_analysis(analysis, output_file):
    """Save the analysis to a file"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(analysis)
        print(f"\n✅ Analysis saved to: {output_file}")
    except Exception as e:
        print(f"Error saving analysis: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Analyze LinkedIn profile JSON data using ChatGPT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 profile_ai_assistant.py yaniv-haliwa.json
  python3 profile_ai_assistant.py profile.json --output analysis.txt
  python3 profile_ai_assistant.py profile.json --debug

Configuration:
  Edit model_config.json to choose AI provider (openai or ollama)

Environment Variables:
  OPENAI_API_KEY: Required when using OpenAI provider

Ollama Setup (local AI):
  1. Install Ollama: https://ollama.ai
  2. Pull a model: ollama pull llama3.2
  3. Set active_provider to "ollama" in model_config.json
        """
    )
    
    parser.add_argument('json_file', 
                       help='LinkedIn profile JSON file to analyze')
    
    parser.add_argument('--output', '-o',
                       help='Output file for analysis (default: {profile_name}_analysis.txt)')
    
    parser.add_argument('--debug', '-d',
                       action='store_true',
                       help='Enable debug output')
    
    args = parser.parse_args()
    
    global DEBUG
    DEBUG = args.debug
    
    if DEBUG:
        print(f"Debug mode enabled")
        print(f"Analyzing file: {args.json_file}")
    
    # Load profile data
    profile_data = load_profile_data(args.json_file)
    
    # Format data for analysis
    formatted_profile = format_profile_for_analysis(profile_data)
    
    if DEBUG:
        print(f"Formatted profile length: {len(formatted_profile)} characters")

    # Load model configuration
    config = load_model_config()

    # Analyze with configured AI provider
    analysis = analyze_profile(formatted_profile, config)
    
    # Determine output file
    if args.output:
        output_file = args.output
    else:
        # Create output filename based on input
        profile_name = profile_data.get('main_profile', {}).get('name', 'profile')
        # Clean filename
        safe_name = ''.join(c for c in profile_name if c.isalnum() or c in '-_ ').strip()
        safe_name = safe_name.replace(' ', '_')
        output_file = f"{safe_name}_analysis.txt"
    
    # Display analysis
    print("\n" + "="*80)
    print("🎯 LINKEDIN PROFILE ANALYSIS")
    print("="*80)
    print(analysis)
    print("="*80)
    
    # Save analysis
    save_analysis(analysis, output_file)
    
    print(f"\n🎉 Analysis complete! Check {output_file} for the full report.")

if __name__ == "__main__":
    main()
