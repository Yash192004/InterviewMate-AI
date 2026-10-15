"""
AI Engine for InterviewMate — Enhanced v3
Integrates with IBM watsonx.ai (primary) or OpenAI (fallback).

Features:
  - Smart resume analysis with career field scoring (0–100)
  - ATS compatibility scoring per job role
  - Resume strengths/weaknesses analysis
  - Career interest questionnaire processing
  - Deep multi-dimensional answer evaluation
  - Context-aware follow-up question generation
  - Conversation memory across the full interview session
  - Personalized improvement plan generation

Environment variables:
    WATSONX_API_KEY      - IBM watsonx.ai API key
    WATSONX_PROJECT_ID   - IBM watsonx.ai project ID
    WATSONX_URL          - IBM watsonx.ai endpoint
    OPENAI_API_KEY       - OpenAI API key (fallback)
"""

import os
import json
import re

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from docx import Document as DocxDocument
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False


INTERVIEWER_PERSONA = (
    "You are Alex, a senior technical recruiter and engineering manager with 15 years of "
    "experience at top tech companies. You conduct realistic, professional interviews. "
    "You are direct, fair, and thorough. You probe vague answers with follow-ups. "
    "You reward concrete examples, clear thinking, and honest self-awareness."
)

SCORING_RUBRIC = """
Scoring rubric (0–10):
  9-10: Exceptional — complete, precise, with strong examples and depth
  7-8:  Good — mostly correct with minor gaps, clear communication
  5-6:  Average — partially correct but missing key details or examples
  3-4:  Below average — significant gaps, vague, or partially incorrect
  1-2:  Poor — largely incorrect, off-topic, or very incomplete
  0:    No answer or completely wrong
Apply this strictly. Do not inflate scores.
"""

CAREER_FIELDS = [
    "Software Developer",
    "Data Analyst",
    "Data Scientist",
    "AI/ML Engineer",
    "Cybersecurity Analyst",
    "Cloud Engineer",
    "DevOps Engineer",
    "Frontend Developer",
    "Backend Developer",
    "Full Stack Developer",
    "Mobile App Developer",
    "Product Manager",
    "Business Analyst",
    "Database Administrator",
    "Network Engineer",
]


class AIEngine:
    """Unified AI engine with deep interview and resume intelligence."""

    def __init__(self):
        self.watsonx_key = os.environ.get("WATSONX_API_KEY")
        self.watsonx_project = os.environ.get("WATSONX_PROJECT_ID")
        self.watsonx_url = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self._wx_client = None
        self._oai_client = None
        self._setup_clients()

    # ── Provider Setup ─────────────────────────────────────────

    def _setup_clients(self):
        if self.watsonx_key and self.watsonx_project:
            try:
                from ibm_watsonx_ai import Credentials
                from ibm_watsonx_ai.foundation_models import ModelInference
                from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as Params
                self._wx_client = ModelInference(
                    model_id="ibm/granite-3-8b-instruct",
                    credentials=Credentials(api_key=self.watsonx_key, url=self.watsonx_url),
                    project_id=self.watsonx_project,
                    params={
                        Params.MAX_NEW_TOKENS: 2000,
                        Params.TEMPERATURE: 0.65,
                        Params.STOP_SEQUENCES: ["<|endoftext|>"],
                    },
                )
                print("[AIEngine] Using IBM watsonx.ai (Granite 3 8B Instruct)")
                return
            except Exception as e:
                print(f"[AIEngine] watsonx.ai setup failed: {e}")

        if self.openai_key:
            try:
                from openai import OpenAI
                self._oai_client = OpenAI(api_key=self.openai_key)
                print("[AIEngine] Using OpenAI GPT-4o-mini")
                return
            except Exception as e:
                print(f"[AIEngine] OpenAI setup failed: {e}")

        print("[AIEngine] WARNING: No AI API keys found. Using intelligent fallback responses.")

    # ── Core LLM ───────────────────────────────────────────────

    def _llm(self, prompt: str, max_tokens: int = 1500, temperature: float = 0.65) -> str:
        if self._wx_client:
            try:
                result = self._wx_client.generate_text(prompt=prompt)
                return result if isinstance(result, str) else result.get("generated_text", "")
            except Exception as e:
                print(f"[AIEngine] watsonx error: {e}")

        if self._oai_client:
            try:
                resp = self._oai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": INTERVIEWER_PERSONA},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                print(f"[AIEngine] OpenAI error: {e}")

        return ""

    # ── Text Extraction ────────────────────────────────────────

    def extract_text(self, filepath: str) -> str:
        ext = filepath.rsplit(".", 1)[-1].lower()
        try:
            if ext == "pdf" and PDF_SUPPORT:
                with pdfplumber.open(filepath) as pdf:
                    return "\n".join(p.extract_text() or "" for p in pdf.pages)
            elif ext == "docx" and DOCX_SUPPORT:
                doc = DocxDocument(filepath)
                return "\n".join(p.text for p in doc.paragraphs)
            elif ext == "txt":
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            elif ext == "doc":
                with open(filepath, "rb") as f:
                    return f.read().decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"[AIEngine] Text extraction error: {e}")
        return ""

    # ── Smart Resume Analysis ──────────────────────────────────

    def analyze_resume(self, resume_text: str) -> dict:
        """Full resume analysis: skills, profile, career field scores, strengths/weaknesses."""
        fields_str = ", ".join(CAREER_FIELDS)
        prompt = f"""{INTERVIEWER_PERSONA}

Carefully analyze this resume and return a single JSON object with EXACTLY these keys:
{{
  "name": "candidate full name extracted from resume, or 'Candidate' if not found",
  "skills": ["up to 15 technical and soft skills found in resume"],
  "experience_years": <integer years of experience, 0 for freshers>,
  "education": "highest degree and field, e.g. B.Tech Computer Science",
  "projects": ["up to 5 project names or one-line descriptions from the resume"],
  "strengths": ["4-5 genuine, specific strengths evident from this resume"],
  "weaknesses": ["3-4 honest gaps or weak areas in this resume"],
  "suggested_roles": ["top 3 roles this person is best suited for, from this list: {fields_str}"],
  "summary": "2-sentence professional summary based on actual resume content",
  "improvement_areas": ["3 specific skills to add or improve based on resume gaps"],
  "experience_level": "fresher|junior|mid|senior",
  "tech_stack": ["primary technologies, frameworks, and tools found in resume"],
  "career_field_scores": {{
    "Software Developer": <score 0-100 based on evidence in resume>,
    "Data Analyst": <score 0-100>,
    "Data Scientist": <score 0-100>,
    "AI/ML Engineer": <score 0-100>,
    "Cybersecurity Analyst": <score 0-100>,
    "Cloud Engineer": <score 0-100>,
    "DevOps Engineer": <score 0-100>,
    "Frontend Developer": <score 0-100>,
    "Backend Developer": <score 0-100>,
    "Full Stack Developer": <score 0-100>,
    "Mobile App Developer": <score 0-100>
  }},
  "what_to_keep": ["3 specific things in this resume to definitely keep"],
  "what_to_change": ["3 specific things to change or improve in this resume"]
}}

Scoring criteria for career_field_scores:
- Base score on actual evidence: skills, projects, education, experience found in the resume
- 80-100: Strong match — multiple relevant skills, projects, experience
- 60-79: Good match — some relevant skills, could grow into role
- 40-59: Moderate — basic skills present but significant gaps
- 20-39: Weak — very few relevant skills
- 0-19: No match — almost no relevant evidence

Rules:
- Return ONLY the JSON object, no markdown, no extra text.
- Be accurate and specific, not generic. Base everything on actual resume content.
- Name MUST be extracted from the resume text itself.

Resume:
{resume_text[:5000]}
"""
        raw = self._llm(prompt, max_tokens=1400, temperature=0.4)
        result = self._parse_json(raw, self._resume_fallback())
        # Ensure career_field_scores always present
        if "career_field_scores" not in result:
            result["career_field_scores"] = self._default_career_scores()
        return result

    def _default_career_scores(self) -> dict:
        return {f: 0 for f in CAREER_FIELDS[:11]}

    def _resume_fallback(self) -> dict:
        return {
            "name": "Candidate",
            "skills": ["Communication", "Problem Solving", "Teamwork"],
            "experience_years": 0,
            "education": "Bachelor's Degree",
            "projects": [],
            "strengths": ["Adaptability", "Willingness to learn"],
            "weaknesses": ["Limited work experience", "Technical depth needs improvement"],
            "suggested_roles": ["Software Developer", "Data Analyst", "Business Analyst"],
            "summary": "A motivated candidate ready to contribute to a dynamic team.",
            "improvement_areas": ["Technical depth", "Domain expertise", "Leadership"],
            "experience_level": "fresher",
            "tech_stack": [],
            "career_field_scores": self._default_career_scores(),
            "what_to_keep": ["Education section", "Project descriptions", "Skills list"],
            "what_to_change": ["Add quantified achievements", "Improve summary", "Add certifications"],
        }

    # ── ATS Score Analysis ─────────────────────────────────────

    def analyze_ats(self, resume_text: str, job_role: str) -> dict:
        """Compute ATS compatibility score for a specific job role."""
        prompt = f"""{INTERVIEWER_PERSONA}

Analyze this resume for ATS (Applicant Tracking System) compatibility for the role: {job_role}

Return ONLY this JSON:
{{
  "ats_score": <integer 0-100>,
  "grade": "A|B|C|D|F",
  "relevant_keywords": ["keywords from resume that match {job_role} requirements"],
  "missing_keywords": ["important keywords for {job_role} missing from resume"],
  "formatting_issues": ["specific formatting problems that hurt ATS parsing"],
  "improvement_suggestions": ["4-5 specific, actionable suggestions to improve ATS score for {job_role}"],
  "keyword_density": "<low|medium|high>",
  "summary": "2-sentence assessment of ATS readiness for {job_role}"
}}

Scoring criteria:
- 85-100: Excellent ATS fit — strong keyword match, clean formatting
- 70-84: Good — most keywords present, minor gaps
- 55-69: Average — some keywords missing, needs improvement
- 40-54: Below average — significant keyword and formatting gaps
- 0-39: Poor — major misalignment with {job_role} requirements

Resume:
{resume_text[:4000]}
"""
        raw = self._llm(prompt, max_tokens=700, temperature=0.3)
        result = self._parse_json(raw, None)
        if not result:
            result = {
                "ats_score": 50,
                "grade": "C",
                "relevant_keywords": [],
                "missing_keywords": ["Role-specific technical skills", "Industry keywords"],
                "formatting_issues": ["Unable to analyze — AI unavailable"],
                "improvement_suggestions": ["Add more role-specific keywords", "Use standard section headings"],
                "keyword_density": "low",
                "summary": f"ATS analysis for {job_role} could not be completed. Please configure AI API keys.",
            }
        return result

    # ── Career Interest Questions ──────────────────────────────

    def get_career_interest_questions(self) -> list:
        """Return the list of career personalization questions."""
        return [
            {
                "id": "preferred_field",
                "question": "Which career field interests you the most?",
                "type": "choice",
                "options": CAREER_FIELDS,
            },
            {
                "id": "experience_level",
                "question": "What is your current experience level?",
                "type": "choice",
                "options": ["Fresher (0 years)", "Junior (1-2 years)", "Mid-level (3-5 years)", "Senior (5+ years)"],
            },
            {
                "id": "career_goal",
                "question": "What is your primary career goal for the next 2 years?",
                "type": "text",
                "placeholder": "e.g. Get my first job as a data analyst at a tech company",
            },
            {
                "id": "target_companies",
                "question": "What type of companies are you targeting?",
                "type": "choice",
                "options": ["Startup", "Mid-size company", "Large enterprise", "MNC / FAANG-level", "Remote/freelance"],
            },
            {
                "id": "weakest_area",
                "question": "What do you feel is your biggest weakness for interviews?",
                "type": "choice",
                "options": [
                    "Technical knowledge",
                    "Communication / explaining clearly",
                    "Confidence under pressure",
                    "Behavioral / HR questions",
                    "Problem-solving speed",
                ],
            },
        ]

    def process_career_interests(self, resume_analysis: dict, interests: dict) -> dict:
        """Generate personalized career recommendations based on resume + interests."""
        career_scores = resume_analysis.get("career_field_scores", {})
        preferred = interests.get("preferred_field", "")
        goal = interests.get("career_goal", "")
        exp = interests.get("experience_level", "Fresher")
        weakness = interests.get("weakest_area", "")

        top_roles = sorted(career_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        top_str = "\n".join(f"  - {r}: {s}/100" for r, s in top_roles)

        prompt = f"""{INTERVIEWER_PERSONA}

Based on this candidate's resume analysis and career interests, provide personalized recommendations.

Resume top career scores:
{top_str}

Candidate's interests:
- Preferred field: {preferred}
- Experience level: {exp}
- Career goal: {goal}
- Self-identified weakness: {weakness}

Return ONLY this JSON:
{{
  "recommended_role": "<single best role recommendation>",
  "recommendation_reason": "<2-3 sentence explanation of why this is the best fit>",
  "alignment_score": <0-100 how well preferred field matches resume>,
  "gap_analysis": "<2 sentences on key gaps between current profile and preferred role>",
  "action_plan": ["5 specific steps to bridge the gap and reach goal"],
  "alternative_roles": ["2 alternative roles worth considering with brief reasons"],
  "interview_focus": ["3 areas to focus on most during interview preparation"],
  "timeline": "<realistic timeline to be interview-ready for recommended role>"
}}
"""
        raw = self._llm(prompt, max_tokens=800, temperature=0.5)
        result = self._parse_json(raw, None)
        if not result:
            result = {
                "recommended_role": preferred or (top_roles[0][0] if top_roles else "Software Developer"),
                "recommendation_reason": "Based on your resume profile and stated interests, this role aligns well with your current skills.",
                "alignment_score": career_scores.get(preferred, 50) if preferred else 50,
                "gap_analysis": "Some skill gaps exist but are bridgeable with focused preparation.",
                "action_plan": ["Build portfolio projects", "Practice interview questions", "Get relevant certifications", "Network in the field", "Apply to internships/entry roles"],
                "alternative_roles": ["Business Analyst — good communication fit", "Data Analyst — analytical skills apply"],
                "interview_focus": ["Technical fundamentals", "Project storytelling", "Behavioral questions"],
                "timeline": "4-8 weeks of focused preparation",
            }
        return result

    # ── Question Generation ────────────────────────────────────

    def generate_question(
        self,
        resume_text: str,
        job_role: str,
        interview_type: str,
        difficulty: str,
        question_number: int,
        weak_topics: list,
        asked_questions: list,
        conversation_history: list = None,
        last_answer: str = "",
        last_score: float = None,
    ) -> dict:
        asked_str = "\n".join(f"  - {q}" for q in asked_questions[-6:]) if asked_questions else "  none"
        weak_str = ", ".join(weak_topics) if weak_topics else "none identified yet"

        conv_ctx = ""
        if conversation_history:
            recent = conversation_history[-3:]
            conv_ctx = "\nRecent exchange:\n" + "\n".join(
                f"  Q: {c['question']}\n  A: {c['answer'][:120]}..." for c in recent
            )

        probe_hint = ""
        if last_score is not None and last_score < 5.5 and last_answer and question_number > 1:
            probe_hint = (
                f"\nThe candidate's last answer scored {last_score:.1f}/10 and was incomplete. "
                "Consider asking a probing follow-up to give them a chance to demonstrate understanding, "
                "OR move to a new topic if the previous one is exhausted."
            )

        type_instructions = {
            "hr": (
                "behavioral or HR question — focus on personality, motivation, teamwork, "
                "communication, leadership, career goals, or culture fit"
            ),
            "technical": (
                "technical question — focus on algorithms, data structures, system design, "
                "coding concepts, architecture, debugging, or role-specific technical skills"
            ),
            "mixed": (
                "alternate naturally between behavioral/HR and technical questions for a realistic interview flow"
            ),
        }.get(interview_type, "mixed question")

        difficulty_guidance = {
            "easy": "Starter-level question. Simple concept or basic experience question.",
            "medium": "Intermediate question requiring some depth and a real example.",
            "hard": "Advanced question requiring deep expertise, trade-off analysis, or system-level thinking.",
        }.get(difficulty, "intermediate question")

        prompt = f"""{INTERVIEWER_PERSONA}

You are conducting question #{question_number} of a {difficulty} {interview_type} interview for the role: {job_role}.

Candidate's weak areas: {weak_str}
Questions already asked (do NOT repeat):
{asked_str}{conv_ctx}{probe_hint}

Difficulty guidance: {difficulty_guidance}
Question type: {type_instructions}

Generate ONE fresh, specific, realistic interview question grounded in the candidate's background.
The question should feel natural, not robotic.

Return ONLY this JSON:
{{"question": "<the question text>", "type": "<hr|technical|behavioral|scenario>", "topic": "<concise topic name>", "hint": "<optional 1-sentence thinking hint for the candidate, or empty string>"}}

Resume context:
{resume_text[:2000]}
"""
        raw = self._llm(prompt, max_tokens=350)
        result = self._parse_json(raw, None)
        if not result or not result.get("question"):
            result = self._fallback_question(job_role, interview_type, question_number, difficulty)
        result.setdefault("hint", "")
        return result

    def _fallback_question(self, job_role: str, interview_type: str, num: int, difficulty: str = "medium") -> dict:
        easy_hr = [
            ("Tell me about yourself and what brought you to this field.", "hr", "Introduction", "Keep it to 2 minutes: background, skills, why this role."),
            ("What are your top 3 strengths?", "hr", "Strengths", "Use specific examples for each strength."),
            ("Why do you want this role?", "hr", "Motivation", "Connect your skills to the role requirements."),
            ("Describe your ideal work environment.", "hr", "Culture Fit", "Think about collaboration style and work preferences."),
        ]
        medium_hr = [
            ("Describe a challenging project and how you handled it. What was the outcome?", "behavioral", "Problem Solving", "Use the STAR method: Situation, Task, Action, Result."),
            ("Tell me about a time you had a conflict with a teammate. How did you resolve it?", "behavioral", "Teamwork", "Focus on the resolution and what you learned."),
            ("Where do you see yourself in 3 years?", "hr", "Career Goals", "Show ambition balanced with realistic planning."),
            ("Describe a failure. What did you learn from it?", "behavioral", "Self-Awareness", "Be honest — interviewers value self-awareness."),
        ]
        tech_easy = [
            ("What is the difference between a stack and a queue? Give a real-world use case.", "technical", "Data Structures", "Think of everyday examples like browser history or print queues."),
            ("Explain Object-Oriented Programming and its four main principles.", "technical", "OOP", "Cover encapsulation, inheritance, polymorphism, abstraction."),
            ("What is the difference between GET and POST HTTP methods?", "technical", "Web Fundamentals", "Think about data visibility and use cases."),
            ("What is a database index and why is it useful?", "technical", "Databases", "Think about how a book's index speeds up lookup."),
        ]
        tech_hard = [
            ("Design a URL shortener like bit.ly. Walk me through your architecture.", "technical", "System Design", "Consider scalability, database choice, hash collisions."),
            ("Explain the CAP theorem and how it affects distributed system design choices.", "technical", "Distributed Systems", "Think about consistency vs. availability trade-offs."),
            ("How would you optimize a slow SQL query in a production database?", "technical", "Database Optimization", "Cover EXPLAIN, indexes, query rewriting, caching."),
            ("Explain how garbage collection works in your primary language.", "technical", "Memory Management", "Describe the algorithm and its impact on performance."),
        ]
        if interview_type == "hr":
            pool = easy_hr if difficulty == "easy" else medium_hr
        elif interview_type == "technical":
            pool = tech_easy if difficulty in ("easy", "medium") else tech_hard
        else:
            pool = (easy_hr + tech_easy) if difficulty == "easy" else (medium_hr + tech_hard)

        q, t, topic, hint = pool[(num - 1) % len(pool)]
        return {"question": q, "type": t, "topic": topic, "hint": hint}

    # ── Deep Answer Evaluation ─────────────────────────────────

    def evaluate_answer(
        self,
        question: str,
        answer: str,
        job_role: str,
        topic: str,
        question_type: str = "general",
        difficulty: str = "medium",
        conversation_history: list = None,
    ) -> dict:
        conv_ctx = ""
        if conversation_history:
            recent = conversation_history[-2:]
            conv_ctx = "\nPrevious Q&A context:\n" + "\n".join(
                f"  Q: {c['question']}\n  A: {c['answer'][:100]}..." for c in recent
            )

        answer_len = len(answer.split())
        length_note = ""
        if answer_len < 20:
            length_note = "\nNote: The answer is very short (under 20 words). Penalise for lack of depth."
        elif answer_len > 400:
            length_note = "\nNote: The answer is very long. Check if it is focused and on-point."

        prompt = f"""{INTERVIEWER_PERSONA}

{SCORING_RUBRIC}

You are evaluating a candidate's answer for a {difficulty} {question_type} interview question for the role: {job_role}.
Topic: {topic}{conv_ctx}{length_note}

QUESTION: {question}

CANDIDATE'S ANSWER: {answer}

Perform a thorough, honest evaluation. Return ONLY this JSON object (no markdown, no extra text):
{{
  "score": <weighted overall score 0-10, one decimal>,
  "dimension_scores": {{
    "technical_accuracy": <0-10, factual/conceptual correctness>,
    "depth": <0-10, insight and completeness>,
    "clarity": <0-10, communication quality and structure>,
    "relevance": <0-10, how well it addresses the question>,
    "examples": <0-10, quality of examples or evidence given>
  }},
  "correctness": "<1-2 sentences: what was factually right or wrong>",
  "depth_assessment": "<1-2 sentences: how deep or shallow the answer was>",
  "clarity": "<1 sentence: how clearly ideas were communicated>",
  "completeness": "<1-2 sentences: what key aspects were covered or missing>",
  "what_went_well": "<2-3 specific things the candidate did well>",
  "feedback": "<3-4 sentences of direct, actionable coaching feedback>",
  "improved_answer": "<A model answer in 4-6 sentences demonstrating expert-level response>",
  "key_missing_points": ["<specific important concept/point missed>"],
  "follow_up_hint": "<1 question an interviewer would naturally ask next, or empty string>",
  "encouragement": "<1 short encouraging sentence personalised to their answer>"
}}
"""
        raw = self._llm(prompt, max_tokens=1000)
        result = self._parse_json(raw, None)
        if not result or "score" not in result:
            result = self._evaluation_fallback(answer, question_type)
        result["score"] = round(max(0.0, min(10.0, float(result.get("score", 5)))), 1)
        dim = result.get("dimension_scores", {})
        for k in ("technical_accuracy", "depth", "clarity", "relevance", "examples"):
            if k in dim:
                dim[k] = round(max(0.0, min(10.0, float(dim[k]))), 1)
        result.setdefault("what_went_well", "")
        result.setdefault("follow_up_hint", "")
        result.setdefault("encouragement", "Keep going — every answer is a learning opportunity.")
        result.setdefault("depth_assessment", result.get("completeness", ""))
        result.setdefault("key_missing_points", [])
        return result

    def _evaluation_fallback(self, answer: str, question_type: str = "general") -> dict:
        wc = len(answer.split())
        score = min(6.5, max(1.5, wc / 20.0))
        return {
            "score": round(score, 1),
            "dimension_scores": {
                "technical_accuracy": round(score, 1),
                "depth": round(min(score, 5.0), 1),
                "clarity": round(min(score + 0.5, 6.5), 1),
                "relevance": round(score, 1),
                "examples": round(max(score - 1.5, 1.0), 1),
            },
            "correctness": "The answer touches on the topic but accuracy could not be fully verified.",
            "depth_assessment": "The answer lacks sufficient depth and specific detail.",
            "clarity": "Communication is understandable but could be more structured.",
            "completeness": "Several key aspects of the question were not addressed.",
            "what_went_well": "You attempted the question and provided some relevant information.",
            "feedback": (
                "Try to structure your answers using the STAR method for behavioral questions "
                "or define-explain-example for technical ones. Include real examples from your "
                "experience to make your answer concrete and memorable."
            ),
            "improved_answer": (
                "A strong answer would open with a clear, direct response to the question, "
                "follow with a specific real-world example demonstrating your experience, "
                "explain the impact or outcome, and close by connecting it to the role requirements."
            ),
            "key_missing_points": ["Specific example", "Technical depth", "Outcome/impact"],
            "follow_up_hint": "",
            "encouragement": "Every practice session makes you sharper — keep going!",
        }

    # ── Improvement Plan ───────────────────────────────────────

    def generate_improvement_plan(
        self,
        job_role: str,
        weak_topics: list,
        overall_score: float,
        breakdown: dict,
        experience_level: str = "fresher",
    ) -> dict:
        weak_str = ", ".join(weak_topics) if weak_topics else "No critical weak spots identified"
        breakdown_str = "\n".join(f"  - {t}: {s}/10" for t, s in breakdown.items())
        level_context = {
            "fresher": "This is a fresher/new graduate. Focus on foundational skills and building confidence.",
            "junior": "Junior-level candidate with 0-2 years experience. Balance fundamentals with practical projects.",
            "mid": "Mid-level candidate. Focus on depth, system design, and leadership skills.",
            "senior": "Senior candidate. Focus on architecture, leadership, and strategic thinking.",
        }.get(experience_level, "")

        prompt = f"""{INTERVIEWER_PERSONA}

{level_context}

Create a highly specific, actionable 2-week daily study plan for a candidate preparing for: {job_role}

Their interview performance:
- Overall score: {overall_score}/10
- Topic breakdown:
{breakdown_str}
- Key weak areas: {weak_str}

Return ONLY this JSON (no extra text):
{{
  "summary": "<2-sentence motivational and specific summary>",
  "focus_areas": ["<top 3 focus areas to prioritise>"],
  "weekly_plan": [
    {{
      "week": 1,
      "focus": "<week theme>",
      "days": [
        {{"day": "Monday", "task": "<specific task>", "resource": "<named resource>", "duration": "<time>", "goal": "<what to achieve>"}},
        {{"day": "Tuesday", "task": "<specific task>", "resource": "<named resource>", "duration": "<time>", "goal": "<what to achieve>"}},
        {{"day": "Wednesday", "task": "<specific task>", "resource": "<named resource>", "duration": "<time>", "goal": "<what to achieve>"}},
        {{"day": "Thursday", "task": "<specific task>", "resource": "<named resource>", "duration": "<time>", "goal": "<what to achieve>"}},
        {{"day": "Friday", "task": "<specific task>", "resource": "<named resource>", "duration": "<time>", "goal": "<what to achieve>"}}
      ]
    }},
    {{
      "week": 2,
      "focus": "<week theme>",
      "days": [
        {{"day": "Monday", "task": "<specific task>", "resource": "<named resource>", "duration": "<time>", "goal": "<what to achieve>"}},
        {{"day": "Tuesday", "task": "<specific task>", "resource": "<named resource>", "duration": "<time>", "goal": "<what to achieve>"}},
        {{"day": "Wednesday", "task": "<specific task>", "resource": "<named resource>", "duration": "<time>", "goal": "<what to achieve>"}},
        {{"day": "Thursday", "task": "<specific task>", "resource": "<named resource>", "duration": "<time>", "goal": "<what to achieve>"}},
        {{"day": "Friday", "task": "<specific task>", "resource": "<named resource>", "duration": "<time>", "goal": "<what to achieve>"}}
      ]
    }}
  ],
  "resources": [
    {{"title": "<name>", "type": "book|course|practice|video|website", "url_hint": "<where to find>", "reason": "<why it helps>", "priority": "high|medium"}}
  ],
  "quick_tips": ["<5 highly specific interview tips tailored to their weak areas>"],
  "daily_habit": "<one simple daily habit to build over 2 weeks>"
}}
"""
        raw = self._llm(prompt, max_tokens=1400)
        result = self._parse_json(raw, None)
        if not result:
            result = self._plan_fallback(weak_topics, job_role)
        return result

    def _plan_fallback(self, weak_topics: list, job_role: str) -> dict:
        return {
            "summary": (
                f"To land your {job_role} role, focus on daily coding practice and "
                "structured mock interviews. Consistent effort over 2 weeks will dramatically improve your confidence."
            ),
            "focus_areas": weak_topics[:3] if weak_topics else ["Data Structures", "System Design", "Behavioral"],
            "weekly_plan": [
                {
                    "week": 1,
                    "focus": "Core Foundations",
                    "days": [
                        {"day": "Monday", "task": "Arrays & Strings — solve 3 LeetCode Easy", "resource": "LeetCode", "duration": "1.5 hrs", "goal": "Comfortable with two-pointer pattern"},
                        {"day": "Tuesday", "task": "Linked Lists & Stacks — solve 2 problems + review", "resource": "NeetCode.io", "duration": "1 hr", "goal": "Understand insert/delete operations"},
                        {"day": "Wednesday", "task": "HR prep — write 3 STAR stories for teamwork, failure, achievement", "resource": "Big Interview", "duration": "1 hr", "goal": "3 polished behavioral stories"},
                        {"day": "Thursday", "task": "Trees & BFS/DFS — solve 2 problems", "resource": "GeeksForGeeks", "duration": "1.5 hrs", "goal": "Understand traversal patterns"},
                        {"day": "Friday", "task": "Full mock interview (HR + 2 technical)", "resource": "InterviewMate AI", "duration": "45 min", "goal": "Score above 6/10"},
                    ],
                },
                {
                    "week": 2,
                    "focus": "Advanced Topics + Simulation",
                    "days": [
                        {"day": "Monday", "task": "System Design basics — design a URL shortener", "resource": "Grokking System Design", "duration": "1.5 hrs", "goal": "Explain scalable architecture"},
                        {"day": "Tuesday", "task": "Dynamic Programming — 2 medium problems", "resource": "LeetCode", "duration": "1.5 hrs", "goal": "Identify DP subproblems"},
                        {"day": "Wednesday", "task": "SQL & Databases — practice 5 queries + explain indexes", "resource": "SQLZoo", "duration": "1 hr", "goal": "Write optimised JOINs"},
                        {"day": "Thursday", "task": "Company research + role-specific prep", "resource": "Glassdoor + LinkedIn", "duration": "1 hr", "goal": "Tailor answers to company values"},
                        {"day": "Friday", "task": "Full-length mock interview — aim for 7+/10", "resource": "InterviewMate AI", "duration": "1 hr", "goal": "Reach target score"},
                    ],
                },
            ],
            "resources": [
                {"title": "Cracking the Coding Interview", "type": "book", "url_hint": "Amazon / PDF", "reason": "Comprehensive coding interview prep", "priority": "high"},
                {"title": "NeetCode 150", "type": "practice", "url_hint": "neetcode.io", "reason": "Curated 150 essential LeetCode patterns", "priority": "high"},
                {"title": "Grokking the System Design Interview", "type": "course", "url_hint": "educative.io", "reason": "Structured system design learning", "priority": "medium"},
                {"title": "Big Interview", "type": "website", "url_hint": "biginterview.com", "reason": "HR and behavioral answer practice", "priority": "medium"},
            ],
            "quick_tips": [
                "Always clarify the question before diving into your answer",
                "Use the STAR method for every behavioral question",
                "For coding, talk through your approach before writing code",
                "Prepare 2-3 questions to ask the interviewer",
                "Practice saying your answers aloud",
            ],
            "daily_habit": "Spend 20 minutes each morning reading one technical concept and explaining it in your own words.",
        }

    # ── JSON Parser ────────────────────────────────────────────

    def _parse_json(self, text: str, fallback) -> dict:
        if not text:
            return fallback
        m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
        if m:
            text = m.group(1)
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e != -1:
            try:
                return json.loads(text[s:e + 1])
            except json.JSONDecodeError:
                pass
        return fallback
