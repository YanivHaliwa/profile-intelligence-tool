# LinkedIn Profile Analyzer - Web Application
[![deepwiki](https://img.shields.io/badge/Ask_DeepWiki-_.svg?style=flat&color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjE2IiBoZWlnaHQ9IjE2IiByeD0iMiIgZmlsbD0iI2ZmZiIvPgo8dGV4dCB4PSI4IiB5PSIxMSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9IkFyaWFsLCBIZWx2ZXRpY2EsIHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iNyIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzAwMCI+RFc8L3RleHQ+Cjwvc3ZnPgo%3D&logoColor=ffffff)](https://deepwiki.com/YanivHaliwa/profile-intelligence-tool)

> **⚠️ EDUCATIONAL USE ONLY - AUTHORIZED TESTING DISCLAIMER ⚠️**
> 
> This tool is developed exclusively for **educational purposes**, **professional development**, and **authorized profile analysis** in controlled environments. 
> 
> **IMPORTANT LEGAL NOTICES:**
> - ✅ **Authorized Use Only**: Use only on profiles you own or have explicit written permission to analyze
> - ✅ **Educational Research**: Designed for web development education and AI integration learning
> - ✅ **Professional Development**: Intended for career analysis and profile optimization research
> - ❌ **No Unauthorized Access**: Do not use on profiles without proper authorization
> - ❌ **Respect Terms of Service**: Always comply with LinkedIn's Terms of Service and applicable laws
> - ❌ **No Malicious Intent**: This tool must not be used for harassment, stalking, or unauthorized data collection
> 
> **By using this software, you acknowledge that you have proper authorization and will use it responsibly and legally.**

## Overview
A comprehensive LinkedIn profile analysis web application that reveals profile data, performs AI-powered professional assessments, and presents insights through a modern Flask-based interface with soft blue styling.

## 🌐 Main Application - `main.py`
**Flask Web Server** - The core application providing the web interface and orchestrating the analysis pipeline.

### Key Features:
- **Modern Web Interface**: Clean, responsive design with soft blue color scheme
- **Real-time Analysis**: Background processing with status updates
- **AI Integration**: Seamless ChatGPT 4o-mini analysis with formatted results
- **Data Management**: JSON file handling and profile data presentation
- **Multi-profile Support**: File browser for multiple analyzed profiles

## 🔄 Application Flow

### 1. **User Input** (`main.py`)
```
User enters LinkedIn username → Flask web interface
```

### 2. **Profile Data Collection** (`profile_analyzer.py`)
```
main.py calls → profile_analyzer.py → Reveals LinkedIn data → Saves JSON
```

### 3. **AI Analysis** (`profile_ai_assistant.py`)
```
User clicks "AI Analysis" → main.py calls → profile_ai_assistant.py → ChatGPT analysis
```

### 4. **Results Display** (`main.py`)
```
Formatted AI analysis → Flask templates → Soft blue web interface
```

## 🚀 Quick Start

## 🔑 Setup
1. Set OpenAI API key: `export OPENAI_API_KEY='your-key-here'`
2. Install dependencies: `pip install -r requirements.txt`
3. Run application: `python3 main.py`

### 1. **Start the Web Application**
```bash
python3 main.py
```
**Server runs on:** `http://localhost:5000`

### 2. **Access the Web Interface**
- Open browser to `http://localhost:5000`
- Enter LinkedIn username (e.g., `yaniv-haliwa`)
- Click "Analyze Profile"

### 3. **Get AI Analysis**
- Wait for profile analysis to complete
- Click "Get AI Analysis" button
- View comprehensive professional assessment

## 📊 AI Analysis Features
**10-Section Professional Assessment:**
- **Compelling Headline**: Professional tagline
- **Overall Rating**: Score out of 100 with weighted breakdown
- **Professional Summary**: Career overview and positioning
- **Key Strengths**: Core competencies and abilities
- **Career Trajectory**: Progression and growth analysis
- **Career Recommendations**: Strategic advancement advice
- **Activity & Thought Leadership**: LinkedIn engagement analysis
- **Skills Assessment**: Technical and professional skills evaluation
- **Projects Highlights**: Most impressive project work
- **Education & Certifications**: Academic and credential analysis

## 🎨 Color-Coded Scoring System
- **🟢 Green**: Scores above 50% of category maximum (good performance)
- **🔴 Red**: Scores at or below 50% of category maximum (needs improvement)

### Score Weights:
- **Professional Experience**: 25 points (most important)
- **Skills & Market Demand**: 20 points (very important)
- **Profile Completeness**: 15 points (important)
- **Activity & Leadership**: 15 points (important)
- **Education & Certifications**: 15 points (important)
- **Career Trajectory**: 10 points (moderately important)

## 📋 Requirements
- Python 3.7+
- Flask
- OpenAI API key (for AI analysis)
- Selenium WebDriver
- BeautifulSoup4

---

## 📋 Legal Disclaimer & Terms of Use

**EDUCATIONAL AND AUTHORIZED USE ONLY**

This LinkedIn Profile Analyzer is developed and distributed solely for:
- **Educational purposes** in web development and AI integration learning
- **Professional development** and career analysis research
- **Profile optimization** and professional assessment studies
- **Personal use** on your own LinkedIn profiles

### ⚖️ Legal Compliance Requirements

**YOU MUST:**
- ✅ Obtain explicit written permission before analyzing any profile that is not your own
- ✅ Comply with all applicable local, state, federal, and international laws
- ✅ Respect LinkedIn's Terms of Service and Community Guidelines
- ✅ Use this tool only for legitimate, authorized, and legal purposes
- ✅ Ensure you have proper authorization for any security testing activities

**YOU MUST NOT:**
- ❌ Use this tool for unauthorized data collection or surveillance
- ❌ Violate any individual's privacy or LinkedIn's platform policies
- ❌ Use this tool for harassment, stalking, or malicious activities
- ❌ Access or analyze profiles without proper authorization
- ❌ Use this tool to circumvent LinkedIn's security measures for unauthorized purposes

### ⚠️ No Warranty & Limitation of Liability

This software is provided "AS IS" without warranty of any kind. The author assumes no responsibility for:
- Any misuse of this tool or violations of terms of service
- Legal consequences arising from unauthorized use
- Data accuracy or completeness of analysis results
- Any damages resulting from the use of this software

**By downloading, installing, or using this software, you agree to these terms and acknowledge that you will use it responsibly, legally, and only for authorized purposes.**

---

## 📄 License
**MIT License** - Free for educational use and professional development.  


## Author
Created by [Yaniv Haliwa](https://github.com/YanivHaliwa) for professional development and educational purposes.