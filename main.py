#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify, redirect, url_for
import subprocess
import json
import os
import time
import threading
import glob
from datetime import datetime
#version 26.7.25

DEBUG = False

app = Flask(__name__)

# Global variable to track analyzing status
analyzing_status = {}

def get_json_files():
    """Get all JSON files in the current directory"""
    json_files = []
    for file in glob.glob("*.json"):
        if os.path.isfile(file):
            # Get file stats
            stats = os.stat(file)
            mod_time = datetime.fromtimestamp(stats.st_mtime)
            file_size = stats.st_size
            
            json_files.append({
                'filename': file,
                'display_name': file.replace('.json', '').replace('-', ' ').title(),
                'modified': mod_time.strftime('%Y-%m-%d %H:%M:%S'),
                'size': f"{file_size:,} bytes"
            })
    
    # Sort by modification time (newest first)
    json_files.sort(key=lambda x: x['modified'], reverse=True)
    return json_files

def smart_load_data():
    """Smart loading: auto-load if 1 file, show browser if multiple"""
    json_files = get_json_files()
    
    if len(json_files) == 0:
        return None, 'no_files'
    elif len(json_files) == 1:
        return json_files[0]['filename'], 'auto_load'
    else:
        return json_files, 'multiple_files'

# Global variable to track analyzing status
analyzing_status = {}

def run_analyzer(username):
    """Run the LinkedIn analyzer in a background thread"""
    try:
        print(f"Starting analyzer for username: {username}")
        
        analyzing_status[username] = {
            'status': 'running',
            'progress': 10,
            'message': 'Starting profile analysis...'
        }
        
        # Run the analyzer
        cmd = ['python', 'profile_analyzer.py', username, '--save', f'{username}.json']
        
        if DEBUG:
            print(f"Running command: {' '.join(cmd)}")
        
        # Update progress
        analyzing_status[username]['progress'] = 30
        analyzing_status[username]['message'] = 'Loading LinkedIn page...'
        
        time.sleep(2)
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            analyzing_status[username] = {
                'status': 'completed',
                'progress': 100,
                'message': 'Profile analyzed successfully!',
                'output': result.stdout
            }
        else:
            analyzing_status[username] = {
                'status': 'error',
                'progress': 0,
                'message': f'Analysis failed: {result.stderr or result.stdout}',
                'error': result.stderr
            }
            
    except subprocess.TimeoutExpired:
        analyzing_status[username] = {
            'status': 'error',
            'progress': 0,
            'message': 'Analysis timed out after 5 minutes',
            'error': 'Timeout'
        }
            
    except Exception as e:
        analyzing_status[username] = {
            'status': 'error',
            'message': f'Error: {str(e)}',
            'progress': 0,
            'error': str(e)
        }

@app.route('/')
def index():
    """Main page with username input"""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def start_analyze():
    """Start the analyzing process"""
    username = request.form.get('username', '').strip()
    
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    
    # Clean username (remove any special characters or spaces)
    username = username.lower().replace(' ', '-').replace('@', '').replace('/', '')
    
    # Check if already analyzing
    if username in analyzing_status and analyzing_status[username]['status'] == 'running':
        return jsonify({'error': 'Already analyzing this profile'}), 400
    
    # Start analyzing in background thread
    thread = threading.Thread(target=run_analyzer, args=(username,))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'username': username,
        'linkedin_url': f'https://linkedin.com/in/{username}',
        'message': 'Analysis started...'
    })

@app.route('/status/<username>')
def get_status(username):
    """Get analyzing status for a username"""
    status = analyzing_status.get(username, {'status': 'not_found', 'message': 'No analyzing process found'})
    return jsonify(status)

@app.route('/test')
def test_with_existing_data():
    """Smart test route - auto-load if 1 file, show browser if multiple"""
    data, load_type = smart_load_data()
    
    if load_type == 'no_files':
        return render_template('error.html', 
                             error='No JSON files found', 
                             message='No profile data files found in the current directory. Please analyze a profile first.')
    
    elif load_type == 'auto_load':
        # Automatically load the single file
        username = data.replace('.json', '')
        return redirect(url_for('load_file', filename=data))
    
    elif load_type == 'multiple_files':
        # Show file browser
        return render_template('file_browser.html', files=data)

@app.route('/load/<filename>')
def load_file(filename):
    """Load a specific JSON file"""
    if not filename.endswith('.json'):
        filename += '.json'
    
    if not os.path.exists(filename):
        return render_template('error.html', 
                             error='File not found', 
                             message=f'File {filename} not found')
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        # Transform the data structure to match what the template expects
        profile_data = {
            'name': raw_data.get('main_profile', {}).get('name', 'Not available'),
            'headline': raw_data.get('main_profile', {}).get('headline', 'Not available'),
            'location': raw_data.get('main_profile', {}).get('location', 'Not available'),
            'about': raw_data.get('main_profile', {}).get('about', 'Not available'),
            'experience': raw_data.get('experience', []),  # Experience is now at top level
            'education': raw_data.get('education', []),
            'certifications': raw_data.get('certifications', []),
            'projects': raw_data.get('projects', []),
            'skills': raw_data.get('skills', []),
            'recent_activity': raw_data.get('recent_activity', [])
        }
        
        # Get file modification time
        mod_time = datetime.fromtimestamp(os.path.getmtime(filename))
        username = filename.replace('.json', '')
        
        # Try to get username from JSON data (more reliable)
        json_username = raw_data.get('username', username)
        
        return render_template('results.html', 
                             profile_data=profile_data, 
                             username=json_username,
                             analyzed_time=mod_time.strftime('%Y-%m-%d %H:%M:%S'))
    
    except Exception as e:
        return render_template('error.html', 
                             error='Error loading file', 
                             message=str(e))

@app.route('/test-direct')
def test_direct():
    """Direct test route that bypasses analyzing and shows existing data"""
    json_file = 'yaniv-haliwa.json'
    
    if not os.path.exists(json_file):
        return render_template('error.html', 
                             error='Test data not found', 
                             message='yaniv-haliwa.json file not found')
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        # Transform the data structure to match what the template expects
        profile_data = {
            'name': raw_data.get('main_profile', {}).get('name', 'Not available'),
            'headline': raw_data.get('main_profile', {}).get('headline', 'Not available'),
            'location': raw_data.get('main_profile', {}).get('location', 'Not available'),
            'about': raw_data.get('main_profile', {}).get('about', 'Not available'),
            'experience': raw_data.get('experience', []),  # Experience is now at top level
            'education': raw_data.get('education', []),
            'certifications': raw_data.get('certifications', []),
            'projects': raw_data.get('projects', []),
            'skills': raw_data.get('skills', []),
            'recent_activity': raw_data.get('recent_activity', [])
        }
        
        # Get file modification time
        mod_time = datetime.fromtimestamp(os.path.getmtime(json_file))
        
        # Try to get username from JSON data (more reliable)
        json_username = raw_data.get('username', 'yaniv-haliwa')
        
        return render_template('results.html', 
                             profile_data=profile_data, 
                             username=json_username,
                             analyzed_time=mod_time.strftime('%Y-%m-%d %H:%M:%S'))
    
    except Exception as e:
        return render_template('error.html', 
                             error='Error loading test data', 
                             message=str(e))

@app.route('/results/<username>')
def show_results(username):
    """Show the analyzed results"""
    json_file = f'{username}.json'
    
    if not os.path.exists(json_file):
        return render_template('error.html', 
                             error='Results not found', 
                             message=f'No data file found for {username}')
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        # Transform the data structure to match what the template expects
        profile_data = {
            'name': raw_data.get('main_profile', {}).get('name', 'Not available'),
            'headline': raw_data.get('main_profile', {}).get('headline', 'Not available'),
            'location': raw_data.get('main_profile', {}).get('location', 'Not available'),
            'about': raw_data.get('main_profile', {}).get('about', 'Not available'),
            'experience': raw_data.get('experience', []),  # Experience is now at top level
            'education': raw_data.get('education', []),
            'certifications': raw_data.get('certifications', []),
            'projects': raw_data.get('projects', []),
            'skills': raw_data.get('skills', []),
            'recent_activity': raw_data.get('recent_activity', [])
        }
        
        # Get file modification time
        mod_time = datetime.fromtimestamp(os.path.getmtime(json_file))
        
        # Try to get username from JSON data (more reliable)
        json_username = raw_data.get('username', username)
        
        return render_template('results.html', 
                             profile_data=profile_data, 
                             username=json_username,
                             analyzed_time=mod_time.strftime('%Y-%m-%d %H:%M:%S'))
    
    except Exception as e:
        return render_template('error.html', 
                             error='Error loading results', 
                             message=str(e))

@app.route('/api/profile/<username>')
def api_profile(username):
    """API endpoint to get profile data as JSON"""
    json_file = f'{username}.json'
    
    if not os.path.exists(json_file):
        return jsonify({'error': 'Profile data not found'}), 404
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        # Transform the data structure for API response
        profile_data = {
            'name': raw_data.get('main_profile', {}).get('name', 'Not available'),
            'headline': raw_data.get('main_profile', {}).get('headline', 'Not available'),
            'location': raw_data.get('main_profile', {}).get('location', 'Not available'),
            'about': raw_data.get('main_profile', {}).get('about', 'Not available'),
            'experience': raw_data.get('experience', []),  # Experience is now at top level
            'education': raw_data.get('education', []),
            'certifications': raw_data.get('certifications', []),
            'projects': raw_data.get('projects', []),
            'skills': raw_data.get('skills', []),
            'recent_activity': raw_data.get('recent_activity', [])
        }
        
        return jsonify(profile_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

from profile_ai_assistant import format_analysis_for_html

@app.route('/analyze/<username>')
def analyze_profile(username):
    """Run AI analysis on a profile"""
    json_file = f'{username}.json'
    
    if not os.path.exists(json_file):
        return jsonify({'error': f'Profile data not found for {username}'}), 404
    
    try:
        # Run the profile AI assistant
        cmd = ['python3', 'profile_ai_assistant.py', json_file]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode != 0:
            return jsonify({'error': f'Analysis failed: {result.stderr}'}), 500
        
        # Find the generated analysis file
        analysis_files = glob.glob(f'*{username}*_analysis.txt') + glob.glob('*_analysis.txt')
        
        if not analysis_files:
            return jsonify({'error': 'Analysis file not found'}), 500
        
        # Read the most recent analysis file
        analysis_file = max(analysis_files, key=os.path.getctime)
        
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis_content = f.read()
        
        # Format the analysis for HTML display with color-coded scores
        formatted_analysis = format_analysis_for_html(analysis_content)
        
        # Parse the analysis content to extract sections
        sections = parse_analysis_content(analysis_content)
        
        return jsonify({
            'success': True,
            'analysis': formatted_analysis,
            'sections': sections,
            'file': analysis_file
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def parse_analysis_content(content):
    """Parse analysis content into structured sections"""
    sections = {}
    lines = content.split('\n')
    current_section = None
    current_content = []
    
    for line in lines:
        line = line.strip()
        
        # Check if this is a section header (starts with ### or **)
        if line.startswith('###') or (line.startswith('**') and line.endswith('**')):
            # Save previous section
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            
            # Start new section
            current_section = line.replace('###', '').replace('**', '').replace(':', '').strip()
            current_content = []
        elif current_section:
            current_content.append(line)
    
    # Save last section
    if current_section and current_content:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
