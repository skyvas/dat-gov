"""Synthetic data generation for Northbridge University.

Governance idea demonstrated here: the *source* is deliberately messy.
Real admissions CRMs and finance systems send duplicates, nulls, bad
emails, future dates and negative amounts — so the generator injects
~2-3% dirty rows per large dataset. If Silver quietly dropped them,
nobody would ever know. Instead they are preserved in Bronze and
quarantined in Silver, with counts in the quality report.

Everything is deterministic (``random.Random(SEED)``, stdlib only, no
Faker): re-running with the same seed reproduces byte-identical CSVs.
All people are fictional; gov_ids are synthetic (``NB-100000`` style).
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

from .config import RAW_DIR, SEED, TERMS

FIRST = [
    "Aarav", "Amara", "Arjun", "Aisha", "Liam", "Maya", "Noah", "Priya", "Ethan", "Zoe",
    "Lucas", "Ivy", "Omar", "Sofia", "Kabir", "Nina", "Felix", "Tara", "Hugo", "Lena",
    "Raj", "Elena", "Marcus", "Hana", "Diego", "Clara", "Yuki", "Owen", "Freya", "Kiran",
    "Nadia", "Sam", "Rosa", "Vikram", "Ella", "Jonas", "Meera", "Theo", "Ines", "Dante",
]
LAST = [
    "Patel", "Chen", "Singh", "Kaur", "Smith", "Garcia", "Kim", "Nguyen", "Brown", "Wilson",
    "Sharma", "Ali", "Martin", "Lee", "Gupta", "Roy", "Das", "Costa", "Novak", "Fischer",
    "Ahmed", "Dubey", "Rossi", "Silva", "Tanaka", "Meyer", "Khan", "Osei", "Petrov", "Larsen",
    "Moreau", "Iyer", "Haddad", "Berg", "Kaur", "Nair", "Frost", "Vega", "Okafor", "Lind",
]
DEPARTMENTS = [
    ("DEPT-CS", "Computer Science", "School of Science"),
    ("DEPT-BUS", "Business Administration", "School of Business"),
    ("DEPT-ECO", "Economics", "School of Social Sciences"),
    ("DEPT-BIO", "Biology", "School of Science"),
    ("DEPT-PSY", "Psychology", "School of Social Sciences"),
    ("DEPT-ENG", "Engineering", "School of Engineering"),
    ("DEPT-MAT", "Mathematics", "School of Science"),
    ("DEPT-NUR", "Nursing", "School of Health Sciences"),
]
PROGRAMS = [
    "Computer Science", "Data Science", "Business Administration", "Economics",
    "Biology", "Psychology", "Engineering", "Nursing",
]
PROGRAM_DEPT = dict(zip(PROGRAMS, [d[0] for d in DEPARTMENTS]))
COURSE_TITLES = {
    "DEPT-CS": ["Intro to Programming", "Data Structures", "Databases", "Algorithms", "Machine Learning"],
    "DEPT-BUS": ["Principles of Management", "Marketing", "Finance", "Organisational Behaviour", "Strategy"],
    "DEPT-ECO": ["Microeconomics", "Macroeconomics", "Econometrics", "Development Economics", "Game Theory"],
    "DEPT-BIO": ["Cell Biology", "Genetics", "Ecology", "Human Anatomy", "Microbiology"],
    "DEPT-PSY": ["Intro to Psychology", "Cognitive Psychology", "Developmental Psychology",
                "Statistics for Psych", "Abnormal Psychology"],
    "DEPT-ENG": ["Statics", "Thermodynamics", "Circuits", "Materials Science", "Control Systems"],
    "DEPT-MAT": ["Calculus I", "Linear Algebra", "Probability", "Discrete Maths", "Numerical Methods"],
    "DEPT-NUR": ["Foundations of Nursing", "Pharmacology", "Community Health", "Clinical Practice", "Pathophysiology"],
}
COUNTRIES = ["Canada", "Canada", "Canada", "United States", "India",
             "China", "Nigeria", "Brazil", "United Kingdom", "Philippines"]
CHANNELS = ["online", "agent", "high-school", "direct"]
TERM_START = {"2024-Fall": date(2024, 9, 3), "2025-Spring": date(2025, 1, 7),
              "2025-Fall": date(2025, 9, 2), "2026-Spring": date(2026, 1, 6)}


def _dob(rng: random.Random) -> date:
    return date(rng.randint(2001, 2007), rng.randint(1, 12), rng.randint(1, 28))


def _email(first: str, last: str, n: int) -> str:
    return f"{first.lower()}.{last.lower()}{n}@example.edu"


def _phone(rng: random.Random) -> str:
    return f"+1-555-{rng.randint(100, 999)}-{rng.randint(1000, 9999)}"


def generate_all(raw_dir: Path = RAW_DIR) -> dict[str, int]:
    """Generate every raw CSV. Returns {dataset: row_count_including_dirty}."""
    rng = random.Random(SEED)
    raw_dir.mkdir(parents=True, exist_ok=True)
    data: dict[str, list[dict]] = {}

    # --- Academics (reference data first) ---
    data["departments"] = [
        {"department_id": d, "department_name": n, "school": s,
         "budget": round(rng.uniform(800_000, 4_500_000), 2), "founded_year": rng.randint(1960, 2010)}
        for d, n, s in DEPARTMENTS
    ]
    courses, dept_courses = [], {}
    for dept_id, _, _ in DEPARTMENTS:
        prefix = dept_id.split("-")[1][:2]
        dept_courses[dept_id] = []
        for i, title in enumerate(COURSE_TITLES[dept_id]):
            cid = f"{prefix}{101 + i * 100}"
            dept_courses[dept_id].append(cid)
            courses.append({"course_id": cid, "department_id": dept_id,
                            "course_code": f"{prefix} {101 + i * 100}", "title": title,
                            "credits": 3 if i < 4 else 4, "level": 100 + (i % 4) * 100})
    data["courses"] = courses
    faculty = []
    for i in range(80):
        dept_id = DEPARTMENTS[i % 8][0]
        fn, ln = rng.choice(FIRST), rng.choice(LAST)
        faculty.append({"faculty_id": f"FAC-{i + 1:04d}", "first_name": fn, "last_name": ln,
                        "email": _email(fn, ln, i + 1), "department_id": dept_id,
                        "rank": rng.choices(["Assistant", "Associate", "Full", "Lecturer"], weights=[3, 3, 2, 2])[0],
                        "hire_date": date(rng.randint(2010, 2024), rng.randint(1, 12), rng.randint(1, 28)).isoformat(),
                        "status": rng.choices(["active", "on_leave", "retired"], weights=[88, 7, 5])[0]})
    data["faculty"] = faculty
    sections = []
    for i in range(120):
        term = TERMS[i % 4]
        course = rng.choice(courses)
        dept_faculty = [f for f in faculty if f["department_id"] == course["department_id"]]
        sections.append({"section_id": f"SEC-{i + 1:04d}", "course_id": course["course_id"],
                         "faculty_id": rng.choice(dept_faculty)["faculty_id"], "term": term,
                         "capacity": rng.choice([20, 30, 40, 50, 60]),
                         "room": f"NB-{rng.randint(100, 420)}",
                         "modality": rng.choices(["in-person", "online", "hybrid"], weights=[6, 2, 2])[0],
                         "schedule": rng.choice(["Mon/Wed 10:00", "Tue/Thu 13:00", "Mon/Wed/Fri 09:00", "Tue 18:00"])})
    data["sections"] = sections

    # --- Admissions ---
    # Outcome per applicant drives the funnel: 3000 enrolled, 400 admitted-not-enrolled,
    # 300 waitlisted, 1300 rejected -> applied 5000, admitted 3400, enrolled 3000.
    outcomes = (["enrolled"] * 3000 + ["admitted"] * 400 + ["waitlisted"] * 300 + ["rejected"] * 1300)
    rng.shuffle(outcomes)
    applicants, applications = [], []
    for i in range(5000):
        fn, ln = rng.choice(FIRST), rng.choice(LAST)
        program = rng.choice(PROGRAMS)
        term = rng.choice(TERMS)
        status = outcomes[i]
        app_date = TERM_START[term] - timedelta(days=rng.randint(30, 180))
        applicants.append({"applicant_id": f"APP-{i + 1:06d}", "first_name": fn, "last_name": ln,
                           "email": _email(fn, ln, i + 1), "phone": _phone(rng),
                           "date_of_birth": _dob(rng).isoformat(), "gov_id": f"NB-{100000 + i}",
                           "country": rng.choice(COUNTRIES),
                           "residency": rng.choices(["domestic", "international"], weights=[7, 3])[0],
                           "program": program, "channel": rng.choice(CHANNELS),
                           "gpa": round(rng.uniform(2.0, 4.0), 2),
                           "application_date": app_date.isoformat(), "status": status})
        applications.append({"application_id": f"APL-{i + 1:06d}", "applicant_id": f"APP-{i + 1:06d}",
                             "program": program, "term": term, "channel": applicants[-1]["channel"],
                             "gpa": applicants[-1]["gpa"],
                             "submitted_date": app_date.isoformat(),
                             "decision_date": (app_date + timedelta(days=rng.randint(14, 60))).isoformat(),
                             "status": "admitted" if status == "admitted" else status})
    # Second applications for 200 applicants (different term/program, mostly not enrolled).
    for j in range(200):
        idx = rng.randrange(5000)
        a = applicants[idx]
        term = rng.choice(TERMS)
        applications.append({"application_id": f"APL-{5001 + j:06d}", "applicant_id": a["applicant_id"],
                             "program": rng.choice(PROGRAMS), "term": term, "channel": a["channel"],
                             "gpa": a["gpa"], "submitted_date": a["application_date"],
                             "decision_date": a["application_date"],
                             "status": rng.choices(["rejected", "admitted", "waitlisted"], weights=[6, 3, 1])[0]})
    data["applicants"] = applicants
    data["applications"] = applications

    # --- Registrar: students are the enrolled applicants ---
    enrolled_apps = [a for a in applicants if a["status"] == "enrolled"]
    assert len(enrolled_apps) == 3000
    students = []
    for i, a in enumerate(enrolled_apps):
        students.append({"student_id": f"STU-{i + 1:06d}", "applicant_id": a["applicant_id"],
                         "first_name": a["first_name"], "last_name": a["last_name"],
                         "email": a["email"], "phone": a["phone"], "date_of_birth": a["date_of_birth"],
                         "gov_id": a["gov_id"], "program": a["program"], "residency": a["residency"],
                         "enrollment_year": 2024 if a["application_date"] < "2025-01-01" else 2025,
                         "term_start": "2024-Fall" if a["application_date"] < "2025-01-01" else "2025-Fall",
                         "status": rng.choices(["active", "graduated", "withdrawn"], weights=[85, 7, 8])[0]})
    data["students"] = students

    # Enrollments: exactly 4 per student = 12,000.
    course_by_id = {c["course_id"]: c for c in courses}
    enrollments = []
    for i, s in enumerate(students):
        terms = rng.sample(TERMS, k=rng.choice([2, 3, 3, 4]))
        for k in range(4):
            sec = rng.choice([x for x in sections if x["term"] == terms[k % len(terms)]])
            enrollments.append({"enrollment_id": f"ENR-{len(enrollments) + 1:06d}",
                                "student_id": s["student_id"], "section_id": sec["section_id"],
                                "course_id": sec["course_id"], "term": sec["term"],
                                "grade": rng.choices(
                                    ["A", "B", "C", "D", "F", "W", "IP", ""],
                                    weights=[25, 30, 20, 8, 4, 3, 5, 5])[0] or "",
                                "credits": course_by_id[sec["course_id"]]["credits"],
                                "enrollment_date": (
                                    TERM_START[sec["term"]] - timedelta(days=rng.randint(0, 14))
                                ).isoformat(),
                                "status": rng.choices(["completed", "enrolled", "withdrawn"], weights=[75, 20, 5])[0]})
    data["enrollments"] = enrollments

    # --- Finance ---
    student_terms: dict[str, list[str]] = {}
    for e in enrollments:
        student_terms.setdefault(e["student_id"], [])
        if e["term"] not in student_terms[e["student_id"]]:
            student_terms[e["student_id"]].append(e["term"])
    charges = []
    for s in students:
        n_terms = rng.choice([2, 3, 3])
        for term in sorted(student_terms[s["student_id"]])[:n_terms]:
            base = 5200.0 if s["residency"] == "domestic" else 13500.0
            amount = round(base * rng.uniform(0.95, 1.1), 2)
            charges.append({"charge_id": f"CHG-{len(charges) + 1:06d}", "student_id": s["student_id"],
                            "term": term, "charge_type": "tuition", "amount": amount,
                            "due_date": (TERM_START[term] + timedelta(days=30)).isoformat(),
                            "status": rng.choices(["billed", "paid", "waived", "overdue"], weights=[30, 55, 5, 10])[0]})
            if rng.random() < 0.3:  # extra fee charge for ~30% of terms
                charges.append({"charge_id": f"CHG-{len(charges) + 1:06d}", "student_id": s["student_id"],
                                "term": term, "charge_type": rng.choice(["fees", "housing", "lab"]),
                                "amount": round(rng.uniform(150, 900), 2),
                                "due_date": (TERM_START[term] + timedelta(days=30)).isoformat(),
                                "status": "billed"})
    data["tuition_charges"] = charges
    payments = []
    for ch in rng.sample(charges, k=6000):
        payments.append({"payment_id": f"PAY-{len(payments) + 1:06d}", "student_id": ch["student_id"],
                         "charge_id": ch["charge_id"], "term": ch["term"],
                         "amount": round(float(ch["amount"]) * rng.uniform(0.6, 1.0), 2),
                         "payment_date": (TERM_START[ch["term"]] + timedelta(days=rng.randint(0, 60))).isoformat(),
                         "method": rng.choice(["card", "bank_transfer", "e-transfer", "cash"]),
                         "status": rng.choices(["completed", "pending", "refunded"], weights=[94, 4, 2])[0]})
    data["payments"] = payments
    aid = []
    for i, s in enumerate(rng.sample(students, k=2000)):
        term = rng.choice(student_terms[s["student_id"]])
        aid.append({"aid_id": f"AID-{i + 1:06d}", "student_id": s["student_id"], "term": term,
                    "aid_type": rng.choice(["grant", "scholarship", "loan", "work-study"]),
                    "amount": round(rng.uniform(1000, 8000), 2),
                    "status": rng.choices(["awarded", "disbursed", "declined"], weights=[20, 70, 10])[0]})
    data["financial_aid"] = aid

    # --- Dirty rows (~2-3% on the large datasets) ---
    def _dup(rows: list[dict], n: int) -> list[dict]:
        return [dict(rng.choice(rows)) for _ in range(n)]

    data["applicants"] += _dup(applicants, 40)
    for j in range(80):
        bad = dict(rng.choice(applicants))
        bad["applicant_id"] = f"APP-9{j:05d}"
        if j < 30:
            bad["email"] = ""
        elif j < 60:
            bad["email"] = "not-an-email"
        else:
            bad["date_of_birth"] = "2031-01-15"
        data["applicants"].append(bad)
    data["applications"] += _dup(applications, 40)
    for j in range(90):
        bad = dict(rng.choice(applications))
        bad["application_id"] = f"APL-9{j:05d}"
        if j < 45:
            bad["term"] = "2099-Winter"
        else:
            bad["applicant_id"] = "APP-999999"
        data["applications"].append(bad)
    data["students"] += _dup(students, 40)
    for j in range(50):
        bad = dict(rng.choice(students))
        bad["student_id"] = f"STU-9{j:05d}"
        bad["date_of_birth"] = "2032-06-01" if j < 25 else bad["date_of_birth"]
        if j >= 25:
            bad["email"] = ""
        data["students"].append(bad)
    data["enrollments"] += _dup(enrollments, 100)
    for j in range(200):
        bad = dict(rng.choice(enrollments))
        bad["enrollment_id"] = f"ENR-9{j:05d}"
        if j < 100:
            bad["course_id"] = "XX999"
        elif j < 150:
            bad["student_id"] = "STU-999999"
        else:
            bad["term"] = "2099-Winter"
        data["enrollments"].append(bad)
    data["tuition_charges"] += _dup(charges, 60)
    for j in range(140):
        bad = dict(rng.choice(charges))
        bad["charge_id"] = f"CHG-9{j:05d}"
        bad["amount"] = -500.00 if j < 100 else bad["amount"]
        if j >= 100:
            bad["student_id"] = "STU-999999"
        data["tuition_charges"].append(bad)
    data["payments"] += _dup(payments, 50)
    for j in range(100):
        bad = dict(rng.choice(payments))
        bad["payment_id"] = f"PAY-9{j:05d}"
        bad["amount"] = -100.00
        data["payments"].append(bad)
    data["financial_aid"] += _dup(aid, 20)
    for j in range(40):
        bad = dict(rng.choice(aid))
        bad["aid_id"] = f"AID-9{j:05d}"
        bad["amount"] = -250.00
        data["financial_aid"].append(bad)
    data["courses"] += _dup(courses, 1)
    data["faculty"] += _dup(faculty, 1)
    for j in range(1):
        bad = dict(rng.choice(faculty))
        bad["faculty_id"] = f"FAC-9{j:04d}"
        bad["email"] = "not-an-email"
        data["faculty"].append(bad)
    data["sections"] += _dup(sections, 1)
    for j in range(2):
        bad = dict(rng.choice(sections))
        bad["section_id"] = f"SEC-9{j:04d}"
        bad["term"] = "2099-Winter"
        data["sections"].append(bad)

    counts = {}
    for name, rows in data.items():
        path = raw_dir / f"{name}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        counts[name] = len(rows)
    return counts
