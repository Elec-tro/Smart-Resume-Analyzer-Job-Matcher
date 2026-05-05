import re
import pypdf
import docx
from typing import List, Dict, Tuple

class ResumeAnalyzer:
    def __init__(self):
        # Predefined skill set (simplified)
        self.skills_dict = {
            "SDE": ["python", "java", "c++", "data structures", "algorithms", "sql", "git", "docker", "kubernetes", "aws", "microservices"],
            "Web Dev": ["javascript", "react", "html", "css", "node.js", "typescript", "vue", "angular", "tailwind", "next.js", "rest api"],
            "Data Analyst": ["python", "sql", "tableau", "power bi", "pandas", "numpy", "statistics", "machine learning", "excel", "visualization"]
        }
        
        self.all_skills = set(skill for skills in self.skills_dict.values() for skill in skills)

    def extract_text_from_pdf(self, file_path: str) -> str:
        text = ""
        with open(file_path, 'rb') as file:
            reader = pypdf.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text()
        return text

    def extract_text_from_docx(self, file_path: str) -> str:
        doc = docx.Document(file_path)
        return " ".join([para.text for para in doc.paragraphs])

    def get_extracted_skills(self, text: str) -> List[str]:
        text = text.lower()
        found_skills = []
        for skill in self.all_skills:
            # Use regex to find exact word matches
            if re.search(rf"\b{re.escape(skill)}\b", text):
                found_skills.append(skill)
        return list(set(found_skills))

    def calculate_ats_score(self, text: str, found_skills: List[str]) -> int:
        # Basic scoring logic
        # 1. Skill coverage (50 points)
        # 2. Length/Formatting (25 points) - simplified
        # 3. Contact info presence (25 points)
        
        score = 0
        
        # Skill coverage
        skill_score = min(50, len(found_skills) * 5)
        score += skill_score
        
        # Contact info (email/phone)
        has_email = bool(re.search(r'[\w\.-]+@[\w\.-]+', text))
        has_phone = bool(re.search(r'\+?\d[\d\s\-\(\)]{8,}\d', text))
        
        if has_email: score += 12
        if has_phone: score += 13
        
        # Structure check (look for headers like Education, Experience)
        headers = ["education", "experience", "projects", "skills", "summary"]
        header_count = sum(1 for h in headers if h in text.lower())
        score += min(25, header_count * 5)
        
        return min(100, score)

    def match_job_roles(self, found_skills: List[str]) -> List[Dict]:
        matches = []
        for role, role_skills in self.skills_dict.items():
            overlap = set(found_skills).intersection(set(role_skills))
            percentage = (len(overlap) / len(role_skills)) * 100 if role_skills else 0
            missing = list(set(role_skills) - set(found_skills))
            
            matches.append({
                "role": role,
                "percentage": round(percentage, 2),
                "missing_skills": missing[:5] # Show top 5 missing
            })
        
        # Sort by percentage descending
        return sorted(matches, key=lambda x: x["percentage"], reverse=True)

    def get_suggestions(self, text: str, found_skills: List[str]) -> List[str]:
        suggestions = []
        if len(found_skills) < 5:
            suggestions.append("Add more technical keywords related to your target role.")
        
        if "experience" not in text.lower():
            suggestions.append("Ensure you have a clear 'Experience' section.")
        
        if not re.search(r'[\w\.-]+@[\w\.-]+', text):
            suggestions.append("Contact email is missing or not readable.")
            
        if len(text.split()) < 200:
            suggestions.append("Your resume seems a bit short. Elaborate more on your projects and impact.")
            
        return suggestions
