#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import time
import json
import re
import subprocess
import os
import glob
import tempfile
import shutil
import html
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
#version 26.7.25

DEBUG = False

def get_default_browser():
    """Detect user's default browser with exact version and variant"""
    browser_info = {'type': None, 'variant': None, 'executable': None, 'version': None}
    
    try:
        # Get default browser using xdg-settings
        result = subprocess.run(['xdg-settings', 'get', 'default-web-browser'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            browser_desktop = result.stdout.strip()
            if DEBUG:
                print(f"Default browser desktop file: {browser_desktop}")
            
            # Parse desktop file to get more details
            desktop_file_path = f"/usr/share/applications/{browser_desktop}"
            if os.path.exists(desktop_file_path):
                with open(desktop_file_path, 'r') as f:
                    content = f.read()
                    exec_line = re.search(r'Exec=([^\n]+)', content)
                    if exec_line:
                        executable = exec_line.group(1).split()[0]
                        browser_info['executable'] = executable
                        if DEBUG:
                            print(f"Found executable from desktop file: {executable}")
                        
                        # Determine browser type and variant from desktop file
                        if 'firefox' in browser_desktop.lower():
                            browser_info['type'] = 'firefox'
                            if 'devedition' in browser_desktop.lower() or 'developer' in browser_desktop.lower():
                                browser_info['variant'] = 'developer'
                            elif 'nightly' in browser_desktop.lower():
                                browser_info['variant'] = 'nightly'
                            elif 'beta' in browser_desktop.lower():
                                browser_info['variant'] = 'beta'
                            elif 'esr' in browser_desktop.lower():
                                browser_info['variant'] = 'esr'
                            else:
                                browser_info['variant'] = 'stable'
                                
                            # Get version
                            try:
                                version_result = subprocess.run([executable, '--version'], 
                                                              capture_output=True, text=True)
                                browser_info['version'] = version_result.stdout.strip()
                            except:
                                pass
                            
                            if DEBUG:
                                print(f"Detected from desktop file: {browser_info}")
                                
                            return browser_info
    except Exception as e:
        if DEBUG:
            print(f"Error reading desktop file: {e}")
    
    # Check for specific browser variants
    browsers_to_check = [
        # Firefox variants
        'firefox-developer-edition', 'firefox-dev', 'firefox-developer',
        'firefox-nightly', 'firefox-beta', 'firefox-esr', 'firefox',
        # Chrome variants  
        'google-chrome-unstable', 'google-chrome-beta', 'google-chrome-stable', 'google-chrome',
        'chromium-browser', 'chromium',
        # Brave variants
        'brave-browser-dev', 'brave-browser-beta', 'brave-browser-nightly', 'brave-browser',
        # Edge variants
        'microsoft-edge-dev', 'microsoft-edge-beta', 'microsoft-edge'
    ]
    
    for browser in browsers_to_check:
        try:
            result = subprocess.run(['which', browser], check=True, capture_output=True, text=True)
            executable_path = result.stdout.strip()
            
            # Get version
            try:
                if 'firefox' in browser:
                    version_result = subprocess.run([executable_path, '--version'], 
                                                  capture_output=True, text=True)
                    version = version_result.stdout.strip()
                    browser_info['type'] = 'firefox'
                    if 'developer' in browser or 'dev' in browser:
                        browser_info['variant'] = 'developer'
                    elif 'nightly' in browser:
                        browser_info['variant'] = 'nightly'  
                    elif 'beta' in browser:
                        browser_info['variant'] = 'beta'
                    elif 'esr' in browser:
                        browser_info['variant'] = 'esr'
                    else:
                        browser_info['variant'] = 'stable'
                        
                elif 'chrome' in browser:
                    version_result = subprocess.run([executable_path, '--version'], 
                                                  capture_output=True, text=True)
                    version = version_result.stdout.strip()
                    browser_info['type'] = 'chrome'
                    if 'unstable' in browser:
                        browser_info['variant'] = 'canary'
                    elif 'beta' in browser:
                        browser_info['variant'] = 'beta'
                    else:
                        browser_info['variant'] = 'stable'
                        
                elif 'brave' in browser:
                    version_result = subprocess.run([executable_path, '--version'], 
                                                  capture_output=True, text=True)
                    version = version_result.stdout.strip()
                    browser_info['type'] = 'brave'
                    if 'dev' in browser:
                        browser_info['variant'] = 'dev'
                    elif 'beta' in browser:
                        browser_info['variant'] = 'beta'
                    elif 'nightly' in browser:
                        browser_info['variant'] = 'nightly'
                    else:
                        browser_info['variant'] = 'stable'
                
                browser_info['executable'] = executable_path
                browser_info['version'] = version
                
                if DEBUG:
                    print(f"Found browser: {browser_info}")
                
                # If this matches the default browser, use it
                if browser_info['executable'] and browser_info['executable'] in str(browser_info.get('executable', '')):
                    return browser_info
                    
                # Return first found if no default detected
                if not browser_info.get('type'):
                    return browser_info
                    
            except Exception as e:
                if DEBUG:
                    print(f"Error getting version for {browser}: {e}")
                continue
                
        except subprocess.CalledProcessError:
            continue
    
    # Default fallback
    if DEBUG:
        print("Could not detect browser, using Firefox as fallback")
    return {'type': 'firefox', 'variant': 'stable', 'executable': 'firefox', 'version': None}

def find_browser_profile(browser_info):
    """Find user's browser profile directory based on browser info"""
    browser_type = browser_info['type']
    variant = browser_info['variant']
    
    if browser_type == 'firefox':
        # Firefox profile locations based on variant
        if variant == 'developer':
            profile_paths = [
                os.path.expanduser("~/.mozilla/firefox-developer-edition/"),
                os.path.expanduser("~/.mozilla/firefox/"),
            ]
            
            # Look specifically for dev-edition-default profiles
            base_path = os.path.expanduser("~/.mozilla/firefox/")
            if os.path.exists(base_path):
                dev_profiles = glob.glob(os.path.join(base_path, "*.dev-edition-default"))
                if dev_profiles:
                    if DEBUG:
                        print(f"Found Firefox Developer Edition profile: {dev_profiles[0]}")
                    return dev_profiles[0]
        elif variant == 'nightly':
            profile_paths = [
                os.path.expanduser("~/.mozilla/firefox-nightly/"),
                os.path.expanduser("~/.mozilla/firefox/"),
            ]
        elif variant == 'beta':
            profile_paths = [
                os.path.expanduser("~/.mozilla/firefox-beta/"),
                os.path.expanduser("~/.mozilla/firefox/"),
            ]
        else:
            profile_paths = [
                os.path.expanduser("~/.mozilla/firefox/"),
                os.path.expanduser("~/snap/firefox/common/.mozilla/firefox/"),
                os.path.expanduser("~/.var/app/org.mozilla.firefox/.mozilla/firefox/")
            ]
        
        for base_path in profile_paths:
            if os.path.exists(base_path):
                # Look for default profile
                profiles = glob.glob(os.path.join(base_path, "*.default*"))
                if profiles:
                    if DEBUG:
                        print(f"Found Firefox {variant} profile: {profiles[0]}")
                    return profiles[0]
    
    elif browser_type == 'chrome':
        # Chrome profile locations based on variant
        if variant == 'canary':
            profile_paths = [
                os.path.expanduser("~/.config/google-chrome-unstable/Default"),
            ]
        elif variant == 'beta':
            profile_paths = [
                os.path.expanduser("~/.config/google-chrome-beta/Default"),
            ]
        else:
            profile_paths = [
                os.path.expanduser("~/.config/google-chrome/Default"),
                os.path.expanduser("~/.config/chromium/Default"),
                os.path.expanduser("~/snap/chromium/common/chromium/Default")
            ]
        
        for profile_path in profile_paths:
            if os.path.exists(profile_path):
                if DEBUG:
                    print(f"Found Chrome {variant} profile: {profile_path}")
                return profile_path
    
    elif browser_type == 'brave':
        # Brave profile locations
        profile_paths = [
            os.path.expanduser("~/.config/BraveSoftware/Brave-Browser/Default"),
            os.path.expanduser("~/.config/BraveSoftware/Brave-Browser-Dev/Default"),
            os.path.expanduser("~/.config/BraveSoftware/Brave-Browser-Beta/Default"),
        ]
        
        for profile_path in profile_paths:
            if os.path.exists(profile_path):
                if DEBUG:
                    print(f"Found Brave {variant} profile: {profile_path}")
                return profile_path
    
    if DEBUG:
        print(f"No {browser_type} {variant} profile found")
    return None

def start_firefox_with_profile():
    """Start Firefox Developer Edition with your profile and remote debugging

    Profile path is determined by:
    1. FIREFOX_PROFILE_PATH environment variable (if set)
    2. Auto-detection via find_browser_profile()
    """
    try:
        # Get profile path from environment or auto-detect
        browser_info = get_default_browser()
        profile_path = os.environ.get('FIREFOX_PROFILE_PATH') or find_browser_profile(browser_info)

        if not profile_path or not os.path.exists(profile_path):
            if DEBUG:
                print("No valid Firefox profile found. Set FIREFOX_PROFILE_PATH environment variable.")
            return None
        
        if DEBUG:
            print(f"Starting Firefox Developer Edition with profile: {profile_path}")
        
        # Start Firefox with remote debugging and your profile
        cmd = [
            'firefox-devedition',
            '--marionette',
            '--profile', profile_path,
            '--remote-debugging-port=9222'
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5)  # Give Firefox time to start
        
        # Now connect to it
        firefox_options = FirefoxOptions()
        firefox_options.add_argument("--marionette")
        
        # Try to connect
        driver = webdriver.Remote(
            command_executor='http://localhost:4444',
            options=firefox_options
        )
        
        if DEBUG:
            print("Connected to Firefox with your profile!")
        
        return driver
        
    except Exception as e:
        if DEBUG:
            print(f"Could not start/connect to Firefox: {e}")
        return None

def setup_driver(headless=True):
    """Set up WebDriver using user's default browser and profile
    
    Args:
        headless (bool): Whether to run in headless mode
    """
    # First try to start Firefox with your profile
    if not headless:
        firefox_driver = start_firefox_with_profile()
        if firefox_driver:
            return firefox_driver
    
    # Detect default browser
    browser_info = get_default_browser()
    if DEBUG:
        print(f"Using browser: {browser_info['type']} {browser_info['variant']} ({browser_info['version']})")
        print(f"Executable: {browser_info['executable']}")

    # Get profile path from environment variable or auto-detect
    profile_path = os.environ.get('FIREFOX_PROFILE_PATH') or find_browser_profile(browser_info)
    
    if browser_info['type'] == 'firefox':
        firefox_options = FirefoxOptions()
        
        # Set preferences to avoid detection FIRST
        firefox_options.set_preference("dom.webdriver.enabled", False)
        firefox_options.set_preference("useAutomationExtension", False)
        
        # Use headless mode only if specified (back to simple working version)
        if headless:
            firefox_options.add_argument("--headless")
        
        # Handle profile for headless vs non-headless differently
        if profile_path:
            if DEBUG:
                print(f"Setting Firefox profile: {profile_path}")
            
            # For headless mode, try using profile with --no-remote to avoid conflicts
            if headless:
                firefox_options.add_argument("--no-remote")
                firefox_options.add_argument("--new-instance")
                
                # Check if Firefox is already running with this profile
                try:
                    # Check for .parentlock file (Firefox creates this when using a profile)
                    parentlock_file = os.path.join(profile_path, '.parentlock')
                    if os.path.exists(parentlock_file):
                        if DEBUG:
                            print("Firefox is already running with this profile (.parentlock exists) - using session copy method")
                        
                        # Copy essential session files to temp profile for headless
                        import tempfile
                        import shutil
                        import os
                        
                        temp_profile = tempfile.mkdtemp(prefix="firefox_headless_")
                        if DEBUG:
                            print(f"Created temp profile for headless: {temp_profile}")
                        
                        # Copy essential files for session persistence
                        essential_files = [
                            'cookies.sqlite', 'webappsstore.sqlite', 'permissions.sqlite',
                            'content-prefs.sqlite', 'prefs.js'
                        ]
                        
                        for filename in essential_files:
                            src = os.path.join(profile_path, filename)
                            dst = os.path.join(temp_profile, filename)
                            if os.path.exists(src):
                                try:
                                    shutil.copy2(src, dst)
                                    if DEBUG:
                                        print(f"Copied {filename} to temp profile")
                                except Exception as e:
                                    if DEBUG:
                                        print(f"Could not copy {filename}: {e}")
                        
                        # Use temp profile for headless
                        firefox_options.add_argument("--profile")
                        firefox_options.add_argument(temp_profile)
                    else:
                        # Firefox not running with this profile, safe to use directly
                        firefox_options.add_argument("--profile")
                        firefox_options.add_argument(profile_path)
                except Exception as e:
                    if DEBUG:
                        print(f"Could not check running processes: {e}")
                    # Fallback to direct profile usage
                    firefox_options.add_argument("--profile")
                    firefox_options.add_argument(profile_path)
            else:
                # Non-headless mode - use profile directly
                firefox_options.add_argument("--profile")
                firefox_options.add_argument(profile_path)
            
            # Check if profile has existing session
            import os
            prefs_file = os.path.join(profile_path, "prefs.js")
            if os.path.exists(prefs_file):
                if DEBUG:
                    print("Found existing prefs.js, profile should have login session")
        else:
            if DEBUG:
                print("No Firefox profile found, using default")
        
        # Basic window settings
        firefox_options.add_argument("--width=1920")
        firefox_options.add_argument("--height=1080")
        
        try:
            # Use specific Firefox executable if found
            if browser_info['executable']:
                # Handle different Firefox executable names
                if 'firefox-devedition' in browser_info['executable']:
                    # Try different possible paths for Firefox Developer Edition
                    possible_paths = [
                        '/usr/bin/firefox-devedition',
                        '/usr/bin/firefox-developer-edition', 
                        '/opt/firefox-dev/firefox',
                        browser_info['executable']
                    ]
                    
                    import os
                    firefox_binary = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            firefox_binary = path
                            break
                    
                    if firefox_binary:
                        firefox_options.binary_location = firefox_binary
                        if DEBUG:
                            print(f"Using Firefox Developer Edition binary: {firefox_binary}")
                    else:
                        if DEBUG:
                            print("Firefox Developer Edition binary not found, using default")
                else:
                    firefox_options.binary_location = browser_info['executable']
                    if DEBUG:
                        print(f"Using Firefox binary: {browser_info['executable']}")
            
            # Try to start Firefox WebDriver (back to simple working version)
            driver = webdriver.Firefox(options=firefox_options)
            if DEBUG:
                print(f"Firefox {browser_info['variant']} WebDriver started successfully")
            return driver
            
        except Exception as e:
            if DEBUG:
                print(f"Firefox WebDriver failed with error: {e}")
                print(f"Full error details: {str(e)}")
            raise Exception(f"Firefox WebDriver could not be started: {e}")

def extract_main_profile(soup):
    """Extract main profile information"""
    profile_data = {}
    
    try:
        # Debug: Print page title to see what we're getting
        title_elem = soup.select_one("title")
        if DEBUG:
            print(f"Page title: {title_elem.text if title_elem else 'No title'}")
        
        # Check if we're on login page
        if title_elem and ("Join LinkedIn" in title_elem.text or "Sign in" in title_elem.text):
            if DEBUG:
                print("Detected login page - LinkedIn requires authentication")
            profile_data['error'] = "Authentication required - LinkedIn redirected to login"
            return profile_data
        
        # Extract name from title or main profile heading
        if title_elem and " | LinkedIn" in title_elem.text:
            profile_data['name'] = title_elem.text.replace(" | LinkedIn", "").strip()
            if DEBUG:
                print(f"Found name from title: {profile_data['name']}")
        else:
            # Fallback selectors for name
            name_selectors = [
                "h1.text-heading-xlarge",
                "h1.text-heading-large", 
                "div.ph5 h1",
                "section.artdeco-card h1",
                ".pv-text-details__left-panel h1",
                "main h1",
                "h1"
            ]
            
            name_elem = None
            for selector in name_selectors:
                name_elem = soup.select_one(selector)
                if name_elem and name_elem.text.strip() and "Join LinkedIn" not in name_elem.text:
                    if DEBUG:
                        print(f"Found name with selector: {selector}")
                    break
            
            profile_data['name'] = name_elem.text.strip() if name_elem else "Not available"
        
        # Extract headline from spans containing the full headline text - improved to get real headline
        headline_text = None
        
        # First try to find headline from JSON patterns that capture any meaningful content
        headline_patterns = [
            r'\[{"value":"([^"]{20,})"[^}]*}\]',  # Array value pattern for substantial content
            r'"headline":"([^"]{15,})"',  # Direct headline with meaningful length
            r'"occupation":"([^"]+)"',  # Alternative occupation field
        ]
        
        page_text = str(soup)
        for pattern in headline_patterns:
            matches = re.findall(pattern, page_text)
            if matches:
                for match in matches:
                    decoded_match = html.unescape(match).replace('&amp;', '&')
                    # Skip metadata strings, accept any meaningful headlines
                    if not any(x in decoded_match.lower() for x in [
                        'stringvalidationmetadata',
                        'com.linkedin.voyager',
                        'metadata',
                        'validation',
                        'error'
                    ]) and len(decoded_match) > 15:
                        headline_text = decoded_match
                        if DEBUG:
                            print(f"Found headline with pattern: {pattern[:30]}... -> {headline_text}")
                        break
                if headline_text:
                    break
        
        # If still no headline found, try visible spans with meaningful professional content
        if not headline_text:
            professional_spans = soup.find_all('span', {'aria-hidden': 'true'})
            for span in professional_spans:
                text = span.get_text(strip=True)
                # Look for spans with professional titles or roles (dynamic detection)
                if (text and len(text) > 15 and len(text) < 200 and 
                    any(indicator in text.lower() for indicator in ['|', 'developer', 'engineer', 'analyst', 'manager', 'specialist', 'consultant']) and
                    not any(skip in text.lower() for skip in ['click', 'button', 'show', 'expand', 'see more', 'connections'])):
                    headline_text = text
                    if DEBUG:
                        print(f"Found headline in professional span: {headline_text}")
                    break
        
        if not headline_text:
            # Fallback selectors for headline
            headline_selectors = [
                "div.text-body-medium.break-words",
                "div.pv-text-details__left-panel div.text-body-medium",
                ".ph5 div.text-body-medium",
                "section.artdeco-card div.text-body-medium", 
                "div.text-body-medium",
                ".pv-text-details__left-panel .text-body-medium"
            ]
            
            for selector in headline_selectors:
                headline_elem = soup.select_one(selector)
                if headline_elem and headline_elem.text.strip() and len(headline_elem.text.strip()) > 10:
                    headline_text = headline_elem.text.strip()
                    if DEBUG:
                        print(f"Found headline with selector: {selector}")
                    break
                    
        profile_data['headline'] = headline_text if headline_text else "Not available"
        
        # Extract location from JSON data or visible elements
        location_text = None
        location_patterns = [
            r'"defaultLocalizedName":"([^"]+)"',  # JSON location data
            r'"geoLocationName":"([^"]+)"',  # Alternative JSON location field
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, page_text)
            if match:
                location_text = match.group(1).strip()
                if location_text and len(location_text) > 2:
                    if DEBUG:
                        print(f"Found location with pattern: {pattern[:20]}...")
                    break
        
        if not location_text:
            # Fallback selectors for location
            location_selectors = [
                "span.text-body-small.inline.t-black--light.break-words",
                "div.pv-text-details__left-panel span.text-body-small",
                ".ph5 span.text-body-small",
                "section.artdeco-card span.text-body-small",
                "span.text-body-small",
                ".pv-text-details__left-panel .text-body-small"
            ]
            
            for selector in location_selectors:
                location_elem = soup.select_one(selector)
                if location_elem and location_elem.text.strip() and "connections" not in location_elem.text.lower():
                    location_text = location_elem.text.strip()
                    if DEBUG:
                        print(f"Found location with selector: {selector}")
                    break
                    
        profile_data['location'] = location_text if location_text else "Not available"
        
        # Extract About section from visible spans - improved pattern based on data2 analysis
        about_text = None
        
        # Look for inline-show-more-text containers first (most reliable pattern)
        about_containers = soup.find_all('div', class_=lambda x: x and 'inline-show-more-text' in x)
        for container in about_containers:
            about_span = container.find('span', {'aria-hidden': 'true'})
            if about_span:
                text = about_span.get_text(strip=True)
                # Check for meaningful about content (longer than typical button text)
                if text and len(text) > 50:
                    about_text = text
                    if DEBUG:
                        print(f"Found about section in inline-show-more-text: {text[:100]}...")
                    break
        
        # Fallback: Look for the about section content in spans with longer content
        if not about_text:
            about_spans = soup.find_all('span', {'aria-hidden': 'true'})
            for span in about_spans:
                text = span.get_text(strip=True)
                # Look for longer text content that could be an about section
                if text and len(text) > 100 and any(keyword in text.lower() for keyword in ['penetration', 'tester', 'automation', 'developer', 'security', 'experience', 'work', 'professional']):
                    about_text = text
                    if DEBUG:
                        print(f"Found about section in long span: {text[:100]}...")
                    break
                
        if not about_text:
            # Final fallback selectors for about
            about_selectors = [
                "div.pv-shared-text-with-see-more span[aria-hidden='true']",
                "section.artdeco-card.pv-about-section div.pv-shared-text-with-see-more span",
                "div.inline-show-more-text span[aria-hidden='true']",
                "div.pv-shared-text-with-see-more",
                "section[data-section='summary'] div",
                ".pv-about-section .pv-shared-text-with-see-more"
            ]
            
            for selector in about_selectors:
                about_elem = soup.select_one(selector)
                if about_elem and about_elem.text.strip():
                    about_text = about_elem.text.strip()
                    if DEBUG:
                        print(f"Found about with selector: {selector}")
                    break
                
        profile_data['about'] = about_text if about_text else "Not available"
        
        # Updated Experience selectors - handle multiple LinkedIn layout formats
        experience_items = []
        
        # Target different LinkedIn experience structures
        exp_sections = []
        
        # Strategy 1: Look for new LinkedIn format with specific classes
        experience_items_raw = soup.select("li.pvs-list__paged-list-item.artdeco-list__item.pvs-list__item--line-separated.pvs-list__item--one-column")
        
        if experience_items_raw:
            exp_sections = experience_items_raw
            if DEBUG:
                print(f"Found {len(exp_sections)} experience items using new LinkedIn structure")
        
        # Strategy 2: Look for older LinkedIn format or different layouts
        if not exp_sections:
            # Find all list items and filter by content structure
            all_items = soup.select("li.artdeco-list__item")
            exp_sections = []
            
            for item in all_items:
                # Check if this item has the proper experience structure
                classes = item.get('class', [])
                
                # Skip connection suggestions (they have random long class names)
                has_random_classes = any(len(cls) > 30 for cls in classes)
                if has_random_classes:
                    continue
                
                # Check for experience indicators
                has_job_title = item.select_one("div.mr1.hoverable-link-text.t-bold") or \
                               item.select_one("a span[aria-hidden='true']") or \
                               item.select_one("h3") or \
                               item.select_one(".t-16.t-black.t-bold")
                               
                has_company = item.select_one("span.t-14.t-normal") or \
                             item.select_one("span.t-14") or \
                             item.select_one("h4") or \
                             item.select_one(".t-14.t-black--light")
                             
                has_duration = item.select_one("span.pvs-entity__caption-wrapper") or \
                              item.select_one("span.t-14.t-black--light") or \
                              item.select_one("time") or \
                              item.select_one(".t-12.t-black--light")
                
                # Must have job title and either company or duration for work experience
                # More flexible - don't require specific classes, just content structure
                if has_job_title and (has_company or has_duration):
                    # Additional check - make sure text content looks like experience
                    item_text = item.get_text().strip().lower()
                    
                    # Skip if it's clearly not work experience
                    skip_patterns = [
                        'people you may know',
                        'connect',
                        'message',
                        'follow',
                        'view profile',
                        'mutual connection',
                        'see more',
                        'show more',
                        'view full profile'
                    ]
                    
                    is_not_experience = any(pattern in item_text for pattern in skip_patterns)
                    
                    # Must have substantial content and not be a suggestion
                    if not is_not_experience and len(item_text) > 20:
                        exp_sections.append(item)
                    
            if DEBUG:
                print(f"Found {len(exp_sections)} experience items using flexible strategy")
        
        # Strategy 3: Ultra fallback - look for any structured content that looks like experience
        if not exp_sections:
            # Look for any div/section that contains job title patterns
            potential_exp_containers = soup.select("div, section, article")
            
            for container in potential_exp_containers:
                # Look for job title indicators
                title_indicators = container.select("div.mr1.hoverable-link-text.t-bold, h3, .t-16.t-black.t-bold")
                
                if title_indicators and len(title_indicators) > 0:
                    # Check if this container has multiple job entries
                    container_text = container.get_text().strip().lower()
                    
                    # Look for experience-related keywords
                    experience_keywords = ['experience', 'work', 'employment', 'position', 'role', 'job']
                    
                    if any(keyword in container_text for keyword in experience_keywords):
                        # Try to extract individual experience items from this container
                        items = container.select("li, div[class*='experience'], div[class*='position']")
                        
                        for item in items:
                            has_title = item.select_one("div.mr1.hoverable-link-text.t-bold, h3, .t-16.t-black.t-bold")
                            if has_title and len(item.get_text().strip()) > 30:
                                exp_sections.append(item)
                                
            if DEBUG:
                print(f"Found {len(exp_sections)} experience items using ultra fallback strategy")
        
        if DEBUG:
            print(f"Total experience sections found: {len(exp_sections)}")
            
        for exp in exp_sections[:10]:  # Limit to first 10 experience entries
            exp_data = {}
            
            # Job title - enhanced selectors with priority order
            title_selectors = [
                "div.mr1.hoverable-link-text.t-bold span[aria-hidden='true']",  # Primary selector for job titles
                "div.display-flex span[aria-hidden='true']",
                "div.mr1 span[aria-hidden='true']", 
                "a span[aria-hidden='true']",
                "h3 span[aria-hidden='true']",
                "div span[aria-hidden='true']"
            ]
            
            title_elem = None
            for sel in title_selectors:
                title_elem = exp.select_one(sel)
                if title_elem and title_elem.text.strip() and len(title_elem.text.strip()) > 2:
                    if DEBUG:
                        print(f"Found job title: {title_elem.text.strip()}")
                    break
                    
            exp_data['title'] = title_elem.text.strip() if title_elem else ""
            
            # Company name - enhanced selectors
            company_selectors = [
                "span.t-14.t-normal span[aria-hidden='true']",  # Primary for company names
                "span.t-14 span[aria-hidden='true']", 
                "div.t-14 span[aria-hidden='true']",
                "span.t-14",
                "h4"
            ]
            
            company_elem = None
            for sel in company_selectors:
                company_elem = exp.select_one(sel)
                if (company_elem and company_elem.text.strip() and 
                    company_elem != title_elem and 
                    len(company_elem.text.strip()) > 2):
                    if DEBUG:
                        print(f"Found company: {company_elem.text.strip()}")
                    break
                    
            exp_data['company'] = company_elem.text.strip() if company_elem else ""
            
            # Duration - enhanced selectors for better extraction
            duration_selectors = [
                "span.pvs-entity__caption-wrapper[aria-hidden='true']",  # Primary for duration
                "span.t-14.t-black--light span[aria-hidden='true']",
                "span.t-black--light span[aria-hidden='true']", 
                "span.t-black--light",
                "time"
            ]
            
            duration_elem = None
            for sel in duration_selectors:
                duration_elem = exp.select_one(sel)
                if (duration_elem and duration_elem.text.strip() and 
                    duration_elem != title_elem and duration_elem != company_elem):
                    # Check if it looks like a duration (contains years, months, etc.)
                    duration_text = duration_elem.text.strip()
                    if any(indicator in duration_text.lower() for indicator in ['yr', 'mo', 'month', 'year', 'present', '20']):
                        if DEBUG:
                            print(f"Found duration: {duration_text}")
                        break
                    
            exp_data['duration'] = duration_elem.text.strip() if duration_elem else ""
            
            # Filter out connection suggestions, certifications and projects that get mixed into experience
            title = exp_data.get('title', '').lower()
            company = exp_data.get('company', '').lower()
            duration = exp_data.get('duration', '').lower()
            
            # Skip LinkedIn connection suggestions and people recommendations
            is_linkedin_suggestion = any(pattern in title for pattern in [
                'get introduced to',
                'connect with',
                'reach out to',
                'send a message to'
            ]) or any(pattern in company for pattern in [
                'ask your mutual connections',
                'mutual connections to help',
                'start a conversation',
                'connect on linkedin',
                '· 1st',  # First degree connection
                '· 2nd',  # Second degree connection
                '· 3rd'   # Third degree connection
            ])
            
            # Skip if it looks like a person name as title (connection suggestions)
            is_person_name = (len(title.split()) == 2 and  # Two words (first name last name)
                             title.replace(' ', '').isalpha() and  # Only letters
                             not any(work_word in title for work_word in ['developer', 'engineer', 'manager', 'analyst', 'specialist', 'tester', 'team']))
            
            # Skip if company field contains connection indicators
            is_connection_company = ('·' in company and len(company) < 10)  # Like "· 1st", "· 2nd"
            
            # Skip if it looks like a certification
            is_certification = any(word in title for word in ['certificate', 'certification', 'cyber', 'advent']) or \
                             any(word in company for word in ['tryhackme', 'hackthebox', 'certificate'])
            
            # Skip if it looks like a project
            is_project = (len(company) > 100 or  # Company field is too long (likely a description)
                         'github' in company or 'built with' in company or 
                         'lightning-fast' in company or 'file indexer' in company)
            
            # Must have proper duration for work experience
            has_valid_duration = (duration and any(indicator in duration for indicator in 
                                ['yr', 'mo', 'month', 'year', 'present', '20', 'jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                                 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']))
            
            # Only add valid work experience entries
            if (exp_data['title'] and exp_data['company'] and 
                not is_linkedin_suggestion and not is_person_name and not is_connection_company and
                not is_certification and not is_project and
                has_valid_duration and len(exp_data['company']) < 100):  # Reasonable company name length
                
                if DEBUG:
                    print(f"Adding valid experience: {exp_data['title']} at {exp_data['company']}")
                experience_items.append(exp_data)
            else:
                if DEBUG:
                    print(f"Filtered out: {exp_data['title']} at {exp_data['company']} (suggestion: {is_linkedin_suggestion}, person: {is_person_name}, connection: {is_connection_company}, cert: {is_certification}, project: {is_project}, duration: {has_valid_duration})")
        
        profile_data['experience'] = experience_items
        
    except Exception as e:
        if DEBUG:
            print(f"Error extracting main profile: {e}")
    
    return profile_data

def extract_recent_activity(soup):
    """Extract recent activity information"""
    activity_data = []
    
    try:
        # Updated selectors for LinkedIn 2025 activity structure
        activity_selectors = [
            "div.feed-shared-update-v2",
            "div.activity-share-update",
            "article.artdeco-card",
            "div.feed-update-v2",
            "article"
        ]
        
        activity_items = []
        for selector in activity_selectors:
            activity_items = soup.select(selector)
            if activity_items:
                if DEBUG:
                    print(f"Found {len(activity_items)} activity items with selector: {selector}")
                break
        
        for item in activity_items[:10]:  # Limit to first 10 activities
            activity = {}
            
            # Activity type - updated selectors
            type_selectors = [
                "span.feed-shared-actor__sub-description span[aria-hidden='true']",
                "div.feed-shared-actor__meta span.t-12",
                "span.feed-shared-actor__sub-description",
                "span.t-12.t-black--light",
                "span.t-12"
            ]
            
            type_elem = None
            for sel in type_selectors:
                type_elem = item.select_one(sel)
                if type_elem and type_elem.text.strip():
                    break
                    
            activity['type'] = type_elem.text.strip() if type_elem else "Post"
            
            # Content - updated selectors
            content_selectors = [
                "div.feed-shared-text span[aria-hidden='true']",
                "div.feed-shared-update-v2__description span[aria-hidden='true']",
                "div.feed-shared-text",
                "div.feed-shared-update-v2__description",
                "div.activity-text",
                "div.share-update-card__description"
            ]
            
            content_elem = None
            for sel in content_selectors:
                content_elem = item.select_one(sel)
                if content_elem and content_elem.text.strip() and len(content_elem.text.strip()) > 20:
                    break
                    
            activity['content'] = content_elem.text.strip() if content_elem else "Not available"
            
            # Date - updated selectors and patterns for LinkedIn 2025
            date_value = "Not available"
            
            # Method 1: Look for time elements with datetime attribute
            time_elem = item.select_one("time")
            if time_elem and time_elem.get('datetime'):
                date_value = time_elem.get('datetime')
                if DEBUG:
                    print(f"Found date from datetime attribute: {date_value}")
            
            # Method 2: Look for visible time text in spans
            if date_value == "Not available":
                date_selectors = [
                    "span.update-components-actor__sub-description span[aria-hidden='true']",
                    "span.feed-shared-actor__sub-description span[aria-hidden='true']", 
                    "div.feed-shared-actor__meta span.t-12 span[aria-hidden='true']",
                    "time span[aria-hidden='true']",
                    "span.t-12.t-black--light span[aria-hidden='true']"
                ]
                
                for sel in date_selectors:
                    date_elem = item.select_one(sel)
                    if date_elem and date_elem.text.strip():
                        date_text = date_elem.text.strip()
                        # Check if this looks like a date (contains time indicators)
                        if any(indicator in date_text.lower() for indicator in ['ago', 'd', 'h', 'w', 'm', 'day', 'hour', 'week', 'month']):
                            date_value = date_text
                            if DEBUG:
                                print(f"Found date with selector: {sel} = {date_value}")
                            break
            
            # Method 3: Extract from JSON data patterns in page source
            if date_value == "Not available":
                item_html = str(item)
                date_patterns = [
                    r'"createdAt":(\d+)',
                    r'"publishedAt":(\d+)', 
                    r'"time":(\d+)',
                    r'"timestamp":(\d+)'
                ]
                
                for pattern in date_patterns:
                    match = re.search(pattern, item_html)
                    if match:
                        timestamp = int(match.group(1))
                        # Convert timestamp to readable format if it's a Unix timestamp
                        if timestamp > 1000000000:  # Unix timestamp
                            import datetime
                            date_value = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                            if DEBUG:
                                print(f"Found date from JSON timestamp: {date_value}")
                            break
                        
            activity['date'] = date_value
            
            # Reposts count extraction with improved number handling
            reposts_selectors = [
                "button[aria-label*='repost'] span[aria-hidden='true']",
                "span[data-repost-count] span[aria-hidden='true']",
                "button[data-repost-count] span",
                "span.social-counts-reposts__count",
                "button[aria-label*='Repost'] span",
                "span.social-details-social-counts__count-value",
                # General selectors that might contain repost counts
                "li span[aria-hidden='true']",
                "div.social-details-social-counts span"
            ]
            
            reposts_count = "0"
            
            # First try to find reposts from aria-label attributes
            # Check multiple aria-label patterns for reposts
            reposts_aria_patterns = [
                ("button[aria-label*='reposts']", r'([\d,]+)\s+reposts?'),       # "162 reposts of post"
                ("button[aria-label*='repost']", r'([\d,]+)\s+reposts?'),        # "162 repost of post"
                ("button[data-social-count-reposts]", r'([\d,]+)'),              # Direct number
            ]
            
            for selector, pattern in reposts_aria_patterns:
                aria_label_elem = item.select_one(selector)
                if aria_label_elem:
                    aria_label = aria_label_elem.get('aria-label', '')
                    reposts_match = re.search(pattern, aria_label)
                    if reposts_match:
                        reposts_count = reposts_match.group(1).replace(',', '')
                        if DEBUG:
                            print(f"Found reposts count from aria-label ({selector}): {reposts_count}")
                        break
            
            # If not found in aria-label, try selector-based extraction
            if reposts_count == "0":
                for sel in reposts_selectors:
                    reposts_elems = item.select(sel)  # Use select() to get all matches
                    for reposts_elem in reposts_elems:
                        if reposts_elem and reposts_elem.text.strip():
                            reposts_text = reposts_elem.text.strip().lower()
                            # Check if this element contains repost-related text
                            if 'repost' in reposts_text:
                                # Extract number from reposts text, handling comma-separated
                                reposts_match = re.search(r'([\d,]+)', reposts_text)
                                if reposts_match:
                                    reposts_count = reposts_match.group(1).replace(',', '')
                                    if DEBUG:
                                        print(f"Found reposts count with selector: {sel} = {reposts_count}")
                                    break
                    if reposts_count != "0":
                        break
            
            # Alternative method: look for text patterns like "3 reposts" in nearby elements
            if reposts_count == "0":
                # Search for text patterns in the entire item
                item_text = item.get_text(separator=' ', strip=True)
                repost_pattern_matches = re.finditer(r'([\d,]+)\s+reposts?', item_text, re.IGNORECASE)
                for match in repost_pattern_matches:
                    reposts_count = match.group(1).replace(',', '')
                    if DEBUG:
                        print(f"Found reposts count via text pattern: {reposts_count}")
                    break
            
            activity['reposts'] = reposts_count
            if DEBUG and reposts_count != "0":
                print(f"Post has {reposts_count} reposts")
            
            # Engagement - updated selectors for likes with improved number extraction
            likes_selectors = [
                "span.social-details-social-counts__social-proof-fallback-number",
                "span[data-social-proof-fallback] span[aria-hidden='true']",
                "button[data-reaction-details] span[aria-hidden='true']",
                "span.social-details-social-counts__count-value span[aria-hidden='true']",
                "span.social-counts-reactions__count",
                "button[aria-label*='reaction'] span",
            ]
            
            likes_elem = None
            likes_count = "0"
            
            # First try to find likes from aria-label attributes (more reliable)
            # Check multiple aria-label patterns for different like states
            aria_label_patterns = [
                ("button[aria-label*='You and']", r'You and ([\d,]+) others'),  # When user liked
                ("button[aria-label*='reactions']", r'([\d,]+)\s+reactions?'),   # General reactions
                ("button[aria-label*='likes']", r'([\d,]+)\s+likes?'),           # Specific likes
                ("button[data-reaction-details]", r'([\d,]+)'),                  # Direct number in aria-label
            ]
            
            for selector, pattern in aria_label_patterns:
                aria_label_elem = item.select_one(selector)
                if aria_label_elem:
                    aria_label = aria_label_elem.get('aria-label', '')
                    likes_match = re.search(pattern, aria_label)
                    if likes_match:
                        likes_count = likes_match.group(1).replace(',', '')
                        if DEBUG:
                            print(f"Found likes count from aria-label ({selector}): {likes_count}")
                        break
            
            # If not found in aria-label, try text-based extraction
            if likes_count == "0":
                for sel in likes_selectors:
                    likes_elem = item.select_one(sel)
                    if likes_elem and likes_elem.text.strip():
                        likes_text = likes_elem.text.strip()
                        # Extract number from likes text, handling comma-separated numbers
                        likes_match = re.search(r'([\d,]+)', likes_text)
                        if likes_match:
                            likes_count = likes_match.group(1).replace(',', '')
                            if DEBUG:
                                print(f"Found likes count with selector: {sel} = {likes_count}")
                            break
                    
            activity['likes'] = likes_count
            
            # Comments count - updated selectors with improved number extraction
            comments_selectors = [
                "button[aria-label*='comment'] span[aria-hidden='true']",
                "span.social-details-social-counts__count-value span[aria-hidden='true']",
                "span.social-counts-comments__count", 
                "button[aria-label*='comment'] span",
            ]
            
            comments_elem = None
            comments_count = "0"
            
            # First try to find comments from aria-label attributes
            # Check multiple aria-label patterns for comments
            comments_aria_patterns = [
                ("button[aria-label*='comments']", r'([\d,]+)\s+comments?'),     # "423 comments on post"
                ("button[aria-label*='comment']", r'([\d,]+)\s+comments?'),      # "423 comment on post" 
                ("button[data-social-count-comments]", r'([\d,]+)'),             # Direct number
            ]
            
            for selector, pattern in comments_aria_patterns:
                aria_label_elem = item.select_one(selector)
                if aria_label_elem:
                    aria_label = aria_label_elem.get('aria-label', '')
                    comments_match = re.search(pattern, aria_label)
                    if comments_match:
                        comments_count = comments_match.group(1).replace(',', '')
                        if DEBUG:
                            print(f"Found comments count from aria-label ({selector}): {comments_count}")
                        break
            
            # If not found in aria-label, try text-based extraction
            if comments_count == "0":
                for sel in comments_selectors:
                    comments_elem = item.select_one(sel)
                    if comments_elem and comments_elem.text.strip():
                        comments_text = comments_elem.text.strip()
                        # Extract number from comments text like "11 comments", handling comma-separated
                        comments_match = re.search(r'([\d,]+)', comments_text)
                        if comments_match:
                            comments_count = comments_match.group(1).replace(',', '')
                            if DEBUG:
                                print(f"Found comments count with selector: {sel} = {comments_count}")
                            break
                    
            activity['comments'] = comments_count + " comments"
            
            if activity['content'] != "Not available" or activity['type'] != "Not available":
                activity_data.append(activity)
        
    except Exception as e:
        if DEBUG:
            print(f"Error extracting recent activity: {e}")
    
    return activity_data

def extract_certifications(soup):
    """Extract certifications information"""
    certifications_data = []
    
    try:
        # Updated selectors for LinkedIn 2025 certifications structure
        cert_container_selectors = [
            "section.artdeco-card.certifications-section li.artdeco-list__item",
            "div.pvs-list__paged-list-item",
            "section[data-section='certifications'] li.artdeco-list__item",
            "li.artdeco-list__item",
            "div.pv-profile-section__card-item-v2"
        ]
        
        cert_items = []
        for selector in cert_container_selectors:
            cert_items = soup.select(selector)
            if cert_items:
                if DEBUG:
                    print(f"Found {len(cert_items)} certification items with selector: {selector}")
                break
        
        for cert in cert_items[:10]:  # Limit to first 10 certifications
            cert_data = {}
            
            # Certification name - updated selectors
            name_selectors = [
                "h3 span[aria-hidden='true']",
                "div.display-flex span[aria-hidden='true']",
                "a span[aria-hidden='true']",
                "div.mr1 span[aria-hidden='true']",
                "span[aria-hidden='true']"
            ]
            
            name_elem = None
            for sel in name_selectors:
                name_elem = cert.select_one(sel)
                if name_elem and name_elem.text.strip() and len(name_elem.text.strip()) > 5:
                    if DEBUG:
                        print(f"Found cert name with selector: {sel}")
                    break
                    
            cert_data['name'] = name_elem.text.strip() if name_elem else "Not available"
            
            # Issuer - updated selectors
            issuer_selectors = [
                "span.t-14.t-normal span[aria-hidden='true']",
                "span.t-14 span[aria-hidden='true']",
                "h4 span[aria-hidden='true']",
                "div.t-14 span[aria-hidden='true']",
                "span.t-14"
            ]
            
            issuer_elem = None
            for sel in issuer_selectors:
                issuer_elem = cert.select_one(sel)
                if issuer_elem and issuer_elem.text.strip() and issuer_elem != name_elem:
                    break
                    
            cert_data['issuer'] = issuer_elem.text.strip() if issuer_elem else "Not available"
            
            # Issue date - improved pattern based on correct HTML structure
            # Look for spans with class "pvs-entity__caption-wrapper" containing "Issued"
            issue_date = "Not available"
            
            # Primary selector - look for the caption wrapper with date info
            date_elem = cert.select_one('span.pvs-entity__caption-wrapper[aria-hidden="true"]')
            if date_elem and date_elem.text.strip():
                date_text = date_elem.text.strip()
                if 'issued' in date_text.lower():
                    # Extract just the issued date part, clean up
                    issued_match = re.search(r'issued\s+([^·]+)', date_text, re.IGNORECASE)
                    if issued_match:
                        issue_date = issued_match.group(1).strip()
                        if DEBUG:
                            print(f"Found issue date: {issue_date}")
                    else:
                        # Fallback to the full text if no pattern match
                        issue_date = date_text
                        if DEBUG:
                            print(f"Using full date text: {issue_date}")
                elif re.search(r'\b\d{4}\b', date_text):
                    # Contains a year, probably a date
                    issue_date = date_text
                    if DEBUG:
                        print(f"Found date with year: {issue_date}")
            
            # Fallback to old selectors if not found
            if issue_date == "Not available":
                all_spans = cert.find_all('span', {'aria-hidden': 'true'})
                for span in all_spans:
                    text = span.get_text(strip=True)
                    if 'issued' in text.lower() or re.search(r'\b\d{4}\b', text):
                        if 'issued' in text.lower():
                            issued_match = re.search(r'issued\s+([^·]+)', text, re.IGNORECASE)
                            if issued_match:
                                issue_date = issued_match.group(1).strip()
                                if DEBUG:
                                    print(f"Found issue date from fallback: {issue_date}")
                                break
                        elif re.search(r'\b\d{4}\b', text) and len(text) < 50:
                            issue_date = text
                            if DEBUG:
                                print(f"Found date from fallback year pattern: {issue_date}")
                            break
                            
            cert_data['issue_date'] = issue_date
            
            # Credential ID - look for text containing "Credential ID"
            credential_id = "Not available"
            
            # Look for spans containing "Credential ID" text
            all_spans = cert.find_all('span', {'aria-hidden': 'true'})
            for span in all_spans:
                text = span.get_text(strip=True)
                if 'credential id' in text.lower():
                    # Extract ID after "Credential ID"
                    id_match = re.search(r'credential\s+id\s+([^\s]+)', text, re.IGNORECASE)
                    if id_match:
                        credential_id = id_match.group(1).strip()
                        if DEBUG:
                            print(f"Found credential ID: {credential_id}")
                        break
                    else:
                        # Fallback - take everything after "Credential ID"
                        parts = text.split('Credential ID')
                        if len(parts) > 1:
                            credential_id = parts[1].strip()
                            if DEBUG:
                                print(f"Found credential ID (fallback): {credential_id}")
                            break
            
            # Fallback to old selectors if not found
            if credential_id == "Not available":
                cred_id_selectors = [
                    "span.pv-certifications__credential-id span[aria-hidden='true']",
                    "div[data-test='credential-id'] span[aria-hidden='true']",
                    "span[data-test='credential-id']",
                    "span.pv-certifications__credential-id"
                ]
                
                cred_elem = None
                for sel in cred_id_selectors:
                    cred_elem = cert.select_one(sel)
                    if cred_elem and cred_elem.text.strip():
                        credential_id = cred_elem.text.strip()
                        break
                        
            cert_data['credential_id'] = credential_id
            
            # Credential URL - look for actual certificate/credential links
            credential_url = "Not available"
            
            # Priority selectors for credential URLs
            credential_selectors = [
                "a[aria-label*='Show credential']",  # Primary - links with "Show credential" aria-label
                "a[aria-label*='credential']",       # Links mentioning credential in aria-label
                "a[href*='.pdf']",                   # Direct PDF certificate links
                "a[href*='certificate']",            # URLs containing 'certificate'
                "a[href*='credential']",             # URLs containing 'credential'  
                "a[href*='verify']",                 # Verification links
                "a[href*='badge']",                  # Badge/credential links
                "a[target='_self']:not([href*='linkedin.com'])", # External links (not LinkedIn internal)
            ]
            
            # Look for credential URLs in order of priority
            for sel in credential_selectors:
                credential_links = cert.select(sel)
                for link in credential_links:
                    href = link.get('href', '')
                    if href and href.startswith('http'):
                        # Skip LinkedIn company/profile URLs, keep actual credential URLs
                        if (not any(exclude in href for exclude in [
                            'linkedin.com/in/', 'linkedin.com/company/', 
                            'linkedin.com/school/', 'linkedin.com/authwall'
                        ])):
                            credential_url = href
                            if DEBUG:
                                print(f"Found credential URL with selector '{sel}': {credential_url}")
                            break
                if credential_url != "Not available":
                    break
                        
            cert_data['credential_url'] = credential_url
            
            # Only add if we have meaningful certification data (filter out people suggestions)
            cert_name = cert_data['name']
            issuer_name = cert_data['issuer']
            
            # Filter out people names - check for typical LinkedIn connection patterns
            is_person = False
            if any(pattern in cert_name.lower() for pattern in ['1st', '2nd', '3rd', '• 1st', '• 2nd', '• 3rd']):
                is_person = True
            if any(pattern in issuer_name.lower() for pattern in ['1st', '2nd', '3rd', '• 1st', '• 2nd', '• 3rd']):
                is_person = True
            # Check if it looks like a person's name (two words, title case, common indicators)
            if (len(cert_name.split()) == 2 and 
                cert_name.istitle() and 
                cert_data['issue_date'] in ['· 1st', '· 2nd', '· 3rd']):
                is_person = True
            
            if (not is_person and 
                cert_data['name'] != "Not available" and 
                len(cert_data['name']) > 3 and
                'certificate' in cert_data['name'].lower() or 'certification' in cert_data['name'].lower() or
                cert_data['issuer'] not in ['· 1st', '· 2nd', '· 3rd'] and
                not any(word in cert_data['name'].lower() for word in ['connection', 'people', 'profile', 'experience'])):
                certifications_data.append(cert_data)
        
    except Exception as e:
        if DEBUG:
            print(f"Error extracting certifications: {e}")
    
    return certifications_data

def extract_projects(soup):
    """Extract projects information based on actual LinkedIn projects page structure"""
    projects_data = []
    
    try:
        # Use the actual LinkedIn projects page structure
        # Main container: li.pvs-list__paged-list-item.artdeco-list__item.pvs-list__item--line-separated.pvs-list__item--one-column
        project_items = soup.select("li.pvs-list__paged-list-item.artdeco-list__item.pvs-list__item--line-separated.pvs-list__item--one-column")
        
        if DEBUG:
            print(f"Found {len(project_items)} potential project items")
        
        if not project_items:
            # Fallback selectors if the main selector doesn't work
            fallback_selectors = [
                "li.artdeco-list__item.pvs-list__item--line-separated",
                "div[data-view-name='profile-component-entity']",
                "li.artdeco-list__item"
            ]
            
            for selector in fallback_selectors:
                project_items = soup.select(selector)
                if project_items:
                    if DEBUG:
                        print(f"Using fallback selector: {selector}, found {len(project_items)} items")
                    break
        
        for project in project_items[:15]:  # Increased limit to capture more projects
            project_data = {
                'name': '',
                'description': '',
                'associated_with': '',
                'project_url': '',
                'duration': ''
            }
            
            # Project name - based on actual structure: div.mr1.t-bold span[aria-hidden='true']
            name_selectors = [
                "div.mr1.t-bold span[aria-hidden='true']",  # Primary selector based on HTML analysis
                "div.display-flex.align-items-center.mr1.t-bold span[aria-hidden='true']",
                "h3 span[aria-hidden='true']",
                "div.mr1 span[aria-hidden='true']",
                "a span[aria-hidden='true']"
            ]
            
            name_elem = None
            for sel in name_selectors:
                name_elem = project.select_one(sel)
                if name_elem and name_elem.text.strip() and len(name_elem.text.strip()) > 2:
                    project_data['name'] = name_elem.text.strip()
                    if DEBUG:
                        print(f"Found project name: {project_data['name']}")
                    break
            
            # Duration - based on actual structure: span.t-14.t-normal span[aria-hidden='true']
            duration_selectors = [
                "span.t-14.t-normal span[aria-hidden='true']",  # Primary based on HTML analysis
                "span.t-14 span[aria-hidden='true']",
                "span.pvs-entity__caption-wrapper[aria-hidden='true']",
                "time"
            ]
            
            duration_elem = None
            for sel in duration_selectors:
                duration_elem = project.select_one(sel)
                if (duration_elem and duration_elem.text.strip() and 
                    duration_elem != name_elem and
                    any(indicator in duration_elem.text.strip() for indicator in ['20', 'Present', '-', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])):
                    project_data['duration'] = duration_elem.text.strip()
                    if DEBUG:
                        print(f"Found project duration: {project_data['duration']}")
                    break
            
            # Description - based on actual structure: look in sub-components for the long description
            # The description is in: div.ATWDfuUGEhyWkwjaEvhvcAOKuvqRgpcbTjIFuQ > ul > li > div > div > div.t-14.t-normal.t-black span[aria-hidden='true']
            description_selectors = [
                "div.ATWDfuUGEhyWkwjaEvhvcAOKuvqRgpcbTjIFuQ span[aria-hidden='true']",  # Based on HTML analysis
                "div.pvs-entity__sub-components span[aria-hidden='true']",
                "ul.SxgmFvlQWwECBIJjrgHbgsrAgATmunE span[aria-hidden='true']",
                "div.t-14.t-normal.t-black span[aria-hidden='true']",
                "div.pv-shared-text-with-see-more span[aria-hidden='true']",
                "div.inline-show-more-text span[aria-hidden='true']"
            ]
            
            description_found = False
            for sel in description_selectors:
                desc_elems = project.select(sel)
                for desc_elem in desc_elems:
                    desc_text = desc_elem.text.strip()
                    # Look for substantial description text (longer than 50 chars)
                    if (desc_text and len(desc_text) > 50 and 
                        desc_text != project_data['name'] and 
                        desc_text != project_data['duration'] and
                        not desc_text.startswith('Skills:')):
                        project_data['description'] = desc_text
                        description_found = True
                        if DEBUG:
                            print(f"Found project description: {desc_text[:100]}...")
                        break
                if description_found:
                    break
            
            # Project URL - look for GitHub links in the description or as separate links
            url_found = False
            # First check description for URLs
            if project_data['description']:
                import re
                url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                urls = re.findall(url_pattern, project_data['description'])
                if urls:
                    project_data['project_url'] = urls[0]  # Use first URL found
                    url_found = True
                    if DEBUG:
                        print(f"Found project URL in description: {project_data['project_url']}")
            
            # If no URL in description, look for external links
            if not url_found:
                external_links = project.find_all('a', href=True)
                for link in external_links:
                    href = link.get('href', '')
                    if (href and 'http' in href and 'linkedin.com' not in href and 
                        any(domain in href for domain in ['github.com', 'gitlab.com', 'bitbucket.org', 'codepen.io', 'repl.it'])):
                        project_data['project_url'] = href
                        url_found = True
                        if DEBUG:
                            print(f"Found external project URL: {href}")
                        break
            
            # Associated with - extract technologies/skills from description
            if project_data['description']:
                # Look for "Technologies Used:" or "Skills:" in description
                desc_lower = project_data['description'].lower()
                if 'technologies used:' in desc_lower:
                    tech_start = desc_lower.find('technologies used:') + len('technologies used:')
                    tech_section = project_data['description'][tech_start:tech_start+200]  # Get next 200 chars
                    # Extract until next period or line break
                    tech_end = min([i for i in [tech_section.find('.'), tech_section.find('\n')] if i != -1] or [len(tech_section)])
                    project_data['associated_with'] = tech_section[:tech_end].strip()
                elif 'skills:' in desc_lower:
                    skills_start = desc_lower.find('skills:') + len('skills:')
                    skills_section = project_data['description'][skills_start:skills_start+200]
                    skills_end = min([i for i in [skills_section.find('.'), skills_section.find('\n')] if i != -1] or [len(skills_section)])
                    project_data['associated_with'] = skills_section[:skills_end].strip()
                else:
                    # Extract key technologies mentioned
                    tech_keywords = ['Python', 'JavaScript', 'React', 'Node.js', 'Django', 'Flask', 'HTML', 'CSS', 'SQL', 'MongoDB', 'Git', 'AWS', 'Docker']
                    found_techs = [tech for tech in tech_keywords if tech.lower() in desc_lower]
                    if found_techs:
                        project_data['associated_with'] = ', '.join(found_techs[:5])  # Limit to 5 technologies
            
            # Filter out non-project items (people suggestions, etc.)
            # NOTE: On a dedicated projects page, profile images and LinkedIn profile links are normal
            # Only filter out obvious people suggestions or invalid entries
            is_valid_project = True
            
            # Check if this is actually a person suggestion rather than a project
            project_text = project.get_text()
            
            # Strong indicators this is a person, not a project
            has_connection_indicator = any(indicator in project_text for indicator in ['· 1st', '· 2nd', '· 3rd', 'Follow', 'Connect', 'Message'])
            has_job_title_pattern = any(pattern in project_text.lower() for pattern in ['at ', ' | ', 'senior ', 'junior ', 'lead ', 'manager', 'developer at', 'engineer at'])
            
            # Check if name looks like a person's name AND has person context
            if project_data['name']:
                name_parts = project_data['name'].split()
                is_person_name = (len(name_parts) == 2 and 
                                all(part.istitle() and part.isalpha() for part in name_parts) and
                                len(name_parts[0]) > 2 and len(name_parts[1]) > 2 and
                                not any(tech in project_data['name'].lower() for tech in ['project', 'app', 'system', 'tool', 'platform', 'linux', 'terminal', 'scanner']))
            else:
                is_person_name = False
            
            # Only filter out if it's clearly a person suggestion
            if has_connection_indicator or (is_person_name and has_job_title_pattern):
                is_valid_project = False
                if DEBUG:
                    print(f"Filtered out person suggestion: {project_data['name']}")
                    print(f"  - Has connection indicator: {has_connection_indicator}")
                    print(f"  - Is person name with job context: {is_person_name and has_job_title_pattern}")
            
            # Additional validation: must have either a description, a GitHub URL, or a substantial name to be a valid project
            has_substantial_content = (
                (project_data['description'] and len(project_data['description']) > 20) or
                (project_data['project_url'] != 'Not available' and 'github.com' in project_data['project_url']) or
                (project_data['name'] and len(project_data['name']) > 10)  # Accept projects with meaningful names
            )
            
            if not has_substantial_content:
                is_valid_project = False
                if DEBUG:
                    print(f"Filtered out due to lack of substantial content: {project_data['name']}")
            
            # Keep projects that have project-like content
            if project_data['description'] and len(project_data['description']) > 50:
                if any(keyword in project_data['description'].lower() for keyword in 
                       ['developed', 'created', 'built', 'designed', 'implemented', 'technologies', 'features', 'github', 'repository', 'framework', 'tool', 'utility', 'cli', 'gui']):
                    is_valid_project = True  # Override filtering if it has project-like description
                    if DEBUG:
                        print(f"Confirmed as project due to project-like description: {project_data['name']}")
            
            # Also accept projects with project-like names even without descriptions
            if project_data['name'] and len(project_data['name']) > 10:
                project_keywords_in_name = ['project', 'system', 'application', 'app', 'tool', 'platform', 'website', 'portal', 'management', 'tracking', 'ordering', 'inventory']
                if any(keyword in project_data['name'].lower() for keyword in project_keywords_in_name):
                    is_valid_project = True  # Override filtering for project-like names
                    if DEBUG:
                        print(f"Confirmed as project due to project-like name: {project_data['name']}")
            
            # Only add if it's a valid project with a name
            if is_valid_project and project_data['name'] and len(project_data['name']) > 2:
                # Set defaults for empty fields
                if not project_data['description']:
                    project_data['description'] = 'Not available'
                if not project_data['associated_with']:
                    project_data['associated_with'] = 'Not available'
                if not project_data['project_url']:
                    project_data['project_url'] = 'Not available'
                if not project_data['duration']:
                    project_data['duration'] = 'Not available'
                
                projects_data.append(project_data)
                if DEBUG:
                    print(f"Added project: {project_data['name']}")
        
    except Exception as e:
        if DEBUG:
            print(f"Error extracting projects: {e}")
    
    return projects_data

def extract_skills(soup):
    """Extract skills information with proper endorsement counts"""
    skills_data = []
    
    try:
        # Multiple selector strategies for skills sections
        skills_selectors = [
            "li.pvs-list__paged-list-item.artdeco-list__item.pvs-list__item--line-separated.pvs-list__item--one-column",
            "section.artdeco-card.skills-section li.artdeco-list__item",
            "section[data-section='skills'] li.artdeco-list__item",
            "section.pvs-list-section li.artdeco-list__item",
            "div[data-view-name='profile-component-entity']"
        ]
        
        skills_items = []
        for selector in skills_selectors:
            skills_items = soup.select(selector)
            if skills_items:
                if DEBUG:
                    print(f"Found {len(skills_items)} skills items with selector: {selector}")
                break
        
        if not skills_items:
            if DEBUG:
                print("No skills items found")
            return skills_data
            
        for skill in skills_items[:30]:  # Limit to first 30 skills
            skill_data = {
                'name': '',
                'endorsements': '0'
            }
            
            # Skill name - enhanced selectors with priority order
            name_selectors = [
                "div.mr1.hoverable-link-text.t-bold span[aria-hidden='true']",  # Primary for skill names
                "div.display-flex.align-items-center.mr1.hoverable-link-text.t-bold span[aria-hidden='true']",
                "a div.mr1.hoverable-link-text.t-bold span[aria-hidden='true']",
                "h3 span[aria-hidden='true']",
                "a span[aria-hidden='true']",
                "div.mr1 span[aria-hidden='true']"
            ]
            
            name_elem = None
            for sel in name_selectors:
                name_elem = skill.select_one(sel)
                if name_elem and name_elem.text.strip() and len(name_elem.text.strip()) > 1:
                    if DEBUG:
                        print(f"Found skill name: {name_elem.text.strip()}")
                    break
                    
            skill_data['name'] = name_elem.text.strip() if name_elem else ""
            
            # Endorsements - enhanced extraction for actual endorsement counts
            endorsement_selectors = [
                "div.hoverable-link-text.display-flex.align-items-center.t-14.t-normal.t-black span[aria-hidden='true']",  # Primary for endorsements
                "span[aria-hidden='true']"  # Generic, filter by content
            ]
            
            endorsement_count = "0"
            for sel in endorsement_selectors:
                endorsement_elems = skill.select(sel)
                for endorsement_elem in endorsement_elems:
                    endorsement_text = endorsement_elem.text.strip().lower()
                    if DEBUG and endorsement_text:
                        print(f"Checking endorsement text: {endorsement_text}")
                    
                    # Look for endorsement patterns
                    if 'endorsement' in endorsement_text:
                        # Extract number from text like "2 endorsements", "1 endorsement"
                        import re
                        numbers = re.findall(r'\d+', endorsement_text)
                        if numbers:
                            endorsement_count = numbers[0]
                            if DEBUG:
                                print(f"Found endorsement count: {endorsement_count}")
                            break
                            
                if endorsement_count != "0":
                    break
            
            skill_data['endorsements'] = endorsement_count
            
            # Only add valid skills with names
            if skill_data['name']:
                skills_data.append(skill_data)
                if DEBUG:
                    print(f"Added skill: {skill_data['name']} ({skill_data['endorsements']} endorsements)")
        
    except Exception as e:
        if DEBUG:
            print(f"Error extracting skills: {e}")
    
    return skills_data

def extract_education(soup):
    """Extract education information"""
    education_data = []
    
    try:
        # Target the specific LinkedIn education structure (same as experience)
        education_items = []
        
        # Strategy 1: Look for the correct education items with proper classes
        # These are the actual education items, not connection suggestions
        education_items_raw = soup.select("li.pvs-list__paged-list-item.artdeco-list__item.pvs-list__item--line-separated.pvs-list__item--one-column")
        
        if education_items_raw:
            education_items = education_items_raw
            if DEBUG:
                print(f"Found {len(education_items)} education items using specific LinkedIn structure")
        
        # Strategy 2: Fallback - look for education section and filter properly
        if not education_items:
            # Find all list items and filter by content structure
            all_items = soup.select("li.artdeco-list__item")
            education_items = []
            
            for item in all_items:
                # Check if this item has the proper education structure
                classes = item.get('class', [])
                
                # Skip connection suggestions (they have random long class names)
                has_random_classes = any(len(cls) > 30 for cls in classes)
                if has_random_classes:
                    continue
                
                # Check for education indicators
                has_institution = item.select_one("div.mr1.hoverable-link-text.t-bold") or \
                                 item.select_one("a span[aria-hidden='true']")
                has_degree = item.select_one("span.t-14.t-normal") or \
                            item.select_one("span.t-14")
                has_duration = item.select_one("span.pvs-entity__caption-wrapper") or \
                              item.select_one("span.t-14.t-black--light")
                
                # Must have proper classes for education
                if (has_institution and 'pvs-list__paged-list-item' in classes):
                    education_items.append(item)
                    
            if DEBUG:
                print(f"Found {len(education_items)} education items using filtered strategy")
            
        for edu in education_items[:10]:  # Limit to first 10 education entries
            edu_data = {
                'institution': '',
                'degree': '',
                'field_of_study': '',
                'duration': '',
                'grade': '',
                'activities': '',
                'description': ''
            }
            
            # Institution name - enhanced selectors with priority order
            institution_selectors = [
                "div.mr1.hoverable-link-text.t-bold span[aria-hidden='true']",  # Primary for institutions
                "a div.mr1.hoverable-link-text.t-bold span[aria-hidden='true']",
                "div.display-flex.align-items-center.mr1.hoverable-link-text.t-bold span[aria-hidden='true']",
                "h3 span[aria-hidden='true']",
                "a span[aria-hidden='true']",
                "div.mr1 span[aria-hidden='true']"
            ]
            
            institution_elem = None
            for sel in institution_selectors:
                institution_elem = edu.select_one(sel)
                if institution_elem and institution_elem.text.strip() and len(institution_elem.text.strip()) > 2:
                    if DEBUG:
                        print(f"Found institution: {institution_elem.text.strip()}")
                    break
                    
            edu_data['institution'] = institution_elem.text.strip() if institution_elem else ""
            
            # Degree and field of study - usually combined in one element
            degree_selectors = [
                "span.t-14.t-normal span[aria-hidden='true']",  # Primary for degree/field
                "div.t-14.t-normal span[aria-hidden='true']",
                "span.t-14 span[aria-hidden='true']",
                "div.t-14 span[aria-hidden='true']",
                "h4 span[aria-hidden='true']"
            ]
            
            degree_elem = None
            for sel in degree_selectors:
                degree_elem = edu.select_one(sel)
                if (degree_elem and degree_elem.text.strip() and 
                    degree_elem != institution_elem and 
                    len(degree_elem.text.strip()) > 2):
                    if DEBUG:
                        print(f"Found degree/field: {degree_elem.text.strip()}")
                    break
                    
            # Split degree and field if combined (e.g., "Bachelor of Engineering, Computer Science")
            degree_text = degree_elem.text.strip() if degree_elem else ""
            if ',' in degree_text:
                parts = degree_text.split(',', 1)
                edu_data['degree'] = parts[0].strip()
                edu_data['field_of_study'] = parts[1].strip()
            else:
                edu_data['degree'] = degree_text
                edu_data['field_of_study'] = ""
            
            # Duration - enhanced selectors
            duration_selectors = [
                "span.pvs-entity__caption-wrapper[aria-hidden='true']",  # Primary for duration
                "span.t-14.t-black--light span[aria-hidden='true']",
                "span.t-black--light span[aria-hidden='true']",
                "span.t-black--light",
                "time"
            ]
            
            duration_elem = None
            for sel in duration_selectors:
                duration_elem = edu.select_one(sel)
                if (duration_elem and duration_elem.text.strip() and 
                    duration_elem != institution_elem and duration_elem != degree_elem):
                    # Check if it looks like a duration (contains years, dates, etc.)
                    duration_text = duration_elem.text.strip()
                    if any(indicator in duration_text.lower() for indicator in ['20', 'yr', 'mo', 'month', 'year', 'present', '-']):
                        if DEBUG:
                            print(f"Found duration: {duration_text}")
                        break
                    
            edu_data['duration'] = duration_elem.text.strip() if duration_elem else ""
            
            # Grade/GPA - look for grade information
            grade_selectors = [
                "span[aria-hidden='true']"  # Generic selector, filter by content
            ]
            
            for sel in grade_selectors:
                grade_elems = edu.select(sel)
                for grade_elem in grade_elems:
                    grade_text = grade_elem.text.strip().lower()
                    if (grade_text and 
                        any(indicator in grade_text for indicator in ['grade:', 'gpa:', 'cgpa:', 'score:', 'marks:']) or
                        (grade_text.replace('.', '').replace(':', '').isdigit() and len(grade_text) <= 5)):
                        edu_data['grade'] = grade_elem.text.strip()
                        if DEBUG:
                            print(f"Found grade: {grade_elem.text.strip()}")
                        break
                if edu_data['grade']:
                    break
            
            # Activities and description - look in sub-components
            activities_selectors = [
                "div.pvs-entity__sub-components span[aria-hidden='true']",
                "div.ATWDfuUGEhyWkwjaEvhvcAOKuvqRgpcbTjIFuQ span[aria-hidden='true']",
                "ul.SxgmFvlQWwECBIJjrgHbgsrAgATmunE span[aria-hidden='true']"
            ]
            
            activities_texts = []
            for sel in activities_selectors:
                activity_elems = edu.select(sel)
                for activity_elem in activity_elems:
                    activity_text = activity_elem.text.strip()
                    if (activity_text and 
                        activity_text not in [edu_data['institution'], edu_data['degree'], edu_data['field_of_study'], edu_data['duration'], edu_data['grade']] and
                        len(activity_text) > 5):
                        activities_texts.append(activity_text)
            
            # Join activities and use as description if substantial
            if activities_texts:
                combined_activities = ' | '.join(activities_texts[:3])  # Limit to first 3 activities
                if len(combined_activities) > 20:  # Only if substantial content
                    edu_data['activities'] = combined_activities
                    edu_data['description'] = combined_activities
            
            # Filter out connection suggestions and invalid entries (same logic as experience)
            institution = edu_data.get('institution', '').lower()
            degree = edu_data.get('degree', '').lower()
            duration = edu_data.get('duration', '').lower()
            
            # Skip LinkedIn connection suggestions
            is_linkedin_suggestion = any(pattern in degree for pattern in [
                '· 1st',  # First degree connection
                '· 2nd',  # Second degree connection
                '· 3rd'   # Third degree connection
            ])
            
            # Skip if it looks like a person name as institution (connection suggestions)
            is_person_name = (len(institution.split()) == 2 and  # Two words (first name last name)
                             institution.replace(' ', '').isalpha() and  # Only letters
                             not any(edu_word in institution for edu_word in ['university', 'college', 'school', 'institute', 'academy']))
            
            # Skip if degree field contains connection indicators
            is_connection_degree = ('·' in degree and len(degree) < 10)  # Like "· 1st", "· 2nd"
            
            # Must have proper institution and not be a connection suggestion
            if (edu_data['institution'] and not is_linkedin_suggestion and 
                not is_person_name and not is_connection_degree):
                
                if DEBUG:
                    print(f"Adding valid education: {edu_data['institution']} - {edu_data['degree']}")
                education_data.append(edu_data)
            else:
                if DEBUG:
                    print(f"Filtered out: {edu_data['institution']} - {edu_data['degree']} (suggestion: {is_linkedin_suggestion}, person: {is_person_name}, connection: {is_connection_degree})")
        
    except Exception as e:
        if DEBUG:
            print(f"Error extracting education: {e}")
    
    return education_data

def try_requests_fallback(username):
    """Try to get basic profile info using requests as fallback"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        # Try different approaches
        urls_to_try = [
            f"https://www.linkedin.com/in/{username}/",
            f"https://linkedin.com/in/{username}/",
            f"https://www.linkedin.com/pub/{username}",
        ]
        
        for url in urls_to_try:
            if DEBUG:
                print(f"Trying: {url}")
            
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if DEBUG:
                    print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    # Check if we got actual profile content
                    if any(indicator in response.text.lower() for indicator in ['linkedin member', 'professional', 'experience at', 'works at']):
                        if DEBUG:
                            print("Found potential profile content")
                        return response.text
                    elif "authwall" not in response.text.lower() and "login" not in response.text.lower():
                        if DEBUG:
                            print("Got response without auth wall")
                        return response.text
            except Exception as e:
                if DEBUG:
                    print(f"Error with {url}: {e}")
                continue
        
        # Try direct access with different approach
        profile_url = f"https://www.linkedin.com/in/{username}/"
        response = requests.get(profile_url, headers=headers, timeout=10)
        
        if DEBUG:
            print(f"Direct request status: {response.status_code}")
        
        if response.status_code == 200:
            return response.text
            
    except Exception as e:
        if DEBUG:
            print(f"Requests fallback failed: {e}")
    
    return None

def get_profile_data(username, headless=True):
    """Get comprehensive profile data from LinkedIn profile
    
    Args:
        username: LinkedIn username (e.g., 'yaniv-haliwa')
        headless: Whether to run in headless mode (default: True)
    """
    # First try requests fallback for basic info
    fallback_html = try_requests_fallback(username)
    if fallback_html:
        if DEBUG:
            print("Got data from requests fallback, parsing...")
        soup = BeautifulSoup(fallback_html, 'html.parser')
        main_profile = extract_main_profile(soup)
        if main_profile and not main_profile.get('error'):
            return {
                'username': username,
                'main_profile': main_profile,
                'recent_activity': [],
                'certifications': [],
                'projects': [],
                'skills': [],
                'education': [],
                'note': 'Limited data from fallback method'
            }
    
    driver = setup_driver(headless=headless)
    
    # Add user agent rotation and anti-detection measures
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    profile_data = {
        'username': username,
        'main_profile': {},
        'recent_activity': [],
        'certifications': [],
        'projects': [],
        'skills': [],
        'education': []
    }
    
    try:
        # URLs to analyze - try public view first
        urls = {
            'main_profile': f"https://www.linkedin.com/in/{username}/",
            'recent_activity': f"https://www.linkedin.com/in/{username}/recent-activity/all/",
            'experience': f"https://www.linkedin.com/in/{username}/details/experience/",
            'certifications': f"https://www.linkedin.com/in/{username}/details/certifications/",
            'projects': f"https://www.linkedin.com/in/{username}/details/projects/",
            'skills': f"https://www.linkedin.com/in/{username}/details/skills/",
            'education': f"https://www.linkedin.com/in/{username}/details/education/"
        }
        
        # Try public profile access first
        public_url = f"https://www.linkedin.com/pub/{username}/view"
        if DEBUG:
            print(f"Trying public profile access: {public_url}")
        
        try:
            driver.get(public_url)
            time.sleep(3)
            if "linkedin.com/in/" in driver.current_url:
                if DEBUG:
                    print("Public profile redirected to regular profile - good sign")
        except:
            if DEBUG:
                print("Public profile access failed, continuing with regular URLs")
        
        for section, url in urls.items():
            if DEBUG:
                print(f"Analyzing {section}: {url}")
            
            try:
                driver.get(url)
                time.sleep(8)  # Allow page to load
                
                # Check if we're redirected to login
                if "login" in driver.current_url or "authwall" in driver.current_url:
                    if DEBUG:
                        print(f"Redirected to login for {section}, trying alternative approach")
                    
                    # Try direct access with different user agent
                    driver.execute_script("""
                        Object.defineProperty(navigator, 'userAgent', {
                            get: () => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                        });
                    """)
                    
                    # Try the URL again
                    driver.get(url)
                    time.sleep(5)
                
                # Wait for content to load with multiple selectors
                wait_selectors = ["main", "body", "div"]
                content_loaded = False
                for selector in wait_selectors:
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.TAG_NAME, selector))
                        )
                        content_loaded = True
                        break
                    except TimeoutException:
                        continue
                
                if not content_loaded:
                    if DEBUG:
                        print(f"Could not load content for {section}")
                    continue
                
                # Get page source for parsing
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # Extract data based on section
                if section == 'main_profile':
                    profile_data['main_profile'] = extract_main_profile(soup)
                    # Move experience to top-level to avoid duplication
                    if 'experience' in profile_data['main_profile']:
                        profile_data['experience'] = profile_data['main_profile']['experience']
                        # Remove from main_profile to avoid duplication
                        del profile_data['main_profile']['experience']
                elif section == 'recent_activity':
                    profile_data['recent_activity'] = extract_recent_activity(soup)
                elif section == 'experience':
                    # Extract experience from dedicated experience page (if not already extracted from main_profile)
                    if 'experience' not in profile_data:
                        experience_data = extract_main_profile(soup).get('experience', [])
                        profile_data['experience'] = experience_data
                elif section == 'certifications':
                    profile_data['certifications'] = extract_certifications(soup)
                elif section == 'projects':
                    profile_data['projects'] = extract_projects(soup)
                elif section == 'skills':
                    profile_data['skills'] = extract_skills(soup)
                elif section == 'education':
                    profile_data['education'] = extract_education(soup)
                
                if DEBUG:
                    print(f"Extracted {section} data successfully")
                
                # Small delay between requests
                time.sleep(2)
                
            except TimeoutException:
                if DEBUG:
                    print(f"Timeout waiting for {section} to load")
                continue
            except Exception as e:
                if DEBUG:
                    print(f"Error analyzing {section}: {e}")
                continue
        
        return profile_data
    
    finally:
        # Keep browser open for inspection
        if DEBUG:
            print("\nBrowser will stay open for inspection...")
            print("Press Ctrl+C in terminal to close when done.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nClosing browser...")
                driver.quit()
        else:
            driver.quit()

def display_profile_data(profile_data):
    """Display the profile data in a formatted way"""
    print(f"\n{'='*80}")
    print(f"LinkedIn Profile Data for: {profile_data['username']}")
    print(f"{'='*80}")
    
    # Check if we have authentication issues
    main = profile_data['main_profile']
    if main and main.get('error'):
        print(f"\n❌ ERROR: {main['error']}")
        print("\n📋 TROUBLESHOOTING:")
        print("1. LinkedIn requires authentication for profile access")
        print("2. Try running with --no-headless to manually login")
        print("3. Consider using LinkedIn's official API")
        print("4. Some profiles may be set to private")
        print(f"\n🔗 Profile URL: https://www.linkedin.com/in/{profile_data['username']}/")
        return
    
    if main:
        print(f"\n--- MAIN PROFILE ---")
        print(f"Name: {main.get('name', 'Not available')}")
        print(f"Headline: {main.get('headline', 'Not available')}")
        print(f"Location: {main.get('location', 'Not available')}")
        print(f"About: {main.get('about', 'Not available')[:200]}{'...' if len(main.get('about', '')) > 200 else ''}")
        
        if main.get('experience'):
            print(f"\nExperience ({len(main['experience'])} items):")
            for i, exp in enumerate(main['experience'][:3], 1):  # Show first 3
                print(f"  {i}. {exp.get('title', 'N/A')} at {exp.get('company', 'N/A')} ({exp.get('duration', 'N/A')})")
        
        if main.get('education'):
            print(f"\nEducation ({len(main['education'])} items):")
            for i, edu in enumerate(main['education'], 1):
                print(f"  {i}. {edu.get('degree', 'N/A')} at {edu.get('school', 'N/A')} ({edu.get('duration', 'N/A')})")
    
    # Recent Activity
    if profile_data['recent_activity']:
        print(f"\n--- RECENT ACTIVITY ({len(profile_data['recent_activity'])} items) ---")
        for i, activity in enumerate(profile_data['recent_activity'][:5], 1):  # Show first 5
            print(f"{i}. {activity.get('type', 'N/A')} - {activity.get('date', 'N/A')}")
            content = activity.get('content', 'N/A')
            print(f"   Content: {content[:100]}{'...' if len(content) > 100 else ''}")
            print(f"   Engagement: {activity.get('likes', '0')} likes, {activity.get('comments', '0')} comments, {activity.get('reposts', '0')} reposts")
    
    # Certifications
    if profile_data['certifications']:
        print(f"\n--- CERTIFICATIONS ({len(profile_data['certifications'])} items) ---")
        for i, cert in enumerate(profile_data['certifications'], 1):
            print(f"{i}. {cert.get('name', 'N/A')}")
            print(f"   Issuer: {cert.get('issuer', 'N/A')}")
            print(f"   Date: {cert.get('issue_date', 'N/A')}")
            if cert.get('credential_id') != 'Not available':
                print(f"   Credential ID: {cert.get('credential_id', 'N/A')}")
    
    # Projects
    if profile_data['projects']:
        print(f"\n--- PROJECTS ({len(profile_data['projects'])} items) ---")
        for i, project in enumerate(profile_data['projects'], 1):
            print(f"{i}. {project.get('name', 'N/A')}")
            print(f"   Associated with: {project.get('associated_with', 'N/A')}")
            print(f"   Duration: {project.get('duration', 'N/A')}")
            desc = project.get('description', 'N/A')
            print(f"   Description: {desc[:150]}{'...' if len(desc) > 150 else ''}")
    
    # Skills
    if profile_data['skills']:
        print(f"\n--- SKILLS ({len(profile_data['skills'])} items) ---")
        # Show top skills first
        top_skills = [s for s in profile_data['skills'] if s.get('is_top_skill')]
        other_skills = [s for s in profile_data['skills'] if not s.get('is_top_skill')]
        
        if top_skills:
            print("Top Skills:")
            for skill in top_skills:
                endorsements = skill.get('endorsements', '0')
                print(f"  • {skill.get('name', 'N/A')} ({endorsements} endorsements)")
        
        if other_skills:
            print("Other Skills:")
            for skill in other_skills[:10]:  # Show first 10 other skills
                endorsements = skill.get('endorsements', '0')
                print(f"  • {skill.get('name', 'N/A')} ({endorsements} endorsements)")
    
    print(f"\n{'='*80}")

def save_profile_data(profile_data, filename):
    """Save profile data to JSON file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
        print(f"Profile data saved to {filename}")
    except Exception as e:
        print(f"Error saving profile data: {e}")

def main():
    # Command line argument parsing
    import argparse
    parser = argparse.ArgumentParser(description='LinkedIn Profile Analyzer')
    parser.add_argument('username', help='LinkedIn username (e.g., yaniv-haliwa)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--save', type=str, help='Save profile data to JSON file')
    parser.add_argument('--no-headless', action='store_true', 
                      help='Run in visible browser mode (helps bypass detection)')
    args = parser.parse_args()
    
    # Set debug mode if specified
    global DEBUG
    if args.debug:
        DEBUG = True
    
    try:
        print("Starting LinkedIn profile analyzer...")
        print(f"Username: {args.username}")
        print(f"Headless mode: {'disabled' if args.no_headless else 'enabled'}")
        
        # Get profile data
        profile_data = get_profile_data(args.username, headless=not args.no_headless)
        
        # Display results
        display_profile_data(profile_data)
        
        # Save to file if requested
        if args.save:
            save_profile_data(profile_data, args.save)
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()