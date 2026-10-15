import os
import json
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename
from models.database import db, InterviewSession, Question, UserProfile, ImprovementPlan
from ai_engine import AIEngine

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "interviewmate-secret-2024")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///interviewmate.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB

ALLOWED_EXTENSIONS = {"pdf", "txt", "doc", "docx"}

db.init_app(app)
ai = AIEngine()


# ── Jinja2 filters ────────────────────────────────────────────

@app.template_filter("from_json")
def from_json_filter(value):
    if not value:
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {}


@app.template_filter("from_json_list")
def from_json_list_filter(value):
    if not value:
        return []
    try:
        return json.loads(value)
    except Exception:
        return []


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_or_create_user():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    user = UserProfile.query.filter_by(session_id=session["user_id"]).first()
    if not user:
        user = UserProfile(session_id=session["user_id"])
        db.session.add(user)
        db.session.commit()
    return user


# ─── Routes ───────────────────────────────────────────────────

@app.route("/")
def index():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    user = get_or_create_user()
    sessions = (
        InterviewSession.query.filter_by(user_id=user.id)
        .order_by(InterviewSession.created_at.desc())
        .limit(10)
        .all()
    )
    scores = [s.overall_score for s in sessions if s.overall_score is not None]
    dates = [s.created_at.strftime("%b %d") for s in sessions if s.overall_score is not None]

    skill_map = {}
    for s in sessions:
        if s.skill_breakdown:
            try:
                skills = json.loads(s.skill_breakdown)
                for k, v in skills.items():
                    skill_map.setdefault(k, []).append(v)
            except Exception:
                pass
    avg_skills = {k: round(sum(v) / len(v), 1) for k, v in skill_map.items()}
    plan = ImprovementPlan.query.filter_by(user_id=user.id).order_by(ImprovementPlan.created_at.desc()).first()

    # Career scores for dashboard
    career_scores = {}
    if user.career_scores:
        try:
            career_scores = json.loads(user.career_scores)
        except Exception:
            pass

    return render_template(
        "dashboard.html",
        user=user,
        sessions=sessions,
        scores=scores,
        dates=dates,
        avg_skills=avg_skills,
        plan=plan,
        career_scores=career_scores,
    )


@app.route("/resume")
def resume_page():
    user = get_or_create_user()
    career_interest_questions = ai.get_career_interest_questions()
    # Load existing analysis data
    analysis = {}
    if user.skills:
        try:
            analysis["skills"] = json.loads(user.skills)
        except Exception:
            analysis["skills"] = []
    if user.career_scores:
        try:
            analysis["career_field_scores"] = json.loads(user.career_scores)
        except Exception:
            pass
    if user.resume_strengths:
        try:
            analysis["strengths"] = json.loads(user.resume_strengths)
        except Exception:
            pass
    if user.resume_weaknesses:
        try:
            analysis["weaknesses"] = json.loads(user.resume_weaknesses)
        except Exception:
            pass
    if user.suggested_roles:
        try:
            analysis["suggested_roles"] = json.loads(user.suggested_roles)
        except Exception:
            pass
    if user.resume_summary:
        analysis["summary"] = user.resume_summary
    if user.candidate_name:
        analysis["name"] = user.candidate_name

    career_recommendation = {}
    if user.career_interests:
        try:
            interests = json.loads(user.career_interests)
            if interests.get("recommendation"):
                career_recommendation = interests["recommendation"]
        except Exception:
            pass

    return render_template(
        "resume.html",
        user=user,
        analysis=analysis,
        career_interest_questions=career_interest_questions,
        career_recommendation=career_recommendation,
    )


@app.route("/api/upload-resume", methods=["POST"])
def upload_resume():
    user = get_or_create_user()
    if "resume" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["resume"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Use PDF, TXT, DOC, or DOCX"}), 400

    filename = secure_filename(f"{session['user_id']}_{file.filename}")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    resume_text = ai.extract_text(filepath)
    if not resume_text:
        return jsonify({"error": "Could not read resume content"}), 400

    analysis = ai.analyze_resume(resume_text)

    # Persist all analysis fields
    user.resume_text = resume_text
    user.resume_filename = filename
    user.resume_uploaded_at = datetime.utcnow()
    user.candidate_name = analysis.get("name", "Candidate")
    user.skills = json.dumps(analysis.get("skills", []))
    user.tech_stack = json.dumps(analysis.get("tech_stack", []))
    user.education = analysis.get("education", "")
    user.experience_years = int(analysis.get("experience_years", 0))
    user.experience_level = analysis.get("experience_level", "fresher")
    user.career_scores = json.dumps(analysis.get("career_field_scores", {}))
    user.resume_strengths = json.dumps(analysis.get("strengths", []))
    user.resume_weaknesses = json.dumps(analysis.get("weaknesses", []))
    user.resume_summary = analysis.get("summary", "")
    user.suggested_roles = json.dumps(analysis.get("suggested_roles", []))
    user.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"success": True, "analysis": analysis})


@app.route("/api/analyze-ats", methods=["POST"])
def analyze_ats():
    user = get_or_create_user()
    data = request.get_json()
    job_role = data.get("job_role", "").strip()
    if not job_role:
        return jsonify({"error": "Job role required"}), 400
    if not user.resume_text:
        return jsonify({"error": "Please upload a resume first"}), 400

    ats_result = ai.analyze_ats(user.resume_text, job_role)

    # Save ATS scores
    existing = {}
    if user.ats_scores:
        try:
            existing = json.loads(user.ats_scores)
        except Exception:
            pass
    existing[job_role] = ats_result
    user.ats_scores = json.dumps(existing)
    db.session.commit()

    return jsonify({"success": True, "ats": ats_result, "job_role": job_role})


@app.route("/api/career-interest-questions")
def career_interest_questions():
    questions = ai.get_career_interest_questions()
    return jsonify({"questions": questions})


@app.route("/api/save-career-interests", methods=["POST"])
def save_career_interests():
    user = get_or_create_user()
    data = request.get_json()
    interests = data.get("interests", {})

    if not user.resume_text:
        return jsonify({"error": "Please upload a resume first"}), 400

    # Process interests + generate recommendation
    resume_analysis = {
        "career_field_scores": json.loads(user.career_scores) if user.career_scores else {},
        "skills": json.loads(user.skills) if user.skills else [],
        "suggested_roles": json.loads(user.suggested_roles) if user.suggested_roles else [],
    }
    recommendation = ai.process_career_interests(resume_analysis, interests)
    interests["recommendation"] = recommendation

    user.career_interests = json.dumps(interests)
    db.session.commit()

    return jsonify({"success": True, "recommendation": recommendation})


@app.route("/interview")
def interview_page():
    user = get_or_create_user()
    if not user.resume_text:
        return redirect(url_for("resume_page"))
    return render_template("interview.html", user=user)


@app.route("/api/start-interview", methods=["POST"])
def start_interview():
    user = get_or_create_user()
    data = request.get_json()
    job_role = data.get("job_role", "Software Engineer")
    interview_type = data.get("interview_type", "mixed")
    difficulty = data.get("difficulty", "medium")
    total_q = int(data.get("total_questions", 8))

    if not user.resume_text:
        return jsonify({"error": "Please upload a resume first"}), 400

    iv_session = InterviewSession(
        user_id=user.id,
        job_role=job_role,
        interview_type=interview_type,
        difficulty=difficulty,
        status="active",
        total_questions=total_q,
    )
    db.session.add(iv_session)
    db.session.commit()
    session["active_interview"] = iv_session.id

    weak_topics = json.loads(user.weak_topics) if user.weak_topics else []
    question_data = ai.generate_question(
        resume_text=user.resume_text,
        job_role=job_role,
        interview_type=interview_type,
        difficulty=difficulty,
        question_number=1,
        weak_topics=weak_topics,
        asked_questions=[],
        conversation_history=[],
    )

    q = Question(
        session_id=iv_session.id,
        question_number=1,
        question_text=question_data["question"],
        question_type=question_data.get("type", interview_type),
        topic=question_data.get("topic", "General"),
        difficulty=difficulty,
    )
    db.session.add(q)
    db.session.commit()

    return jsonify({
        "session_id": iv_session.id,
        "question_id": q.id,
        "question": question_data["question"],
        "question_number": 1,
        "total_questions": total_q,
        "topic": question_data.get("topic"),
        "type": question_data.get("type"),
        "hint": question_data.get("hint", ""),
    })


@app.route("/api/submit-answer", methods=["POST"])
def submit_answer():
    user = get_or_create_user()
    data = request.get_json()
    question_id = data.get("question_id")
    answer_text = data.get("answer", "").strip()

    if not answer_text:
        return jsonify({"error": "Answer cannot be empty"}), 400

    q = db.session.get(Question, question_id)
    if not q:
        return jsonify({"error": "Question not found"}), 404

    iv_session = db.session.get(InterviewSession, q.session_id)

    prev_qs = (Question.query
               .filter_by(session_id=iv_session.id)
               .filter(Question.user_answer.isnot(None))
               .order_by(Question.question_number)
               .all())
    conversation_history = [
        {"question": pq.question_text, "answer": pq.user_answer or ""}
        for pq in prev_qs
    ]

    evaluation = ai.evaluate_answer(
        question=q.question_text,
        answer=answer_text,
        job_role=iv_session.job_role,
        topic=q.topic,
        question_type=q.question_type or "general",
        difficulty=q.difficulty or iv_session.difficulty,
        conversation_history=conversation_history,
    )

    q.user_answer = answer_text
    q.score = evaluation.get("score", 5)
    q.feedback = evaluation.get("feedback", "")
    q.improved_answer = evaluation.get("improved_answer", "")
    q.what_went_well = evaluation.get("what_went_well", "")
    q.key_missing_points = json.dumps(evaluation.get("key_missing_points", []))
    q.dimension_scores = json.dumps(evaluation.get("dimension_scores", {}))
    q.answered_at = datetime.utcnow()
    db.session.commit()

    answered_count = Question.query.filter_by(session_id=iv_session.id).filter(Question.user_answer.isnot(None)).count()
    total_questions = iv_session.total_questions or 8

    if answered_count >= total_questions:
        return jsonify({
            "evaluation": evaluation,
            "interview_complete": True,
            "session_id": iv_session.id,
        })

    # Adaptive difficulty
    recent_scores = [qq.score for qq in prev_qs[-3:] if qq.score is not None]
    recent_scores.append(q.score)
    avg_recent = sum(recent_scores) / len(recent_scores) if recent_scores else 5
    if avg_recent >= 7.5:
        next_difficulty = "hard"
    elif avg_recent <= 4.0:
        next_difficulty = "easy"
    else:
        next_difficulty = iv_session.difficulty

    asked = [qq.question_text for qq in Question.query.filter_by(session_id=iv_session.id).all()]
    weak_topics = json.loads(user.weak_topics) if user.weak_topics else []
    conv_history_full = conversation_history + [{"question": q.question_text, "answer": answer_text}]

    next_q_data = ai.generate_question(
        resume_text=user.resume_text,
        job_role=iv_session.job_role,
        interview_type=iv_session.interview_type,
        difficulty=next_difficulty,
        question_number=answered_count + 1,
        weak_topics=weak_topics,
        asked_questions=asked,
        conversation_history=conv_history_full,
        last_answer=answer_text,
        last_score=q.score,
    )

    nq = Question(
        session_id=iv_session.id,
        question_number=answered_count + 1,
        question_text=next_q_data["question"],
        question_type=next_q_data.get("type", iv_session.interview_type),
        topic=next_q_data.get("topic", "General"),
        difficulty=next_difficulty,
    )
    db.session.add(nq)
    db.session.commit()

    return jsonify({
        "evaluation": evaluation,
        "interview_complete": False,
        "next_question": {
            "question_id": nq.id,
            "question": next_q_data["question"],
            "question_number": answered_count + 1,
            "topic": next_q_data.get("topic"),
            "type": next_q_data.get("type"),
            "hint": next_q_data.get("hint", ""),
            "difficulty": next_difficulty,
        },
    })


@app.route("/api/finish-interview", methods=["POST"])
def finish_interview():
    user = get_or_create_user()
    data = request.get_json()
    session_id = data.get("session_id")

    iv_session = db.session.get(InterviewSession, session_id)
    if not iv_session:
        return jsonify({"error": "Session not found"}), 404

    questions = Question.query.filter_by(session_id=session_id).filter(Question.user_answer.isnot(None)).all()
    if not questions:
        return jsonify({"error": "No answered questions"}), 400

    scores = [q.score for q in questions if q.score is not None]
    overall = round(sum(scores) / len(scores), 1) if scores else 0

    topic_scores = {}
    for q in questions:
        topic_scores.setdefault(q.topic, []).append(q.score or 5)
    breakdown = {t: round(sum(v) / len(v), 1) for t, v in topic_scores.items()}

    # Average dimension scores across session
    dim_totals = {}
    dim_counts = {}
    for q in questions:
        if q.dimension_scores:
            try:
                dims = json.loads(q.dimension_scores)
                for k, v in dims.items():
                    dim_totals[k] = dim_totals.get(k, 0) + v
                    dim_counts[k] = dim_counts.get(k, 0) + 1
            except Exception:
                pass
    dim_avg = {k: round(dim_totals[k] / dim_counts[k], 1) for k in dim_totals}

    iv_session.overall_score = overall
    iv_session.skill_breakdown = json.dumps(breakdown)
    iv_session.dim_avg = json.dumps(dim_avg)
    iv_session.status = "completed"
    iv_session.completed_at = datetime.utcnow()
    iv_session.total_questions = len(questions)

    weak = [t for t, s in breakdown.items() if s < 5.5]
    user.weak_topics = json.dumps(weak)
    user.total_interviews = (user.total_interviews or 0) + 1
    db.session.commit()

    exp_level = user.experience_level or "fresher"

    plan_text = ai.generate_improvement_plan(
        job_role=iv_session.job_role,
        weak_topics=weak,
        overall_score=overall,
        breakdown=breakdown,
        experience_level=exp_level,
    )
    plan = ImprovementPlan(
        user_id=user.id,
        session_id=session_id,
        plan_json=json.dumps(plan_text),
    )
    db.session.add(plan)
    db.session.commit()

    return jsonify({
        "overall_score": overall,
        "breakdown": breakdown,
        "dim_avg": dim_avg,
        "weak_topics": weak,
        "plan": plan_text,
        "total_questions": len(questions),
    })


@app.route("/results/<int:session_id>")
def results_page(session_id):
    user = get_or_create_user()
    iv_session = db.session.get(InterviewSession, session_id)
    if not iv_session:
        from flask import abort
        abort(404)
    questions = Question.query.filter_by(session_id=session_id).all()
    plan = ImprovementPlan.query.filter_by(session_id=session_id).first()
    breakdown = json.loads(iv_session.skill_breakdown) if iv_session.skill_breakdown else {}
    dim_avg = json.loads(iv_session.dim_avg) if iv_session.dim_avg else {}
    plan_data = json.loads(plan.plan_json) if plan and plan.plan_json else {}
    return render_template(
        "results.html",
        iv_session=iv_session,
        questions=questions,
        breakdown=breakdown,
        dim_avg=dim_avg,
        plan_data=plan_data,
        user=user,
    )


@app.route("/improvement-plan")
def improvement_plan_page():
    user = get_or_create_user()
    plan = ImprovementPlan.query.filter_by(user_id=user.id).order_by(ImprovementPlan.created_at.desc()).first()
    plan_data = json.loads(plan.plan_json) if plan and plan.plan_json else {}
    return render_template("plan.html", user=user, plan_data=plan_data, plan=plan)


@app.route("/history")
def history_page():
    user = get_or_create_user()
    # All completed sessions
    sessions = (
        InterviewSession.query.filter_by(user_id=user.id)
        .order_by(InterviewSession.created_at.desc())
        .all()
    )
    # ATS scores
    ats_scores = {}
    if user.ats_scores:
        try:
            ats_scores = json.loads(user.ats_scores)
        except Exception:
            pass
    # Career scores
    career_scores = {}
    if user.career_scores:
        try:
            career_scores = json.loads(user.career_scores)
        except Exception:
            pass

    return render_template(
        "history.html",
        user=user,
        sessions=sessions,
        ats_scores=ats_scores,
        career_scores=career_scores,
    )


@app.route("/api/delete-session/<int:session_id>", methods=["DELETE"])
def delete_session(session_id):
    user = get_or_create_user()
    iv_session = db.session.get(InterviewSession, session_id)
    if not iv_session or iv_session.user_id != user.id:
        return jsonify({"error": "Session not found"}), 404

    # Delete related data
    Question.query.filter_by(session_id=session_id).delete()
    ImprovementPlan.query.filter_by(session_id=session_id).delete()
    db.session.delete(iv_session)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/delete-resume", methods=["DELETE"])
def delete_resume():
    user = get_or_create_user()
    # Clear all resume data
    user.resume_text = None
    user.resume_filename = None
    user.resume_uploaded_at = None
    user.candidate_name = None
    user.skills = None
    user.tech_stack = None
    user.education = None
    user.career_scores = None
    user.ats_scores = None
    user.resume_strengths = None
    user.resume_weaknesses = None
    user.resume_summary = None
    user.suggested_roles = None
    user.career_interests = None
    user.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/user-stats")
def user_stats():
    user = get_or_create_user()
    sessions = InterviewSession.query.filter_by(user_id=user.id, status="completed").all()
    scores = [s.overall_score for s in sessions if s.overall_score]
    avg = round(sum(scores) / len(scores), 1) if scores else 0
    return jsonify({
        "total_interviews": len(sessions),
        "average_score": avg,
        "best_score": max(scores) if scores else 0,
        "weak_topics": json.loads(user.weak_topics) if user.weak_topics else [],
    })


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
