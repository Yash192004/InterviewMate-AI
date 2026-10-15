from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class UserProfile(db.Model):
    __tablename__ = "user_profiles"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), unique=True, nullable=False)
    candidate_name = db.Column(db.String(256))          # extracted from resume
    resume_text = db.Column(db.Text)
    resume_filename = db.Column(db.String(256))
    resume_uploaded_at = db.Column(db.DateTime)         # upload timestamp
    skills = db.Column(db.Text)                         # JSON list of skills
    tech_stack = db.Column(db.Text)                     # JSON list
    education = db.Column(db.String(512))
    experience_years = db.Column(db.Integer, default=0)
    experience_level = db.Column(db.String(32))         # fresher|junior|mid|senior
    career_scores = db.Column(db.Text)                  # JSON {role: score_out_of_100}
    ats_scores = db.Column(db.Text)                     # JSON {role: {score, keywords, missing, suggestions}}
    resume_strengths = db.Column(db.Text)               # JSON list
    resume_weaknesses = db.Column(db.Text)              # JSON list
    resume_summary = db.Column(db.Text)
    suggested_roles = db.Column(db.Text)                # JSON list
    career_interests = db.Column(db.Text)               # JSON {preferred_field, experience_level, goals}
    weak_topics = db.Column(db.Text)                    # JSON list
    total_interviews = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    sessions = db.relationship("InterviewSession", backref="user", lazy=True)
    plans = db.relationship("ImprovementPlan", backref="user", lazy=True)


class InterviewSession(db.Model):
    __tablename__ = "interview_sessions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user_profiles.id"), nullable=False)
    job_role = db.Column(db.String(128), default="Software Engineer")
    interview_type = db.Column(db.String(32), default="mixed")   # hr | technical | mixed
    difficulty = db.Column(db.String(16), default="medium")
    status = db.Column(db.String(16), default="active")          # active | completed
    overall_score = db.Column(db.Float)
    skill_breakdown = db.Column(db.Text)    # JSON {topic: score}
    dim_avg = db.Column(db.Text)            # JSON avg dimension scores
    total_questions = db.Column(db.Integer, default=8)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    questions = db.relationship("Question", backref="session", lazy=True)
    plan = db.relationship("ImprovementPlan", backref="session", lazy=True, uselist=False)


class Question(db.Model):
    __tablename__ = "questions"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("interview_sessions.id"), nullable=False)
    question_number = db.Column(db.Integer)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(32))    # hr | technical | behavioral
    topic = db.Column(db.String(128))
    difficulty = db.Column(db.String(16))
    user_answer = db.Column(db.Text)
    score = db.Column(db.Float)                 # 0–10 overall
    dimension_scores = db.Column(db.Text)       # JSON {technical_accuracy, depth, clarity, relevance, examples}
    feedback = db.Column(db.Text)
    improved_answer = db.Column(db.Text)
    what_went_well = db.Column(db.Text)
    key_missing_points = db.Column(db.Text)     # JSON list
    answered_at = db.Column(db.DateTime)


class ImprovementPlan(db.Model):
    __tablename__ = "improvement_plans"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user_profiles.id"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("interview_sessions.id"))
    plan_json = db.Column(db.Text)   # JSON structured plan
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
