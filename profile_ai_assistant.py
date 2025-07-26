#!/usr/bin/env python3
import json
import argparse
import sys
import os
from openai import OpenAI
#version 26.7.25

DEBUG = False

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

def analyze_with_chatgpt(profile_text, api_key):
    """Send profile data to ChatGPTfor analysis"""
    
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
            model="gpt-4o",
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

def get_api_key():
    """Get OpenAI API key from environment variable or user input"""
    
    # Try environment variable first
    api_key = os.getenv('OPENAI_API_KEY')
    
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
    """Format the analysis text for better HTML display with consistent formatting matching Template 2"""
    
    import re
    
    # Define score thresholds for color coding
    score_thresholds = {
        'Professional experience depth and relevance': 12.5,  # Half of 25
        'Skills diversity and market demand': 10,  # Half of 20
        'Profile completeness and presentation quality': 7.5,  # Half of 15
        'Activity and thought leadership presence': 7.5,  # Half of 15
        'Education and certifications value': 7.5,  # Half of 15
        'Career trajectory and growth potential': 5  # Half of 10
    }
    
    html_parts = []
    
    # Extract sections using multiple patterns to handle AI inconsistency
    sections = extract_sections_from_text(analysis_text)
    
    # Format headline if present - clean styling like Template 2
    if 'headline' in sections:
        clean_headline = clean_content_for_template(sections["headline"])
        html_parts.append(f'<div class="headline">{clean_headline}</div>')
    
    # Format overall rating with score breakdown (keep this as you like it)
    if 'overall_rating' in sections:
        html_parts.append(format_overall_rating_html(sections['overall_rating'], score_thresholds))
    
    # Summary sections - with Template 2 styling
    html_parts.append('<div class="section-group-title">Summary</div>')
    
    summary_sections = ['professional_summary', 'key_strengths', 'career_trajectory', 'career_recommendations']
    for section_key in summary_sections:
        if section_key in sections:
            section_title = format_section_title(section_key)
            html_parts.append(format_standard_section_html(section_title, sections[section_key], section_key))
    
    # Details sections - with Template 2 styling
    html_parts.append('<div class="section-group-title">Details</div>')
    
    detail_sections = ['activity', 'skills_assessment', 'projects_highlights', 'certifications_value', 'education_background']
    for section_key in detail_sections:
        if section_key in sections:
            section_title = format_section_title(section_key)
            html_parts.append(format_standard_section_html(section_title, sections[section_key], section_key))
    
    return ''.join(html_parts)

def extract_sections_from_text(text):
    """Extract structured sections from AI response text using multiple patterns"""
    import re
    
    sections = {}
    lines = text.split('\n')
    
    # Try to extract headline (multiple patterns)
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Pattern 1: "**0. HEADLINE:** content" or "HEADLINE:" content
        headline_match = re.match(r'^\*\*(?:0\.\s*)?HEADLINE:\*\*\s*(.+)', line, re.IGNORECASE)
        if headline_match:
            sections['headline'] = headline_match.group(1).strip()
            break
        
        # Pattern 2: "0. HEADLINE:" without markdown
        headline_match2 = re.match(r'^(?:0\.\s*)?HEADLINE:\s*(.+)', line, re.IGNORECASE)
        if headline_match2:
            sections['headline'] = headline_match2.group(1).strip()
            break
    
    # Extract sections using multiple patterns
    current_section = None
    current_content = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Skip headline
        if 'headline' in sections and sections['headline'] in line:
            continue
            
        # Pattern 1: Numbered sections with markdown (**1. SECTION:** content)
        numbered_match = re.match(r'^\*\*(\d+)\.\s*([^:*]+):\*\*\s*(.*)', line, re.IGNORECASE)
        if numbered_match:
            # Save previous section
            if current_section and current_content:
                sections[normalize_section_key(current_section)] = '\n'.join(current_content).strip()
            
            # Start new section
            current_section = numbered_match.group(2).strip()
            current_content = []
            if numbered_match.group(3):
                current_content.append(numbered_match.group(3).strip())
            continue
            
        # Pattern 2: Numbered sections without markdown (1. SECTION: content)
        numbered_match2 = re.match(r'^(\d+)\.\s*([^:]+):\s*(.*)', line, re.IGNORECASE)
        if numbered_match2:
            # Save previous section
            if current_section and current_content:
                sections[normalize_section_key(current_section)] = '\n'.join(current_content).strip()
            
            # Start new section
            current_section = numbered_match2.group(2).strip()
            current_content = []
            if numbered_match2.group(3):
                current_content.append(numbered_match2.group(3).strip())
            continue
        
        # Pattern 2: Section headers without numbers
        section_match = re.match(r'^([A-Z][A-Z\s&]+):\s*(.*)', line)
        if section_match and len(section_match.group(1).split()) <= 4:
            # Save previous section
            if current_section and current_content:
                sections[normalize_section_key(current_section)] = '\n'.join(current_content).strip()
            
            # Start new section
            current_section = section_match.group(1).strip()
            current_content = []
            if section_match.group(2):
                current_content.append(section_match.group(2).strip())
            continue
        
        # Pattern 3: Markdown headers (## Section)
        markdown_match = re.match(r'^#{1,3}\s*(.+)', line)
        if markdown_match:
            # Save previous section
            if current_section and current_content:
                sections[normalize_section_key(current_section)] = '\n'.join(current_content).strip()
            
            # Start new section
            current_section = markdown_match.group(1).strip()
            current_content = []
            continue
        
        # Add content to current section
        if current_section:
            current_content.append(line)
    
    # Save last section
    if current_section and current_content:
        sections[normalize_section_key(current_section)] = '\n'.join(current_content).strip()
    
    return sections

def normalize_section_key(section_title):
    """Convert section title to normalized key"""
    import re
    
    title_lower = section_title.lower()
    
    # Map various AI responses to our standardized keys
    if 'overall rating' in title_lower or 'professional rating' in title_lower or 'rating' in title_lower:
        return 'overall_rating'
    elif 'professional summary' in title_lower or 'summary' in title_lower:
        return 'professional_summary'
    elif 'key strengths' in title_lower or 'strengths' in title_lower:
        return 'key_strengths'
    elif 'career trajectory' in title_lower or 'trajectory' in title_lower or 'career progression' in title_lower:
        return 'career_trajectory'
    elif 'career recommendations' in title_lower or 'recommendations' in title_lower:
        return 'career_recommendations'
    elif 'activity' in title_lower or 'thought leadership' in title_lower:
        return 'activity'
    elif 'skills assessment' in title_lower or 'skills' in title_lower:
        return 'skills_assessment'
    elif 'projects' in title_lower or 'highlights' in title_lower:
        return 'projects_highlights'
    elif 'certifications' in title_lower or 'certificates' in title_lower:
        return 'certifications_value'
    elif 'education' in title_lower:
        return 'education_background'
    else:
        # Default: convert to snake_case
        return re.sub(r'[^a-zA-Z0-9]', '_', title_lower).strip('_')

def format_section_title(section_key):
    """Convert section key back to display title"""
    title_map = {
        'overall_rating': 'OVERALL RATING',
        'professional_summary': 'PROFESSIONAL SUMMARY',
        'key_strengths': 'KEY STRENGTHS',
        'career_trajectory': 'CAREER TRAJECTORY',
        'career_recommendations': 'CAREER RECOMMENDATIONS',
        'activity': 'ACTIVITY & THOUGHT LEADERSHIP',
        'skills_assessment': 'SKILLS ASSESSMENT',
        'projects_highlights': 'PROJECTS HIGHLIGHTS',
        'certifications_value': 'CERTIFICATIONS VALUE',
        'education_background': 'EDUCATION BACKGROUND'
    }
    return title_map.get(section_key, section_key.replace('_', ' ').title())

def format_overall_rating_html(content, score_thresholds):
    """Format the overall rating section with score breakdown and color coding"""
    import re
    
    # Extract overall score
    overall_score_match = re.search(r'(\d+)/100', content)
    overall_score = int(overall_score_match.group(1)) if overall_score_match else 0
    
    # Color code overall score
    overall_color = '#28a745' if overall_score > 50 else '#dc3545'
    
    html = f'''
    <div class="section-box">
        <div class="section-header">
            <span class="section-title">📊 OVERALL RATING</span>
        </div>
        <div class="section-content">
            <div class="overall-score">
                <h2 style="color: {overall_color}; margin: 0; font-size: 2.5em;">{overall_score}/100</h2>
                <p style="margin: 5px 0 0 0; font-weight: 600; color: #6c757d;">Overall Professional Rating</p>
            </div>
    '''
    
    # Parse content to extract scores with explanations
    lines = content.split('\n')
    score_items = []
    current_item = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Look for score lines
        if '/' in line and any(keyword in line.lower() for keyword in ['experience', 'skills', 'profile', 'activity', 'education', 'career']):
            # Save previous item
            if current_item:
                score_items.append(current_item)
            
            # Start new item
            score_match = re.search(r'(\d+)/(\d+)', line)
            if score_match:
                score = int(score_match.group(1))
                max_score = int(score_match.group(2))
                
                # Clean up the line text
                clean_line = re.sub(r'\*\s*', '', line)
                clean_line = re.sub(r'[•\-]\s*', '', clean_line)
                
                current_item = {
                    'title': clean_line,
                    'score': score,
                    'max_score': max_score,
                    'explanation': []
                }
        elif current_item and line and not line.startswith(('📊', 'Score Breakdown', 'SUMMARY')):
            # Add explanation to current item
            clean_explanation = re.sub(r'[•\-]\s*', '', line)
            if clean_explanation and not clean_explanation.lower().startswith(('overall', 'score')):
                current_item['explanation'].append(clean_explanation)
    
    # Save last item
    if current_item:
        score_items.append(current_item)
    
    # Generate score breakdown HTML
    if score_items:
        html += '<div class="score-breakdown"><h4 style="color: #495057; margin-bottom: 15px;">Score Breakdown:</h4>'
        
        for item in score_items:
            percentage = (item['score'] / item['max_score']) * 100
            color = '#28a745' if percentage > 50 else '#dc3545'
            
            html += f'''
            <div class="score-item">
                <div>
                    <div style="font-weight: 600; color: #495057; margin-bottom: 5px;">
                        <span style="color: {color};">●</span> {item['title']}
                    </div>
            '''
            
            # Add explanations if available
            if item['explanation']:
                html += '<div style="font-size: 0.9em; color: #6c757d; margin-left: 15px;">'
                for explanation in item['explanation']:
                    html += f'<div style="margin-bottom: 3px;">• {explanation}</div>'
                html += '</div>'
            
            html += '</div></div>'
        
        html += '</div>'
    
    # Add any additional summary content
    remaining_lines = []
    in_summary = False
    for line in lines:
        if 'SUMMARY' in line.upper() or 'summary' in line.lower():
            in_summary = True
            continue
        if in_summary and line.strip():
            remaining_lines.append(line.strip())
    
    if remaining_lines:
        html += f'<div class="rating-explanation" style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">'
        html += f'<h5 style="color: #495057; margin-bottom: 10px;">Summary:</h5>'
        for line in remaining_lines:
            if line and not line.startswith(('●', '•', '*')):
                html += f'<p style="margin-bottom: 8px; color: #6c757d;">{line}</p>'
        html += '</div>'
    
    html += '</div></div>'
    return html

def format_standard_section_html(title, content, section_key):
    """Format a standard section with consistent styling matching Template 2"""
    
    # Get section icon and emoji - exactly like Template 2
    icon_map = {
        'professional_summary': '👤',
        'key_strengths': '⭐',
        'career_trajectory': '📈',
        'career_recommendations': '💡',
        'activity': '💬',
        'skills_assessment': '🔧',
        'projects_highlights': '🚀',
        'certifications_value': '🏆',
        'education_background': '🎓'
    }
    
    icon = icon_map.get(section_key, '📋')
    
    # Determine section class based on whether it's summary or details
    is_summary = section_key in ['professional_summary', 'key_strengths', 'career_trajectory', 'career_recommendations']
    section_class = 'summary-section' if is_summary else 'details-section'
    
    # Clean and format content - remove ALL markdown formatting
    clean_content = clean_content_for_template(content)
    
    # Generate HTML exactly like Template 2
    html = f'''
        <div class="section {section_class}">
            <div class="section-title">{icon} {title}</div>
            <div class="section-content">{clean_content}</div>
        </div>
    '''
    
    return html

def clean_content_for_template(content):
    """Clean content to match Template 2 - remove all markdown and formatting"""
    import re
    
    if not content or not content.strip():
        return 'No information available.'
    
    # Clean up the text
    text = content.strip()
    
    # Remove ALL markdown formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove **bold**
    text = re.sub(r'__(.*?)__', r'\1', text)      # Remove __bold__
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Remove *italic*
    text = re.sub(r'==(.*?)==', r'\1', text)      # Remove ==sections==
    
    # Remove bullet point markers but keep the content
    text = re.sub(r'^\s*[•\-\*]\s*', '', text, flags=re.MULTILINE)
    
    # Split into clean paragraphs
    paragraphs = text.split('\n\n')
    formatted_paragraphs = []
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        # Check if it's a list (multiple lines with similar structure)
        lines = para.split('\n')
        if len(lines) > 1:
            # Clean each line and join with <br>
            clean_lines = []
            for line in lines:
                line = line.strip()
                if line:
                    # Remove any remaining bullet markers
                    line = re.sub(r'^[•\-\*]\s*', '', line)
                    clean_lines.append(line)
            
            if clean_lines:
                # Join with line breaks for lists
                formatted_paragraphs.append('<br>'.join(clean_lines))
        else:
            # Single paragraph
            formatted_paragraphs.append(para)
    
    return '<br><br>'.join(formatted_paragraphs) if formatted_paragraphs else content

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
  python3 profile_analyzer.py yaniv-haliwa.json
  python3 profile_analyzer.py adrianzoren.json --output analysis.txt
  python3 profile_analyzer.py profile.json --debug

Environment Variables:
  OPENAI_API_KEY: Your OpenAI API key (recommended)
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
    
    # Get API key
    api_key = get_api_key()
    
    # Analyze with ChatGPT
    print("🤖 Analyzing profile with ChatGPT...")
    analysis = analyze_with_chatgpt(formatted_profile, api_key)
    
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
