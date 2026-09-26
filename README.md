# ATS Resume Chatbot

A Telegram-based ATS (Applicant Tracking System) chatbot that evaluates resumes against Job Descriptions, calculates ATS scores, checks mandatory requirements, ranks candidates, identifies gaps, and generates a downloadable ATS recruitment report.

## Features

- Job Description upload and content validation
- Resume upload in PDF, DOCX, and TXT formats
- JD-based ATS scoring out of 100
- Mandatory requirement checking
- Candidate ranking
- Multiple-resume comparison
- Candidate details and score breakdown
- Skill gap identification
- Improvement and recommendation suggestions
- Certification/course suggestions (up to 3)
- Downloadable ATS recruitment report
- Telegram chatbot interface

## Technologies Used

- Python 3
- python-telegram-bot
- pypdf
- python-docx
- ReportLab
- python-dotenv
- Regular Expressions (Regex)

## Project Structure

```text
ATS-Resume-Chatbot/
│
├── bot.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/1096sakemaruthi/ATS-Resume-Chatbot.git
cd ATS-Resume-Chatbot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
pip install reportlab
```

### 3. Create `.env`

Create a `.env` file in the project folder:

```env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
```

Keep the Telegram bot token private. The `.env` file is excluded from Git.

### 4. Run the chatbot

```bash
python bot.py
```

Expected output:

```text
Starting Maruthi Chatbot...
Maruthi Chatbot is running...
```

## Usage

### JD-Based Recruitment Workflow

1. Start the chatbot using `/start`.
2. Create a new recruitment job using `/newjob`.
3. Upload the Job Description.
4. Upload one or more resumes.
5. Use `/rank` to generate candidate ranking.
6. Use `/details` to view candidate details.
7. Use `/compare` to compare candidates.
8. Use `/recommendations` to view recommendations.
9. Use `/gaps` to view skill gaps.
10. Use `/report` to download the ATS recruitment report.

### Supported Resume Formats

- PDF
- DOCX
- TXT

## Main Commands

| Command | Purpose |
|---|---|
| `/start` | Start the chatbot |
| `/help` | Show available commands |
| `/newjob` | Start a new recruitment job |
| `/upload_jd` | Upload a Job Description |
| `/upload_resumes` | Upload resumes |
| `/rank` | Rank candidates |
| `/details` | View candidate details |
| `/compare` | Compare resumes |
| `/recommendations` | View recommendations |
| `/gaps` | View skill gaps |
| `/report` | Download ATS recruitment report |
| `/clear` | Clear current data |
| `/reset` | Reset the workflow |

## ATS Scoring Criteria

The JD-based ATS evaluation uses deterministic weighted scoring:

| Criterion | Weight |
|---|---:|
| Technical Skills Match | 25 |
| Responsibilities Match | 20 |
| Relevant Experience | 15 |
| Years Experience | 10 |
| Domain Experience | 10 |
| Education | 5 |
| Certifications | 5 |
| Tools/Technology Match | 5 |
| Seniority/Role Alignment | 5 |
| **Total** | **100** |

Candidate ranking also considers mandatory requirements, relevant experience, and technical skill match as tie-breakers.

## ATS Report

After uploading a Job Description and resumes, the `/report` command generates a downloadable ATS recruitment report containing:

- Job title
- Candidate ranking
- ATS scores
- Mandatory requirement status
- Score breakdown
- Candidate gaps
- Ranking methodology

## Security

- Keep the Telegram bot token inside `.env`.
- Never commit or publicly share `.env`.
- Avoid uploading private or sensitive candidate information to a public repository.

## Project Purpose

The project provides a Telegram-based recruitment assistant that helps automate resume screening against Job Descriptions, calculate ATS scores, compare candidates, identify gaps, and generate structured recruitment reports.

## Author

**S. Maruthi**

GitHub: https://github.com/1096sakemaruthi

---

**ATS Resume Chatbot — JD-based ATS Recruitment Assistant**
