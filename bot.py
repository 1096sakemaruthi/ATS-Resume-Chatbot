import os
import re
import tempfile
import traceback

from dotenv import load_dotenv
from pypdf import PdfReader
from docx import Document

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file")


# ============================================================
# STORAGE
# ============================================================

user_resumes = {}
user_jobs = {}
user_states = {}


# ============================================================
# SAFE TELEGRAM MESSAGE
# ============================================================

async def send_report(update, message):
    """
    Try Markdown first.
    If Telegram Markdown parsing fails,
    automatically send as normal text.
    """

    try:
        await update.message.reply_text(
            message,
            parse_mode="Markdown",
        )

    except Exception as e:
        print("Markdown error:", e)

        try:
            plain_message = message.replace("*", "")
            plain_message = plain_message.replace("_", "")

            await update.message.reply_text(
                plain_message
            )

        except Exception as second_error:
            print("Fallback message error:", second_error)


# ============================================================
# DOCUMENT TEXT EXTRACTION
# ============================================================

def extract_pdf_text(file_path):

    text = ""

    try:
        reader = PdfReader(file_path)

        for page in reader.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    except Exception as e:

        print("PDF extraction error:", e)

    return text


def extract_docx_text(file_path):

    text = ""

    try:

        document = Document(file_path)

        for paragraph in document.paragraphs:

            if paragraph.text:
                text += paragraph.text + "\n"

    except Exception as e:

        print("DOCX extraction error:", e)

    return text


def extract_txt_text(file_path):

    text = ""

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as file:

            text = file.read()

    except Exception as e:

        print("TXT extraction error:", e)

    return text


def extract_document_text(file_path, filename):

    extension = os.path.splitext(
        filename
    )[1].lower()

    if extension == ".pdf":
        return extract_pdf_text(file_path)

    if extension == ".docx":
        return extract_docx_text(file_path)

    if extension == ".txt":
        return extract_txt_text(file_path)

    return ""


# ============================================================
# DOCUMENT TYPE VALIDATION
# ============================================================

def is_likely_resume(text):

    text = text.lower()

    resume_indicators = [
        "resume",
        "curriculum vitae",
        "career objective",
        "professional summary",
        "work experience",
        "professional experience",
        "education",
        "projects",
        "certifications",
        "technical skills",
        "skills",
        "internship",
        "internships",
        "achievements",
        "contact",
        "email",
        "phone",
        "linkedin",
        "github",
    ]

    count = sum(
        1
        for indicator in resume_indicators
        if indicator in text
    )

    return count >= 4


def is_likely_job_description(text):

    text = text.lower()

    jd_indicators = [
        "job description",
        "job title",
        "position",
        "role",
        "responsibilities",
        "requirements",
        "required skills",
        "mandatory skills",
        "preferred skills",
        "must have",
        "good to have",
        "nice to have",
        "qualifications",
        "what you will do",
        "what you'll do",
        "we are looking for",
        "years of experience",
    ]

    count = sum(
        1
        for indicator in jd_indicators
        if indicator in text
    )

    return count >= 2


# ============================================================
# COMMON DATA
# ============================================================

SKILLS = [
    "python",
    "java",
    "c",
    "c++",
    "javascript",
    "typescript",
    "react",
    "angular",
    "html",
    "css",
    "sql",
    "mysql",
    "postgresql",
    "mongodb",
    "git",
    "github",
    "spring boot",
    "spring",
    "machine learning",
    "deep learning",
    "data structures",
    "aws",
    "azure",
    "gcp",
    "docker",
    "kubernetes",
    "terraform",
    "rest api",
    "api",
    "linux",
    "jenkins",
    "redis",
    "kafka",
]

TOOLS = [
    "git",
    "github",
    "docker",
    "kubernetes",
    "terraform",
    "jenkins",
    "aws",
    "azure",
    "gcp",
    "mysql",
    "postgresql",
    "mongodb",
    "redis",
    "kafka",
]

EDUCATION_WORDS = [
    "education",
    "b.tech",
    "btech",
    "bachelor",
    "degree",
    "college",
    "university",
    "engineering",
    "computer science",
    "m.tech",
    "mtech",
    "b.sc",
    "bsc",
]

EXPERIENCE_WORDS = [
    "experience",
    "internship",
    "intern",
    "developer",
    "worked",
    "employment",
    "professional experience",
]

PROJECT_WORDS = [
    "project",
    "projects",
    "developed",
    "implemented",
    "application",
    "system",
]

KEYWORDS = [
    "problem solving",
    "communication",
    "teamwork",
    "leadership",
    "analytical",
    "agile",
    "api",
    "database",
    "software development",
    "testing",
]


# ============================================================
# SKILL NORMALIZATION
# ============================================================

SKILL_NORMALIZATION = {
    "k8s": "kubernetes",
    "eks": "amazon eks",
    "aks": "azure kubernetes service",
    "gke": "google kubernetes engine",
    "amazon web services": "aws",
    "microsoft azure": "azure",
    "google cloud platform": "gcp",
    "terraform iac": "terraform",
    "structured query language": "sql",
}


def normalize_skill(skill):

    skill = skill.lower().strip()

    return SKILL_NORMALIZATION.get(
        skill,
        skill
    )


def extract_skills(text):

    text = text.lower()

    found = []

    for skill in SKILLS:

        if skill in text:

            normalized = normalize_skill(skill)

            if normalized not in found:
                found.append(normalized)

    return found


# ============================================================
# YEARS OF EXPERIENCE
# ============================================================

def extract_years_experience(text):

    text = text.lower()

    patterns = [
        r"(\d+(?:\.\d+)?)\+?\s*years?\s*(?:of)?\s*experience",
        r"(\d+(?:\.\d+)?)\+?\s*years?\s*experience",
    ]

    years = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text
        )

        for match in matches:

            try:
                years.append(float(match))

            except ValueError:
                pass

    if not years:
        return 0

    return max(years)


# ============================================================
# ORIGINAL ATS SCORE
# ============================================================

def calculate_original_score(text):

    if not text.strip():

        return {
            "total": 0,
            "criteria": {},
            "suggestions": [],
            "courses": [],
        }

    text = text.lower()

    criteria = {}

    skill_count = sum(
        1
        for skill in SKILLS
        if skill in text
    )

    skills_score = min(
        25,
        round((skill_count / 8) * 25)
    )

    criteria["Skills"] = skills_score

    education_found = sum(
        1
        for word in EDUCATION_WORDS
        if word in text
    )

    education_score = (
        15
        if education_found >= 2
        else 8
        if education_found == 1
        else 0
    )

    criteria["Education"] = education_score

    experience_found = sum(
        1
        for word in EXPERIENCE_WORDS
        if word in text
    )

    experience_score = (
        20
        if experience_found >= 2
        else 10
        if experience_found == 1
        else 0
    )

    criteria["Experience"] = experience_score

    project_found = sum(
        1
        for word in PROJECT_WORDS
        if word in text
    )

    project_score = (
        15
        if project_found >= 3
        else 8
        if project_found >= 1
        else 0
    )

    criteria["Projects"] = project_score

    keyword_count = sum(
        1
        for word in KEYWORDS
        if word in text
    )

    keyword_score = min(
        15,
        round((keyword_count / 5) * 15)
    )

    criteria["Keywords"] = keyword_score

    structure_words = [
        "summary",
        "objective",
        "skills",
        "education",
        "projects",
        "certifications",
        "contact",
    ]

    structure_count = sum(
        1
        for word in structure_words
        if word in text
    )

    structure_score = (
        10
        if structure_count >= 6
        else 7
        if structure_count >= 4
        else 4
        if structure_count >= 2
        else 0
    )

    criteria["Resume Structure"] = structure_score

    total = sum(criteria.values())

    suggestions = []

    if skills_score < 20:

        suggestions.append(
            "Add more relevant technical skills and tools."
        )

    if experience_score < 15:

        suggestions.append(
            "Add internship, training, or practical experience details."
        )

    if project_score < 10:

        suggestions.append(
            "Add 1-2 strong projects with technologies and measurable results."
        )

    if keyword_score < 10:

        suggestions.append(
            "Add job-relevant keywords such as API, SQL, Git, testing, and teamwork."
        )

    if structure_score < 7:

        suggestions.append(
            "Improve resume structure with clear sections and headings."
        )

    suggestions = suggestions[:3]

    courses = []

    if "python" not in text:
        courses.append("Python Programming Certification")

    if "sql" not in text:
        courses.append("SQL and Database Certification")

    if "git" not in text:
        courses.append("Git and GitHub Certification")

    if "cloud" not in text:
        courses.append("Cloud Computing Fundamentals")

    if "machine learning" not in text:
        courses.append("Machine Learning Fundamentals")

    courses = courses[:3]

    return {
        "total": total,
        "criteria": criteria,
        "suggestions": suggestions,
        "courses": courses,
    }


# ============================================================
# JD ANALYSIS
# ============================================================

def analyze_job_description(text):

    text = text.lower()

    skills = extract_skills(text)

    years = extract_years_experience(text)

    mandatory_skills = []

    preferred_skills = []

    mandatory_words = [
        "mandatory",
        "must have",
        "required",
        "must",
        "essential",
    ]

    preferred_words = [
        "preferred",
        "good to have",
        "nice to have",
        "optional",
    ]

    for skill in skills:

        position = text.find(skill)

        if position == -1:
            continue

        nearby_text = text[
            max(0, position - 100):
            min(len(text), position + 100)
        ]

        mandatory = any(
            word in nearby_text
            for word in mandatory_words
        )

        preferred = any(
            word in nearby_text
            for word in preferred_words
        )

        if mandatory:

            if skill not in mandatory_skills:
                mandatory_skills.append(skill)

        elif preferred:

            if skill not in preferred_skills:
                preferred_skills.append(skill)

    if not mandatory_skills:

        mandatory_skills = skills[:5]

    preferred_skills = [
        skill
        for skill in preferred_skills
        if skill not in mandatory_skills
    ]

    job_title = "Not Specified"

    title_patterns = [
        r"job title\s*[:\-]\s*(.+)",
        r"position\s*[:\-]\s*(.+)",
        r"role\s*[:\-]\s*(.+)",
    ]

    for pattern in title_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            job_title = match.group(1).strip()

            break

    return {
        "job_title": job_title,
        "skills": skills,
        "mandatory_skills": mandatory_skills,
        "preferred_skills": preferred_skills,
        "required_years": years,
        "education_required": any(
            word in text
            for word in EDUCATION_WORDS
        ),
        "raw_text": text,
    }


# ============================================================
# JD BASED SCORE
# ============================================================

def calculate_jd_score(resume_text, job):

    resume_text = resume_text.lower()

    resume_skills = extract_skills(resume_text)

    jd_skills = job["skills"]

    mandatory_skills = job["mandatory_skills"]

    preferred_skills = job["preferred_skills"]

    criteria = {}

    # Technical Skills - 25
    if jd_skills:

        matched = sum(
            1
            for skill in jd_skills
            if skill in resume_skills
        )

        technical_score = round(
            (matched / len(jd_skills)) * 25
        )

    else:

        technical_score = 25

    criteria["Technical Skills Match"] = technical_score

    # Responsibilities - 20
    responsibility_words = [
        "responsibilities",
        "develop",
        "design",
        "implement",
        "maintain",
        "test",
        "support",
        "analyze",
        "build",
    ]

    jd_responsibilities = sum(
        1
        for word in responsibility_words
        if word in job["raw_text"]
    )

    resume_responsibilities = sum(
        1
        for word in responsibility_words
        if word in resume_text
    )

    if jd_responsibilities == 0:

        responsibility_score = 20

    else:

        ratio = min(
            1,
            resume_responsibilities /
            jd_responsibilities
        )

        responsibility_score = round(
            ratio * 20
        )

    criteria["Responsibilities Match"] = responsibility_score

    # Relevant Experience - 15
    relevant_experience = sum(
        1
        for word in EXPERIENCE_WORDS
        if word in resume_text
    )

    experience_score = (
        15
        if relevant_experience >= 3
        else 10
        if relevant_experience >= 1
        else 0
    )

    criteria["Relevant Experience"] = experience_score

    # Years Experience - 10
    resume_years = extract_years_experience(
        resume_text
    )

    required_years = job["required_years"]

    if required_years <= 0:

        years_score = 10

    elif resume_years >= required_years:

        years_score = 10

    elif resume_years > 0:

        years_score = round(
            (resume_years / required_years) * 10
        )

    else:

        years_score = 0

    criteria["Years Experience"] = years_score

    # Domain - 10
    domain_words = [
        "software",
        "technology",
        "information technology",
        "computer science",
        "fintech",
        "healthcare",
        "ecommerce",
        "education",
        "banking",
        "cloud",
        "ai",
        "machine learning",
    ]

    jd_domain_words = [
        word
        for word in domain_words
        if word in job["raw_text"]
    ]

    if not jd_domain_words:

        domain_score = 10

    else:

        matched_domains = sum(
            1
            for word in jd_domain_words
            if word in resume_text
        )

        domain_score = round(
            (
                matched_domains /
                len(jd_domain_words)
            ) * 10
        )

    criteria["Domain Experience"] = domain_score

    # Education - 5
    if job["education_required"]:

        education_score = (
            5
            if any(
                word in resume_text
                for word in EDUCATION_WORDS
            )
            else 0
        )

    else:

        education_score = 5

    criteria["Education"] = education_score

    # Certifications - 5
    certification_words = [
        "certification",
        "certified",
        "certificate",
        "course",
    ]

    certification_found = sum(
        1
        for word in certification_words
        if word in resume_text
    )

    certification_score = (
        5
        if certification_found >= 1
        else 0
    )

    criteria["Certifications"] = certification_score

    # Tools - 5
    jd_tools = [
        tool
        for tool in TOOLS
        if tool in job["raw_text"]
    ]

    if not jd_tools:

        tools_score = 5

    else:

        matched_tools = sum(
            1
            for tool in jd_tools
            if tool in resume_text
        )

        tools_score = round(
            (matched_tools / len(jd_tools)) * 5
        )

    criteria["Tools/Technology Match"] = tools_score

    # Role - 5
    role_words = [
        "developer",
        "engineer",
        "software engineer",
        "intern",
        "internship",
        "analyst",
        "administrator",
        "manager",
        "associate",
    ]

    jd_roles = [
        word
        for word in role_words
        if word in job["raw_text"]
    ]

    if not jd_roles:

        seniority_score = 5

    else:

        role_matches = sum(
            1
            for role in jd_roles
            if role in resume_text
        )

        seniority_score = (
            5
            if role_matches >= 1
            else 0
        )

    criteria["Seniority/Role Alignment"] = seniority_score

    # Mandatory requirements
    missing_mandatory = [
        skill
        for skill in mandatory_skills
        if skill not in resume_skills
    ]

    if missing_mandatory:

        penalty = min(
            20,
            len(missing_mandatory) * 5
        )

        criteria["Technical Skills Match"] = max(
            0,
            criteria["Technical Skills Match"] - penalty
        )

    total = sum(criteria.values())

    # Strengths
    strengths = []

    matched_mandatory = [
        skill
        for skill in mandatory_skills
        if skill in resume_skills
    ]

    if matched_mandatory:

        strengths.append(
            "Mandatory skills matched: "
            + ", ".join(matched_mandatory[:5])
        )

    if technical_score >= 18:

        strengths.append(
            "Strong technical skill alignment with the job."
        )

    if experience_score >= 10:

        strengths.append(
            "Relevant experience is present."
        )

    strengths = strengths[:3]

    # Gaps
    gaps = []

    if missing_mandatory:

        gaps.append(
            "Missing mandatory skills: "
            + ", ".join(missing_mandatory[:5])
        )

    missing_preferred = [
        skill
        for skill in preferred_skills
        if skill not in resume_skills
    ]

    if missing_preferred:

        gaps.append(
            "Missing preferred skills: "
            + ", ".join(missing_preferred[:5])
        )

    if required_years > 0 and resume_years < required_years:

        gaps.append(
            f"Required experience: {required_years} years; "
            f"detected approximately {resume_years} years."
        )

    gaps = gaps[:3]

    # ========================================================
    # Exactly 3 JD + Candidate Gap Based Certifications
    # ========================================================

    missing_skills_for_certification = []

    for skill in missing_mandatory:

        if skill not in missing_skills_for_certification:
            missing_skills_for_certification.append(skill)

    for skill in missing_preferred:

        if skill not in missing_skills_for_certification:
            missing_skills_for_certification.append(skill)

    certification_map = {
        "python": (
            "Python Programming Certification",
            "Improves Python skills required for the role."
        ),
        "java": (
            "Java Programming Certification",
            "Improves Java skills required for the role."
        ),
        "c": (
            "C Programming Certification",
            "Improves C programming skills required for the role."
        ),
        "c++": (
            "C++ Programming Certification",
            "Improves C++ skills required for the role."
        ),
        "javascript": (
            "JavaScript Programming Certification",
            "Improves JavaScript skills required for the role."
        ),
        "typescript": (
            "TypeScript Certification",
            "Improves TypeScript skills required for the role."
        ),
        "react": (
            "React.js Certification",
            "Improves React skills required for the role."
        ),
        "angular": (
            "Angular Certification",
            "Improves Angular skills required for the role."
        ),
        "sql": (
            "SQL and Database Certification",
            "Improves SQL skills required for the role."
        ),
        "mysql": (
            "MySQL Database Certification",
            "Improves MySQL skills required for the role."
        ),
        "postgresql": (
            "PostgreSQL Certification",
            "Improves PostgreSQL skills required for the role."
        ),
        "mongodb": (
            "MongoDB Certification",
            "Improves MongoDB skills required for the role."
        ),
        "git": (
            "Git and GitHub Certification",
            "Improves Git and version control skills required for the role."
        ),
        "github": (
            "GitHub Certification",
            "Improves GitHub and collaboration skills required for the role."
        ),
        "spring boot": (
            "Spring Boot Certification",
            "Improves Spring Boot skills required for the role."
        ),
        "spring": (
            "Spring Framework Certification",
            "Improves Spring skills required for the role."
        ),
        "machine learning": (
            "Machine Learning Certification",
            "Improves Machine Learning skills required for the role."
        ),
        "deep learning": (
            "Deep Learning Certification",
            "Improves Deep Learning skills required for the role."
        ),
        "aws": (
            "AWS Certified Cloud Practitioner",
            "Improves AWS knowledge required for the role."
        ),
        "azure": (
            "Microsoft Azure Fundamentals Certification",
            "Improves Azure knowledge required for the role."
        ),
        "gcp": (
            "Google Cloud Fundamentals Certification",
            "Improves GCP knowledge required for the role."
        ),
        "docker": (
            "Docker Certification",
            "Improves Docker skills required for the role."
        ),
        "kubernetes": (
            "Kubernetes Certification",
            "Improves Kubernetes skills required for the role."
        ),
        "terraform": (
            "Terraform Certification",
            "Improves Terraform skills required for the role."
        ),
        "rest api": (
            "REST API Certification",
            "Improves REST API skills required for the role."
        ),
        "api": (
            "API Development Certification",
            "Improves API development skills required for the role."
        ),
        "linux": (
            "Linux Administration Certification",
            "Improves Linux skills required for the role."
        ),
        "jenkins": (
            "Jenkins CI/CD Certification",
            "Improves Jenkins and CI/CD skills required for the role."
        ),
        "redis": (
            "Redis Certification",
            "Improves Redis skills required for the role."
        ),
        "kafka": (
            "Apache Kafka Certification",
            "Improves Kafka skills required for the role."
        ),
    }

    courses = []

    # First use candidate skill gaps
    for skill in missing_skills_for_certification:

        if skill in certification_map:

            name, reason = certification_map[skill]

            courses.append(
                {
                    "name": name,
                    "reason": reason,
                    "skill_gap": skill,
                    "jd_relevance": (
                        f"{skill.upper()} is mentioned in the Job Description."
                    ),
                }
            )

        if len(courses) == 3:
            break

    # If fewer than 3 gaps have mapped certifications,
    # use other JD skills to keep recommendations relevant
    if len(courses) < 3:

        for skill in jd_skills:

            if skill in resume_skills:
                continue

            if skill not in certification_map:
                continue

            if any(
                course["skill_gap"] == skill
                for course in courses
            ):
                continue

            name, reason = certification_map[skill]

            courses.append(
                {
                    "name": name,
                    "reason": reason,
                    "skill_gap": skill,
                    "jd_relevance": (
                        f"{skill.upper()} is part of the Job Description requirements."
                    ),
                }
            )

            if len(courses) == 3:
                break

    # Final fallback only when JD has fewer than 3
    # certifiable technical skills
    fallback_certifications = [
        (
            "Technical Skills Certification",
            "Improves technical skills required for the role.",
            "Technical skills",
            "Supports the technical requirements identified in the Job Description."
        ),
        (
            "Software Development Certification",
            "Improves software development skills required for the role.",
            "Software development",
            "Supports the software development responsibilities in the Job Description."
        ),
        (
            "Professional Technology Certification",
            "Improves technical knowledge required for the role.",
            "Technical knowledge",
            "Supports the overall technical requirements of the Job Description."
        ),
    ]

    fallback_index = 0

    while len(courses) < 3 and fallback_index < len(fallback_certifications):

        name, reason, skill_gap, jd_relevance = (
            fallback_certifications[fallback_index]
        )

        if not any(
            course["name"] == name
            for course in courses
        ):

            courses.append(
                {
                    "name": name,
                    "reason": reason,
                    "skill_gap": skill_gap,
                    "jd_relevance": jd_relevance,
                }
            )

        fallback_index += 1

    return {
        "total": total,
        "criteria": criteria,
        "missing_mandatory": missing_mandatory,
        "strengths": strengths,
        "gaps": gaps,
        "courses": courses[:3],
        "mandatory_satisfied": len(missing_mandatory) == 0,
        "resume_years": resume_years,
    }


# ============================================================
# ORIGINAL REPORT
# ============================================================

def create_report(filename, result):

    safe_filename = (
        filename
        .replace("_", "\\_")
        .replace("*", "\\*")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )

    message = f"""
📄 *Resume ATS Analysis*

📌 *Resume:* {safe_filename}

🎯 *ATS Score: {result['total']}%*

━━━━━━━━━━━━━━━━━━

📊 *Criteria & Weightage*

"""

    for criterion, score in result["criteria"].items():

        message += (
            f"• {criterion}: {score}%\n"
        )

    message += """
━━━━━━━━━━━━━━━━━━

💡 *Top Improvements*
"""

    if result["suggestions"]:

        for i, suggestion in enumerate(
            result["suggestions"],
            1
        ):

            message += (
                f"{i}. {suggestion}\n"
            )

    else:

        message += (
            "No major improvements detected.\n"
        )

    message += """
━━━━━━━━━━━━━━━━━━

🎓 *Suggested Courses / Certifications*
"""

    if result["courses"]:

        for i, course in enumerate(
            result["courses"],
            1
        ):

            message += (
                f"{i}. {course}\n"
            )

    else:

        message += (
            "Your resume already contains several relevant skills.\n"
        )

    message += """
━━━━━━━━━━━━━━━━━━

🤖 *Maruthi Chatbot*
Resume screening and comparison assistant.
"""

    return message


# ============================================================
# JD REPORT
# ============================================================

def create_jd_report(filename, result):

    safe_filename = (
        filename
        .replace("_", "\\_")
        .replace("*", "\\*")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )

    # Maximum weightage for each criterion
    weightage = {
        "Technical Skills Match": 25,
        "Responsibilities Match": 20,
        "Relevant Experience": 15,
        "Years Experience": 10,
        "Domain Experience": 10,
        "Education": 5,
        "Certifications": 5,
        "Tools/Technology Match": 5,
        "Seniority/Role Alignment": 5,
    }

    message = f"""
📄 *Candidate Analysis*

📌 *Resume:* {safe_filename}

🎯 *JD Match Score: {result['total']}/100*

━━━━━━━━━━━━━━━━━━

🧮 *How the ATS Score is Calculated*

Each criterion has a fixed maximum weightage.
The candidate gets points based on the JD and resume match.

"""

    for criterion, score in result["criteria"].items():

        maximum = weightage.get(
            criterion,
            score
        )

        message += (
            f"• {criterion}: {score}/{maximum}\n"
        )

    # ========================================================
    # Total Score Calculation section REMOVED
    # ========================================================

    message += f"""
━━━━━━━━━━━━━━━━━━

🎯 *Final ATS Score: {result['total']}/100*

The final score is the sum of all weighted criteria.

━━━━━━━━━━━━━━━━━━

💪 *Strengths*
"""

    if result["strengths"]:

        for strength in result["strengths"]:

            message += (
                f"• {strength}\n"
            )

    else:

        message += (
            "• No major strengths detected from the available text.\n"
        )

    message += """
━━━━━━━━━━━━━━━━━━

⚠️ *Missing Skills / Gaps*
"""

    if result["gaps"]:

        for gap in result["gaps"]:

            message += (
                f"• {gap}\n"
            )

    else:

        message += (
            "• No major gaps detected.\n"
        )

    message += """
━━━━━━━━━━━━━━━━━━

🎓 *Exactly 3 Certification Recommendations*
"""

    for index, course in enumerate(
        result["courses"],
        1
    ):

        message += (
            f"{index}. *{course['name']}*\n"
            f"   Reason: {course['reason']}\n\n"
        )

    message += """
━━━━━━━━━━━━━━━━━━

🤖 *Maruthi Chatbot*
JD-based ATS recruitment assistant.
"""

    return message


# ============================================================
# START
# ============================================================

async def start(update, context):

    user_id = update.effective_user.id

    user_states[user_id] = "START"

    await update.message.reply_text(
        """
👋 *Welcome to Maruthi Chatbot!*

🤖 AI-powered ATS recruitment chatbot.

📋 Job Description Analysis
📄 Resume Analysis
📊 ATS Scoring
🔎 Skill Matching
⚠️ Missing Skill Detection
🏆 Candidate Comparison
🎓 Certification Recommendations

━━━━━━━━━━━━━━━━━━

*Quick Resume Analysis*

Upload:
• PDF
• DOCX
• TXT

━━━━━━━━━━━━━━━━━━

*JD Based Recruitment*

1️⃣ /newjob

2️⃣ Upload Job Description

3️⃣ Upload one or multiple resumes

4️⃣ /rank

━━━━━━━━━━━━━━━━━━

📌 Commands:

/start
/newjob
/upload_jd
/upload_resumes
/rank
/details
/compare
/recommendations
/gaps
/report
/reset
/help
/clear
""",
        parse_mode="Markdown",
    )


# ============================================================
# NEW JOB
# ============================================================

async def new_job(update, context):

    user_id = update.effective_user.id

    user_jobs.pop(
        user_id,
        None
    )

    user_resumes.pop(
        user_id,
        None
    )

    user_states[user_id] = "WAITING_FOR_JD"

    await update.message.reply_text(
        """
📋 *New Recruitment Job Started*

Please upload the *Job Description*.

Supported:

📄 PDF
📝 DOCX
📃 TXT
""",
        parse_mode="Markdown",
    )


# ============================================================
# UPLOAD JD
# ============================================================

async def upload_jd(update, context):

    user_id = update.effective_user.id

    user_states[user_id] = "WAITING_FOR_JD"

    await update.message.reply_text(
        """
📋 *Upload Job Description*

Supported:

• PDF
• DOCX
• TXT
""",
        parse_mode="Markdown",
    )


# ============================================================
# DOCUMENT HANDLER
# ============================================================

async def handle_document(update, context):

    document = update.message.document

    if not document:
        return

    filename = (
        document.file_name
        or "document.pdf"
    )

    extension = os.path.splitext(
        filename
    )[1].lower()

    supported = [
        ".pdf",
        ".docx",
        ".txt",
    ]

    if extension not in supported:

        await update.message.reply_text(
            "❌ Supported formats are PDF, DOCX and TXT."
        )

        return

    user_id = update.effective_user.id

    state = user_states.get(
        user_id,
        "START"
    )

    # ========================================================
    # JD UPLOAD
    # ========================================================

    if state == "WAITING_FOR_JD":

        await update.message.reply_text(
            "⏳ Job Description received. Analyzing requirements..."
        )

        temp_path = None

        try:

            telegram_file = await document.get_file()

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=extension
            ) as temp_file:

                temp_path = temp_file.name

            await telegram_file.download_to_drive(
                custom_path=temp_path
            )

            text = extract_document_text(
                temp_path,
                filename
            )

            if temp_path and os.path.exists(temp_path):

                try:
                    os.remove(temp_path)
                except Exception:
                    pass

            if not text.strip():

                await update.message.reply_text(
                    "❌ I could not extract text from this Job Description."
                )

                return

            # ====================================================
            # NEW VALIDATION:
            # Resume uploaded where JD is expected
            # ====================================================

            if is_likely_resume(text) and not is_likely_job_description(text):

                await update.message.reply_text(
                    """
❌ *Wrong document.*

You are currently at the *Job Description* stage.

📋 Please upload a *Job Description* only.

A resume was detected, so it was not accepted.

Supported:
• PDF
• DOCX
• TXT
""",
                    parse_mode="Markdown",
                )

                return

            job = analyze_job_description(
                text
            )

            user_jobs[user_id] = job

            user_resumes[user_id] = []

            user_states[user_id] = (
                "WAITING_FOR_RESUMES"
            )

            await update.message.reply_text(
                f"""
✅ *Job Description Ready*

📌 Job Title: {job['job_title']}

🛠 Skills detected: {len(job['skills'])}

🔴 Mandatory skills:
{', '.join(job['mandatory_skills']) if job['mandatory_skills'] else 'Not specified'}

🟡 Preferred skills:
{', '.join(job['preferred_skills']) if job['preferred_skills'] else 'Not specified'}

🎓 Required experience:
{job['required_years']} years

━━━━━━━━━━━━━━━━━━

Now upload one or multiple candidate resumes.

After uploading use:

/rank
""",
                parse_mode="Markdown",
            )

        except Exception as e:

            print("JD document error:")
            traceback.print_exc()

            await update.message.reply_text(
                f"❌ JD analysis error: {str(e)}"
            )

        return

    # ========================================================
    # RESUME UPLOAD
    # ========================================================

    if state != "WAITING_FOR_RESUMES" and user_id not in user_jobs:

        await update.message.reply_text(
            """
⚠️ *Please follow the correct recruitment flow.*

First use:

/newjob

Then upload the Job Description.

After the Job Description is ready,
upload candidate resumes.
""",
            parse_mode="Markdown",
        )

        return

    await update.message.reply_text(
        "⏳ Resume received. Analyzing your resume..."
    )

    temp_path = None

    try:

        telegram_file = await document.get_file()

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension
        ) as temp_file:

            temp_path = temp_file.name

        await telegram_file.download_to_drive(
            custom_path=temp_path
        )

        text = extract_document_text(
            temp_path,
            filename
        )

        if temp_path and os.path.exists(temp_path):

            try:
                os.remove(temp_path)
            except Exception:
                pass

        if not text.strip():

            await update.message.reply_text(
                "❌ I could not extract text from this document."
            )

            return

        # ====================================================
        # NEW VALIDATION:
        # JD uploaded where Resume is expected
        # ====================================================

        if is_likely_job_description(text) and not is_likely_resume(text):

            await update.message.reply_text(
                """
❌ *Wrong document.*

The Job Description is already uploaded.

📄 Please upload a *candidate resume* now.

Supported:
• PDF
• DOCX
• TXT

This document was not added as a candidate.
""",
                parse_mode="Markdown",
            )

            return

        # ====================================================
        # JD MODE
        # ====================================================

        if user_id in user_jobs:

            job = user_jobs[user_id]

            result = calculate_jd_score(
                text,
                job
            )

            if user_id not in user_resumes:
                user_resumes[user_id] = []

            user_resumes[user_id].append(
                {
                    "filename": filename,
                    "score": result["total"],
                    "result": result,
                    "text": text.lower(),
                }
            )

            user_resumes[user_id] = (
                user_resumes[user_id][-10:]
            )

            user_states[user_id] = (
                "ANALYSIS_COMPLETE"
            )

            report = create_jd_report(
                filename,
                result
            )

            await send_report(
                update,
                report
            )

            if len(user_resumes[user_id]) >= 2:

                await update.message.reply_text(
                    "📊 Multiple candidates uploaded.\n\n"
                    "Use /rank to rank candidates."
                )

            return

        # ========================================================
        # ORIGINAL RESUME MODE
        # ========================================================

        result = calculate_original_score(
            text
        )

        if user_id not in user_resumes:
            user_resumes[user_id] = []

        user_resumes[user_id].append(
            {
                "filename": filename,
                "score": result["total"],
                "result": result,
                "text": text.lower(),
            }
        )

        user_resumes[user_id] = (
            user_resumes[user_id][-10:]
        )

        report = create_report(
            filename,
            result
        )

        await send_report(
            update,
            report
        )

        if len(user_resumes[user_id]) >= 2:

            await update.message.reply_text(
                "📊 Multiple resumes uploaded.\n\n"
                "Use /compare to compare them."
            )

    except Exception as e:

        print("Document error:")
        traceback.print_exc()

        await update.message.reply_text(
            f"❌ Something went wrong while analyzing the document.\n\n"
            f"Error: {str(e)}"
        )


# ============================================================
# RANK
# ============================================================

async def rank_candidates(update, context):

    user_id = update.effective_user.id

    resumes = user_resumes.get(
        user_id,
        []
    )

    if user_id not in user_jobs:

        await update.message.reply_text(
            "📋 Please create a Job Description first using /newjob."
        )

        return

    if len(resumes) < 2:

        await update.message.reply_text(
            "📄 Please upload at least 2 resumes first."
        )

        return

    sorted_resumes = sorted(
        resumes,
        key=lambda x: (
            x["score"],
            x["result"]["mandatory_satisfied"],
            x["result"]["criteria"].get(
                "Relevant Experience",
                0
            ),
            x["result"]["criteria"].get(
                "Technical Skills Match",
                0
            ),
        ),
        reverse=True,
    )

    message = """
🏆 *CANDIDATE RANKING*
━━━━━━━━━━━━━━━━━━━━━━━━

"""

    for index, resume in enumerate(
        sorted_resumes,
        1
    ):

        mandatory = (
            "✅ Satisfied"
            if resume["result"]["mandatory_satisfied"]
            else "⚠️ Not Fully Satisfied"
        )

        experience_score = resume["result"]["criteria"].get(
            "Relevant Experience",
            0
        )
        technical_score = resume["result"]["criteria"].get(
            "Technical Skills Match",
            0
        )

        if experience_score >= 12:
            experience_match = "Strong"
        elif experience_score >= 7:
            experience_match = "Moderate"
        else:
            experience_match = "Limited"

        if technical_score >= 18:
            technical_match = "Strong"
        elif technical_score >= 10:
            technical_match = "Moderate"
        else:
            technical_match = "Limited"

        score = resume["score"]
        bar_length = 20
        filled = round((score / 100) * bar_length)
        filled = max(0, min(bar_length, filled))
        score_bar = "█" * filled + "░" * (bar_length - filled)

        safe_filename = (
            resume["filename"]
            .replace("_", "\\_")
        )

        rank_icon = (
            "🥇"
            if index == 1
            else "🥈"
            if index == 2
            else "🥉"
            if index == 3
            else "🔹"
        )

        message += (
            f"{rank_icon} *RANK #{index}*\n"
            f"📄 *{safe_filename}*\n\n"
            f"🎯 ATS Score: *{score}/100*\n"
            f"   `{score_bar}`\n\n"
            f"📋 Mandatory Requirements: {mandatory}\n"
            f"💼 Experience Match: *{experience_match}*\n"
            f"🛠 Technical Skills: *{technical_match}*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )

    message += """🔎 *RANKING METHODOLOGY*

Candidates are ranked using deterministic ATS scoring.

① Mandatory Requirements
② Relevant Experience
③ Technical Skill Match

━━━━━━━━━━━━━━━━━━━━━━━━
🤖 *Maruthi Chatbot*
JD-based ATS Recruitment Assistant
"""

    await send_report(
        update,
        message
    )

    user_states[user_id] = (
        "SHOWING_RANKING"
    )


# ============================================================
# COMPARE
# ============================================================

async def compare_resumes(update, context):

    user_id = update.effective_user.id

    resumes = user_resumes.get(
        user_id,
        []
    )

    if len(resumes) < 2:

        await update.message.reply_text(
            "📄 Please upload at least 2 resumes first."
        )

        return

    sorted_resumes = sorted(
        resumes,
        key=lambda x: x["score"],
        reverse=True,
    )

    message = """
📊 *Resume Comparison*

━━━━━━━━━━━━━━━━━━
"""

    for index, resume in enumerate(
        sorted_resumes,
        1
    ):

        safe_filename = (
            resume["filename"]
            .replace("_", "\\_")
        )

        message += (
            f"{index}. 📄 *{safe_filename}*\n"
            f"   🎯 ATS Score: *{resume['score']}%*\n\n"
        )

    message += """
━━━━━━━━━━━━━━━━━━
"""

    top = sorted_resumes[0]

    safe_top_filename = (
        top["filename"]
        .replace("_", "\\_")
    )

    message += (
        f"📌 Highest ATS score: "
        f"*{top['score']}%*\n"
        f"📄 Resume: *{safe_top_filename}*\n\n"
        "The comparison is based on Maruthi Chatbot ATS criteria."
    )

    await send_report(
        update,
        message
    )


# ============================================================
# DETAILS
# ============================================================

async def details(update, context):

    user_id = update.effective_user.id

    resumes = user_resumes.get(
        user_id,
        []
    )

    if not resumes:

        await update.message.reply_text(
            "📄 Please upload a resume first."
        )

        return

    latest = resumes[-1]

    if user_id in user_jobs:

        message = create_jd_report(
            latest["filename"],
            latest["result"]
        )

    else:

        message = create_report(
            latest["filename"],
            latest["result"]
        )

    await send_report(
        update,
        message
    )


# ============================================================
# RECOMMENDATIONS
# ============================================================

async def recommendations(update, context):

    user_id = update.effective_user.id

    resumes = user_resumes.get(
        user_id,
        []
    )

    if not resumes:

        await update.message.reply_text(
            "📄 Please upload a resume first."
        )

        return

    latest = resumes[-1]

    if user_id in user_jobs:

        courses = latest["result"]["courses"]

        message = """
🎓 *Exactly 3 Certification Recommendations*

"""

        for index, course in enumerate(
            courses[:3],
            1
        ):

            message += (
                f"{index}. *{course['name']}*\n"
                f"   Reason: {course['reason']}\n\n"
            )

    else:

        courses = latest["result"].get(
            "courses",
            []
        )

        message = """
🎓 *Suggested Courses / Certifications*

"""

        for index, course in enumerate(
            courses[:3],
            1
        ):

            message += (
                f"{index}. {course}\n"
            )

    await send_report(
        update,
        message
    )


# ============================================================
# GAPS
# ============================================================

async def gaps(update, context):

    user_id = update.effective_user.id

    resumes = user_resumes.get(
        user_id,
        []
    )

    if not resumes:

        await update.message.reply_text(
            "📄 Please upload a resume first."
        )

        return

    if user_id not in user_jobs:

        await update.message.reply_text(
            "📋 Upload a Job Description first to identify JD-specific gaps."
        )

        return

    latest = resumes[-1]

    candidate_gaps = latest["result"]["gaps"]

    message = """
⚠️ *Candidate Gaps*

━━━━━━━━━━━━━━━━━━
"""

    if candidate_gaps:

        for gap in candidate_gaps:

            message += (
                f"• {gap}\n"
            )

    else:

        message += (
            "No major gaps detected.\n"
        )

    await send_report(
        update,
        message
    )


# ============================================================
# DOWNLOADABLE ATS REPORT
# ============================================================

async def download_report(update, context):

    user_id = update.effective_user.id
    resumes = user_resumes.get(user_id, [])

    if user_id not in user_jobs:
        await update.message.reply_text(
            "📋 Please create a Job Description first using /newjob."
        )
        return

    if not resumes:
        await update.message.reply_text(
            "📄 Please upload at least one resume first."
        )
        return

    job = user_jobs[user_id]

    sorted_resumes = sorted(
        resumes,
        key=lambda x: (
            x["score"],
            x["result"]["mandatory_satisfied"],
            x["result"]["criteria"].get("Relevant Experience", 0),
            x["result"]["criteria"].get("Technical Skills Match", 0),
        ),
        reverse=True,
    )

    report_path = None

    try:
        safe_title = re.sub(r"[^A-Za-z0-9_-]+", "_", job["job_title"]).strip("_")
        if not safe_title:
            safe_title = "ATS_Report"

        report_filename = f"ATS_Report_{safe_title}.pdf"

        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".pdf") as report_file:
            report_path = report_file.name

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, alignment=TA_CENTER, spaceAfter=10)
        heading_style = ParagraphStyle("ReportHeading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, spaceBefore=8, spaceAfter=6)
        body_style = ParagraphStyle("ReportBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13, spaceAfter=3)
        small_style = ParagraphStyle("ReportSmall", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.5, leading=11, spaceAfter=2)

        story = [
            Paragraph("ATS RECRUITMENT REPORT", title_style),
            Paragraph("JD-based ATS Recruitment Assistant", ParagraphStyle("Subtitle", parent=body_style, alignment=TA_CENTER, fontSize=9, spaceAfter=12)),
        ]

        story.append(Paragraph("Job Information", heading_style))
        job_info = [
            ["Job Title", str(job["job_title"])],
            ["Candidates Analyzed", str(len(sorted_resumes))],
            ["Required Experience", f'{job["required_years"]} years'],
        ]
        table = Table(job_info, colWidths=[45*mm, 125*mm])
        table.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("BACKGROUND", (0,0), (0,-1), colors.lightgrey),
            ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ]))
        story.extend([table, Spacer(1, 8)])

        story.append(Paragraph("Job Requirements", heading_style))
        mandatory = ", ".join(job["mandatory_skills"]) if job["mandatory_skills"] else "Not specified"
        preferred = ", ".join(job["preferred_skills"]) if job["preferred_skills"] else "Not specified"
        req_table = Table([["Mandatory Skills", mandatory], ["Preferred Skills", preferred]], colWidths=[45*mm, 125*mm])
        req_table.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey), ("BACKGROUND", (0,0), (0,-1), colors.lightgrey),
            ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 9),
            ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(req_table)

        story.append(Paragraph("Candidate Ranking", heading_style))
        ranking_data = [["Rank", "Candidate", "ATS Score", "Mandatory", "Experience", "Technical"]]
        for index, resume in enumerate(sorted_resumes, 1):
            result = resume["result"]
            criteria = result["criteria"]
            ranking_data.append([
                str(index), str(resume["filename"]), f'{resume["score"]}/100',
                "Satisfied" if result["mandatory_satisfied"] else "Not Fully Satisfied",
                f'{criteria.get("Relevant Experience", 0)}/15',
                f'{criteria.get("Technical Skills Match", 0)}/25',
            ])
        rank_table = Table(ranking_data, colWidths=[12*mm, 57*mm, 22*mm, 32*mm, 23*mm, 24*mm], repeatRows=1)
        rank_table.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey), ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 7.5),
            ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 3), ("RIGHTPADDING", (0,0), (-1,-1), 3),
            ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(rank_table)

        for index, resume in enumerate(sorted_resumes, 1):
            result = resume["result"]
            criteria = result["criteria"]
            story.append(Paragraph(f"Rank #{index} - {str(resume['filename'])}", heading_style))
            story.append(Paragraph(
                f'ATS Score: <b>{resume["score"]}/100</b> | Mandatory Requirements: '
                f'<b>{"Satisfied" if result["mandatory_satisfied"] else "Not Fully Satisfied"}</b>', body_style))
            story.append(Paragraph("Score Breakdown", small_style))
            for criterion, score in criteria.items():
                story.append(Paragraph(f"• {criterion}: {score}", small_style))
            if result.get("gaps"):
                story.append(Paragraph("Gaps", small_style))
                for gap in result["gaps"]:
                    story.append(Paragraph(f"• {gap}", small_style))

        story.append(Paragraph("Ranking Methodology", heading_style))
        story.append(Paragraph("Candidates are ranked using deterministic ATS scoring.", body_style))
        story.append(Paragraph("Tie-breakers: 1. Mandatory Requirements  2. Relevant Experience  3. Technical Skill Match", body_style))
        story.append(Spacer(1, 10))
        story.append(Paragraph("Generated by Maruthi Chatbot", ParagraphStyle("Footer", parent=small_style, alignment=TA_CENTER, spaceBefore=10)))

        document = SimpleDocTemplate(
            report_path, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm,
            topMargin=15*mm, bottomMargin=15*mm,
            title="ATS Recruitment Report", author="Maruthi Chatbot"
        )
        document.build(story)

        with open(report_path, "rb") as report_file:
            await update.effective_message.reply_document(
                document=report_file,
                filename=report_filename,
                caption="📥 ATS Recruitment PDF Report generated successfully."
            )

    except Exception as e:
        print("Report generation error:")
        traceback.print_exc()
        await update.effective_message.reply_text(f"❌ Could not generate the ATS report.\n\nError: {str(e)}")

    finally:
        if report_path and os.path.exists(report_path):
            try:
                os.remove(report_path)
            except Exception:
                pass


# ============================================================
# RESET
# ============================================================

async def reset(update, context):

    user_id = update.effective_user.id

    user_resumes.pop(
        user_id,
        None
    )

    user_jobs.pop(
        user_id,
        None
    )

    user_states[user_id] = "RESET"

    await update.message.reply_text(
        """
🔄 *Recruitment Session Reset*

All uploaded Job Description and resumes have been cleared.

Use /newjob to start again.
""",
        parse_mode="Markdown",
    )


# ============================================================
# CLEAR
# ============================================================

async def clear_resumes(update, context):

    user_id = update.effective_user.id

    user_resumes.pop(
        user_id,
        None
    )

    await update.message.reply_text(
        "🗑️ Uploaded resumes cleared successfully."
    )


# ============================================================
# HELP
# ============================================================

async def help_command(update, context):

    await update.message.reply_text(
        """
🤖 *Maruthi Chatbot Help*

━━━━━━━━━━━━━━━━━━

📋 *Recruitment Flow*

1️⃣ /newjob

2️⃣ Upload Job Description

3️⃣ Upload multiple resumes

4️⃣ /rank

━━━━━━━━━━━━━━━━━━

📌 *Commands*

/start
/newjob
/upload_jd
/upload_resumes
/rank
/details
/compare
/recommendations
/gaps
/report
/reset
/clear
/help

━━━━━━━━━━━━━━━━━━

📄 Supported Documents:

• PDF
• DOCX
• TXT

━━━━━━━━━━━━━━━━━━

🎯 Features:

• ATS Score
• JD Matching
• Skill Normalization
• Mandatory Skills
• Preferred Skills
• Score Breakdown
• Candidate Ranking
• Strengths
• Missing Skills
• Certification Recommendations
• Multiple Resume Comparison
• Downloadable ATS PDF Report
""",
        parse_mode="Markdown",
    )


# ============================================================
# UPLOAD RESUMES
# ============================================================

async def upload_resumes(update, context):

    user_id = update.effective_user.id

    if user_id not in user_jobs:

        await update.message.reply_text(
            "📋 Please upload a Job Description first using /newjob."
        )

        return

    user_states[user_id] = (
        "WAITING_FOR_RESUMES"
    )

    await update.message.reply_text(
        """
📄 *Upload Candidate Resumes*

You can upload multiple:

• PDF
• DOCX
• TXT

After uploading candidates use:

/rank
""",
        parse_mode="Markdown",
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("Starting Maruthi Chatbot...")

    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )

    application.add_handler(
        CommandHandler(
            "newjob",
            new_job
        )
    )

    application.add_handler(
        CommandHandler(
            "upload_jd",
            upload_jd
        )
    )

    application.add_handler(
        CommandHandler(
            "upload_resumes",
            upload_resumes
        )
    )

    application.add_handler(
        CommandHandler(
            "rank",
            rank_candidates
        )
    )

    application.add_handler(
        CommandHandler(
            "details",
            details
        )
    )

    application.add_handler(
        CommandHandler(
            "compare",
            compare_resumes
        )
    )

    application.add_handler(
        CommandHandler(
            "recommendations",
            recommendations
        )
    )

    application.add_handler(
        CommandHandler(
            "gaps",
            gaps
        )
    )

    application.add_handler(
        CommandHandler(
            "report",
            download_report
        )
    )

    application.add_handler(
        CommandHandler(
            "reset",
            reset
        )
    )

    application.add_handler(
        CommandHandler(
            "clear",
            clear_resumes
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Document.ALL,
            handle_document
        )
    )

    print("Maruthi Chatbot is running...")

    application.run_polling()


if __name__ == "__main__":
    main()