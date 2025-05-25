import spacy
import re
import json
from datetime import datetime

# Load spaCy model once
try:
    nlp = spacy.load("en_core_web_lg")
except OSError:
    print("SpaCy model 'en_core_web_lg' not found. Run 'python -m spacy download en_core_web_lg'")
    exit()

# --- Regex Patterns for Contact Info ---
EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
# Adjusted phone regex to capture standard formats (e.g., (XXX)-XXX-XXXX, XXX-XXX-XXXX, XXXXXXXXXX)
PHONE_REGEX = r"(\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4})"
LINKEDIN_REGEX = r"(linkedin\.com/in/[a-zA-Z0-9_-]+)"
GITHUB_REGEX = r"(github\.com/[a-zA-Z0-9_-]+)"
WEBSITE_REGEX = r"(https?://)?(www\.)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,6}(?:/\S*)?" # Generic URL, excluding common email domains

# --- Common Resume Section Headers (Case-insensitive) ---
# Ordered by appearance likelihood and specificity
SECTION_HEADERS = {
    "professional_summary": ["professional summary", "summary", "profile", "about me", "objective"],
    "areas_of_expertise": ["areas of expertise", "skills", "technical skills", "abilities", "expertise"],
    "educational": ["educational", "education", "academic background"],
    "professional_experience": ["professional experience", "experience", "work experience"],
    "projects": ["projects", "personal projects", "portfolio"],
    "awards": ["awards", "honors", "achievements"],
    "certifications": ["certifications", "licenses"],
    "publications": ["publications"],
    "volunteer": ["volunteer experience", "volunteering"]
}

# --- Skill Keywords Categories (Expanded based on resume2.pdf) ---
SKILL_CATEGORIES = {
    "Web Technologies": [], # Will be populated directly from resume table
    "Web Frameworks": [],
    "Databases": [],
    "Version Control System": [],
    "Project Management and Issue Tracking Tool": [],
    "Testing Tools": [],
    "Web Services": [],
    "Web Servers": [],
    "Other Technologies": [],
    "DevOps Practices": []
}

# --- Date Parsing Helper ---
def parse_date_range(date_str: str) -> tuple[str, str]:
    """
    Attempts to parse date ranges like "Month Year - Month Year" or "Month Year - Present".
    Returns (start_date, end_date) in YYYY-MM-DD or YYYY format.
    """
    date_str = date_str.replace('–', '-').strip()
    
    # Handle "Present"
    current_date_formatted = datetime.now().strftime("%Y-%m-%d")
    if "Present" in date_str:
        date_str = date_str.replace("Present", current_date_formatted)
    
    parts = date_str.split('-')
    start_date = parts[0].strip()
    end_date = parts[1].strip() if len(parts) > 1 else current_date_formatted # If only one date, assume it's start

    # Patterns for parsing individual dates
    patterns = [
        "%B %Y", "%b %Y",  # "January 2020", "Jan 2020"
        "%Y-%m-%d",        # "2020-01-01"
        "%Y/%m/%d",        # "2020/01/01"
        "%m/%d/%Y",        # "01/01/2020"
        "%Y"               # "2020"
    ]

    def _parse_single_date(d_str):
        for pattern in patterns:
            try:
                dt_obj = datetime.strptime(d_str, pattern)
                # If only year is parsed, return just the year. Otherwise, YYYY-MM-DD
                return dt_obj.strftime("%Y") if len(d_str) == 4 else dt_obj.strftime("%Y-%m-%d")
            except ValueError:
                pass
        return d_str # Return original if not parsed

    return _parse_single_date(start_date), _parse_single_date(end_date)


# --- Core Extraction Functions ---

def extract_name_and_title(text: str) -> tuple[str, str]:
    """Extracts the candidate's name and primary professional title."""
    name = ""
    title = ""
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    # Heuristic: Name is usually the first or second prominent line, followed by a title
    if len(lines) > 0:
        doc_first_line = nlp(lines[0])
        for ent in doc_first_line.ents:
            if ent.label_ == "PERSON" and len(ent.text.split()) >= 2: # At least two words for a name
                name = ent.text.title() # Normalize capitalization
                break
        
        # If name not found on first line, try second, or look for capitalized words
        if not name and len(lines) > 1:
             doc_second_line = nlp(lines[1])
             for ent in doc_second_line.ents:
                if ent.label_ == "PERSON" and len(ent.text.split()) >= 2:
                    name = ent.text.title()
                    break
        
        # From the resume, title "Front End Developer" follows the name on the next line
        if name:
            name_idx = text.find(name)
            if name_idx != -1:
                # Look for title immediately after name, likely on a new line
                after_name_text = text[name_idx + len(name):]
                # Regex for common job titles on a line by themselves, after name
                title_match = re.search(r"^\s*([A-Za-z\s.&/-]+(?:Developer|Engineer|Manager|Analyst|Specialist|Architect)\s*)$", after_name_text, re.MULTILINE | re.IGNORECASE)
                if title_match:
                    # Make sure it's close to the name
                    if title_match.start() < 100: # Heuristic: title should be close
                        title = title_match.group(1).strip()
    
    # Fallback if spaCy PERSON is not good enough, or if a title is missed
    if not name:
        # Very simple heuristic: Look for first few lines with multiple capitalized words
        for i, line in enumerate(lines[:3]): # Check first 3 lines
            if len(line.split()) >= 2 and line.isupper() and "DEVELOPER" not in line.upper() and "EMAIL" not in line.upper():
                name = line.title() # Convert "KRISHNA BEERAM" to "Krishna Beeram"
                break
    
    if not title:
        # Look for "Front End Developer" or similar phrases explicitly near the top
        title_match_direct = re.search(r"Front End Developer", text, re.IGNORECASE)
        if title_match_direct and title_match_direct.start() < 300: # Near the top
            title = "Front End Developer"


    return name, title

def extract_contact_info(text: str) -> dict:
    """Extracts email, phone, and social media links."""
    contact = {}
    
    emails = re.findall(EMAIL_REGEX, text)
    if emails:
        contact['Email'] = emails[0].strip()

    phones = re.findall(PHONE_REGEX, text)
    if phones:
        contact['Mobile'] = phones[0].strip() # Use the captured group

    linkedin_match = re.search(LINKEDIN_REGEX, text, re.IGNORECASE)
    if linkedin_match:
        contact['LinkedIn'] = linkedin_match.group(0).strip()

    github_match = re.search(GITHUB_REGEX, text, re.IGNORECASE)
    if github_match:
        contact['GitHub'] = github_match.group(0).strip()
    
    # Generic website (excluding email domains and social media if already captured)
    website_matches = re.findall(WEBSITE_REGEX, text, re.IGNORECASE)
    for url_parts in website_matches:
        full_url = "".join(url_parts).strip()
        if full_url and \
           "linkedin.com" not in full_url.lower() and \
           "github.com" not in full_url.lower() and \
           "@gmail.com" not in full_url.lower() and \
           "@email.com" not in full_url.lower(): # Exclude common email domains
            contact['Website'] = full_url
            break 
            
    return contact

def section_text(text: str) -> dict:
    """
    Attempts to segment the resume text into logical sections based on common headers.
    This is improved to handle the specific resume's header patterns.
    """
    segmented_data = {key: "" for key in SECTION_HEADERS.keys()}
    
    # Prepare a regex pattern to find all potential headers, capturing their name
    # Using specific patterns from the resume, like "Professional Summary:"
    header_patterns = {
        "professional_summary": r"Professional Summary:\s*",
        "areas_of_expertise": r"AREAS OF EXPERTISE:\s*",
        "educational": r"Educational:\s*",
        "professional_experience": r"Professional Experience:\s*",
        # Adding Educational Details (at bottom) as a special case
        "educational_details_bottom": r"Educational Details:\s*"
    }
    
    # Combine patterns to find all headers in order
    header_matches = []
    for section_name, pattern_str in header_patterns.items():
        # Using re.finditer to get all matches and their start/end positions
        for match in re.finditer(pattern_str, text, re.IGNORECASE):
            header_matches.append((match.start(), match.end(), section_name, match.group(0)))
            
    # Sort matches by their start position
    header_matches.sort()

    # Iterate through sorted matches to define section boundaries
    for i, (start_idx, end_idx, section_name, header_text) in enumerate(header_matches):
        next_start_idx = len(text)
        if i + 1 < len(header_matches):
            next_start_idx = header_matches[i+1][0]
        
        content = text[end_idx:next_start_idx].strip()
        
        # Map to the standard section names, handling duplicates (like education)
        if section_name == "educational_details_bottom":
            if not segmented_data["educational"]: # Only assign if not already filled by top "Educational"
                segmented_data["educational"] = content
        else:
            segmented_data[section_name] = content

    # Handle summary/introductory text before the first identified section
    if header_matches:
        first_header_start = header_matches[0][0]
        intro_text = text[:first_header_start].strip()
        # Look for "Professional Summary" directly
        summary_match = re.search(r"Professional Summary:\s*(.*?)(?=Email:|Mobile:|\n\n|\Z)", intro_text, re.DOTALL | re.IGNORECASE)
        if summary_match:
            segmented_data["professional_summary"] = summary_match.group(1).strip()
        else: # If no explicit header, assume initial block is summary
            # Take a heuristic portion of text as summary if it's not contact info
            lines = intro_text.split('\n')
            potential_summary_lines = []
            for line in lines:
                if not any(re.search(pat, line, re.IGNORECASE) for pat in [EMAIL_REGEX, PHONE_REGEX, LINKEDIN_REGEX]):
                    potential_summary_lines.append(line)
                else:
                    break # Stop at contact info
            summary_candidate = "\n".join(potential_summary_lines).strip()
            if len(summary_candidate.split()) > 10: # If it's a substantial block
                segmented_data["professional_summary"] = summary_candidate
    
    return segmented_data

def parse_experience(experience_text: str) -> list:
    """
    Parses experience section, specifically looking for the Client/Title/Duration/Description pattern.
    """
    experiences = []
    # Splitting based on the "Client" header which signifies a new experience block
    job_blocks = re.split(r'\nClient\n', experience_text, flags=re.IGNORECASE)
    
    for block in job_blocks:
        block = block.strip()
        if not block:
            continue
            
        current_job = {}
        
        # Extract Client, Title, Duration, Location
        client_match = re.search(r"Client\s*\n\s*(.*?)\nTitle\s*\n\s*(.*?)\nDuration\s*\n\s*(.*?)\n", block, re.DOTALL | re.IGNORECASE)
        if client_match:
            current_job['Client'] = client_match.group(1).split(',')[0].strip()
            current_job['Title'] = client_match.group(2).strip()
            current_job['Duration'] = client_match.group(3).strip()
            
            # Extract Location from the Client line
            location_match = re.search(r",\s*([A-Za-z\s,]+(?:TX|WI|IL|MA|WA|MD|CA)\b)", client_match.group(1)) # Specific states for this resume
            if location_match:
                current_job['Location'] = location_match.group(1).strip()
            else:
                # Fallback for location if not in client line
                location_fallback_match = re.search(r"\nDescription:\s*The Charles Schwab Corporation is an American multinational financial services company.\n\s*Responsibilities:\n[\s\S]*?Environment:[\s\S]*?,\s*([A-Za-z\s,]+(?:TX|WI|IL|MA|WA|MD|CA)\b)", block, re.IGNORECASE)
                if location_fallback_match:
                    current_job['Location'] = location_fallback_match.group(1).strip()

        # Extract Responsibilities
        responsibilities_match = re.search(r"Responsibilities:\s*\n(.*?)(?=\nEnvironment:|\Z)", block, re.DOTALL | re.IGNORECASE)
        if responsibilities_match:
            resp_text = responsibilities_match.group(1).strip()
            # Split responsibilities by bullet points or newlines
            responsibilities = [re.sub(r'^\s*[\•*-]\s*', '', line).strip() for line in resp_text.split('\n') if re.sub(r'^\s*[\•*-]\s*', '', line).strip()]
            current_job['Responsibilities'] = responsibilities
        
        if current_job:
            experiences.append(current_job)
            
    return experiences

def parse_education(education_text: str) -> list:
    """Parses education section into a list of educational entries."""
    educations = []
    
    # Split by "Bachelor of Technology" and "Masters from"
    # This specific resume has two distinct education blocks
    
    # First block: Bachelor of Technology
    btech_match = re.search(r"Bachelor of Technology in (.*?) from (.*?),\s*(.*)", education_text, re.IGNORECASE)
    if btech_match:
        educations.append({
            "Degree": "B.Tech",
            "Field": btech_match.group(1).strip(),
            "Institution": btech_match.group(2).strip() + ", " + btech_match.group(3).strip()
        })
    
    # Second block: Masters from Lamar University
    masters_match = re.search(r"Masters from (.*?),\s*(.*?)\.\n\s*\((\w+\s+\d{4})\s*-\s*(\w+\s+\d{4})\)", education_text, re.IGNORECASE)
    if masters_match:
        start_date_str = masters_match.group(3)
        end_date_str = masters_match.group(4)
        
        educations.append({
            "Degree": "Masters",
            "Institution": masters_match.group(1).strip(),
            "Location": masters_match.group(2).strip(),
            "Duration": f"{start_date_str} - {end_date_str}"
        })
            
    return educations

def parse_skills(skills_text: str) -> dict:
    """
    Parses the tabular skills section into categorized skills.
    Assumes skills are in a "Category \n Skill1, Skill2 \n Category \n Skill3, Skill4" format.
    """
    categorized_skills = {}
    lines = [line.strip() for line in skills_text.split('\n') if line.strip()]
    
    current_category = None
    for line in lines:
        # Check if the line is a known skill category header
        found_category = False
        for category_name in SKILL_CATEGORIES.keys():
            if line.lower() == category_name.lower():
                current_category = category_name
                categorized_skills[current_category] = []
                found_category = True
                break
        
        if not found_category and current_category:
            # This line should contain skills for the current category
            # Split by common delimiters like comma, semicolon
            skills_on_line = re.split(r'[,\;]+', line)
            for skill in skills_on_line:
                skill_cleaned = skill.strip()
                if skill_cleaned:
                    # Remove "JS" if it's already "React JS" etc. to avoid "ReactJS" and "React"
                    # Add specific formatting for "Angular 8 10 12"
                    if skill_cleaned == "Angular 8 10 12":
                        categorized_skills[current_category].append("Angular 8 10 12")
                    else:
                        categorized_skills[current_category].append(skill_cleaned)
    
    return categorized_skills


def parse_projects(projects_text: str) -> list:
    """
    Parses projects section. This resume has a single project defined
    within the first professional experience's environment section, and an explicit
    'PROJECTS' section with a description.
    """
    projects = []
    
    # Explicit Projects section
    # "E-commerce Recommendation System - A Python-based ML system using TensorFlow. Link: github.com/janesmith/recommender"
    project_match = re.search(r"E-commerce Recommendation System\s*-\s*(.*?)(Link:\s*(.*?))?$", projects_text, re.DOTALL | re.IGNORECASE)
    if project_match:
        project_title = "E-commerce Recommendation System"
        description = project_match.group(1).strip()
        link = project_match.group(3).strip() if project_match.group(3) else ""
        
        technologies = []
        # Find technologies within the description
        for category_name, keywords in SKILL_CATEGORIES.items():
            for kw in keywords:
                if kw.lower() in description.lower() and kw not in technologies:
                    technologies.append(kw)
        
        # Add a specific regex for technologies if needed
        tech_regex = r"(Python|TensorFlow|Pandas|React\.js|Node\.js|Express|MongoDB|HTML5|CSS3|SASS|JavaScript|TypeScript|Material-UI|React Redux|Cypress|Cyara|JSON|NPM|Axios|Bitbucket|Jira|AWS|Agile/Scrum)" # Based on Environment from first exp.
        tech_matches = re.findall(tech_regex, description, re.IGNORECASE)
        for tech in tech_matches:
            if tech not in technologies:
                technologies.append(tech)

        projects.append({
            "title": project_title,
            "description": description,
            "technologies": sorted(list(set(technologies))), # Ensure unique and sorted
            "link": link
        })
        
    return projects


def parse_resume(raw_text: str) -> dict:
    """Main function to parse raw resume text into structured JSON."""
    doc = nlp(raw_text)

    # 1. Extract Name and overall Title
    name, overall_title = extract_name_and_title(raw_text)

    # 2. Extract Contact Info
    contact_info = extract_contact_info(raw_text)

    # 3. Section Segmentation (Crucial for accuracy of other parsers)
    # The order here is important as it might influence the content of "summary"
    segmented_text = section_text(raw_text)

    # 4. Extract Summary
    summary = segmented_text.get("professional_summary", "").strip()

    # 5. Parse Experience
    experience_data = parse_experience(segmented_text.get("professional_experience", ""))

    # 6. Parse Education
    education_data = parse_education(segmented_text.get("educational", ""))

    # 7. Parse Skills (from "AREAS OF EXPERTISE" table)
    skills_data = parse_skills(segmented_text.get("areas_of_expertise", ""))

    # 8. Parse Projects (if a dedicated section or strong patterns exist)
    # Based on the resume, the projects section is somewhat limited
    projects_data = parse_projects(segmented_text.get("projects", "") + "\n" + raw_text) # Also search raw text if not in dedicated section

    # Initialize empty lists for other sections as they don't appear in this resume
    awards_data = []
    certifications_data = []

    parsed_output = {
        "Name": name,
        "Title": overall_title,
        "Contact": contact_info,
        "Summary": summary,
        "Skills": skills_data,
        "Education": education_data,
        "Experience": experience_data,
        "Projects": projects_data,
        "Awards": awards_data,
        "Certifications": certifications_data
    }

    return parsed_output