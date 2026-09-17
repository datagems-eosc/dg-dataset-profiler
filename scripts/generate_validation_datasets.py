"""Generate synthetic datasets for validating a profiler deployment.

Each dataset looks like a plausible real one and carries data quality problems
planted on purpose, so a run can be checked against known targets:

    clinic_appointments   CSV, UTF-8, comma-delimited
    air_quality_readings  CSV, UTF-8 *with BOM*, semicolon-delimited, Greek text
    course_enrolments     Excel workbook, two sheets

Together they cover every tabular reader path: delimiter sniffing, the BOM and
non-ASCII handling, and one record set per Excel sheet.

Output goes to tests/assets/validation/<name>/data/ (visible to the dev stack
through its ./tests mount), plus a ProfilingRequest body per dataset. Seeded, so
reruns produce identical files.

    python scripts/generate_validation_datasets.py
"""

import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path("tests/assets/validation")
SEED = 20260916

# Stands in for the dataset id the deployment assigns on upload. The storage path
# is keyed by the same id, so it appears twice in each request body.
ID_PLACEHOLDER = "<DATASET_ID>"

FIRST = ["Maria", "Giorgos", "Eleni", "Nikos", "Sofia", "Dimitris", "Anna", "Kostas",
         "Katerina", "Yannis", "Laura", "Marco", "Chiara", "Jonas", "Ines", "Tomas",
         "Clara", "Pablo", "Lea", "Mateo", "Hanna", "Luca", "Zoe", "Felix"]
LAST = ["Papadopoulou", "Georgiou", "Nikolaou", "Ioannou", "Rossi", "Bianchi",
        "Schmidt", "Weber", "Garcia", "Lopez", "Martin", "Dubois", "Silva",
        "Costa", "Novak", "Horvat", "Jensen", "Nielsen", "Kowalski", "Popescu"]


def _pick(rng, share, rows):
    """Row indices for a planted issue affecting roughly `share` of rows."""
    k = max(3, int(rows * share))
    return set(rng.sample(range(rows), k))


# ---------------------------------------------------------------------------
# 1. Outpatient clinic appointments
# ---------------------------------------------------------------------------

def clinic_appointments(rng):
    n = 480
    departments = ["Cardiology", "Dermatology", "Endocrinology", "Neurology",
                   "Orthopaedics", "Paediatrics", "General Practice"]
    physicians = [f"Dr. {rng.choice(FIRST)} {rng.choice(LAST)}" for _ in range(14)]
    nationalities = ["GR", "IT", "DE", "ES", "FR", "PT", "CY", "BG"]

    bad_dob = _pick(rng, 0.08, n)       # DD/MM/YYYY among ISO dates
    bad_age = _pick(rng, 0.02, n)       # negative or implausible ages
    bad_sex = _pick(rng, 0.10, n)       # female / Male / FEMALE among F / M
    bad_bp = _pick(rng, 0.02, n)        # 0 or 400 mmHg
    bad_phone = _pick(rng, 0.12, n)     # bare digits among +30 formatted numbers
    bad_pay = _pick(rng, 0.09, n)       # Paid / PAID / settled among paid

    rows = []
    start = date(2025, 1, 6)
    for i in range(n):
        dob = date(1938, 1, 1) + timedelta(days=rng.randint(0, 31000))
        appt = start + timedelta(days=rng.randint(0, 250))
        age = appt.year - dob.year - ((appt.month, appt.day) < (dob.month, dob.day))
        sex = rng.choice(["F", "M"])
        first, last = rng.choice(FIRST), rng.choice(LAST)
        systolic = rng.randint(100, 165)
        digits = f"{rng.randint(2100000000, 2109999999)}"

        rows.append({
            "appointment_id": f"APT-{100000 + i}",
            "patient_id": f"P{rng.randint(10000, 99999)}",
            "patient_name": f"{first} {last}",
            "date_of_birth": dob.strftime("%d/%m/%Y") if i in bad_dob else dob.isoformat(),
            "age": (rng.choice([-4, -12, 142, 187]) if i in bad_age else age),
            "sex": (rng.choice(["female", "Male", "FEMALE", "male"]) if i in bad_sex else sex),
            "nationality": rng.choice(nationalities),
            "email": f"{first.lower()}.{last.lower()}{rng.randint(1, 99)}@example.org",
            "phone": digits if i in bad_phone else f"+30 {digits[:3]} {digits[3:]}",
            "appointment_date": appt.isoformat(),
            "department": rng.choice(departments),
            "attending_physician": rng.choice(physicians),
            "systolic_bp": (rng.choice([0, 400]) if i in bad_bp else systolic),
            "diastolic_bp": systolic - rng.randint(35, 55),
            "fee_eur": round(rng.choice([40, 55, 60, 75, 90, 120]) * rng.uniform(0.95, 1.05), 2),
            "payment_status": (rng.choice(["Paid", "PAID", "settled"]) if i in bad_pay
                               else rng.choice(["paid", "paid", "paid", "pending", "insurance"])),
        })

    out = ROOT / "clinic_appointments" / "data"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "clinic_appointments_2025.csv", index=False)

    return {
        "name": "Outpatient Clinic Appointments 2025",
        "headline": "Appointment-level records from a multi-department outpatient clinic.",
        "description": (
            "Appointment records from a multi-department outpatient clinic covering January to "
            "September 2025. Each row is a single appointment with patient demographics, contact "
            "details, the attending department and physician, blood pressure taken at intake, the "
            "consultation fee and its payment status. Synthetic data, generated for validating the "
            "dataset profiler deployment; it contains no real patient information."
        ),
        "fields_of_science": ["HEALTH SCIENCES"],
        "keywords": ["healthcare", "outpatient", "appointments", "clinic"],
        "country": "GR",
        "license": "CC BY 4.0",
    }


# ---------------------------------------------------------------------------
# 2. Urban air quality sensor readings
# ---------------------------------------------------------------------------

def air_quality_readings(rng):
    stations = [
        ("ATH-PAT", "Αθήνα - Πατησίων", "Athens", 37.9995, 23.7330),
        ("ATH-MAR", "Αθήνα - Μαρούσι", "Athens", 38.0310, 23.7870),
        ("PIR-CEN", "Πειραιάς - Κέντρο", "Piraeus", 37.9420, 23.6470),
        ("THE-EGN", "Θεσσαλονίκη - Εγνατία", "Thessaloniki", 40.6370, 22.9410),
        ("THE-KAL", "Θεσσαλονίκη - Καλαμαριά", "Thessaloniki", 40.5850, 22.9510),
        ("PAT-CEN", "Πάτρα - Κέντρο", "Patras", 38.2460, 21.7350),
    ]
    municipality_variants = {"Athens": ["ATHENS", "Athína", "athens"],
                             "Thessaloniki": ["THESSALONIKI", "Thessaloníki"]}
    n = 600

    bad_hum = _pick(rng, 0.03, n)       # humidity above 100 %
    bad_temp = _pick(rng, 0.02, n)      # -999 sensor sentinel
    bad_ts = _pick(rng, 0.10, n)        # DD/MM/YYYY HH:MM among ISO timestamps
    bad_muni = _pick(rng, 0.12, n)      # ATHENS / Athína among Athens
    bad_pm = _pick(rng, 0.02, n)        # negative particulate readings

    rows = []
    t0 = datetime(2025, 3, 1, 0, 0)
    for i in range(n):
        code, name, muni, lat, lon = stations[i % len(stations)]
        ts = t0 + timedelta(hours=i // len(stations))
        pm25 = round(rng.uniform(4, 38), 1)
        if i in bad_muni and muni in municipality_variants:
            muni = rng.choice(municipality_variants[muni])

        rows.append({
            "reading_id": 900000 + i,
            "station_code": code,
            "station_name": name,
            "municipality": muni,
            "latitude": lat,
            "longitude": lon,
            "measured_at": (ts.strftime("%d/%m/%Y %H:%M") if i in bad_ts
                            else ts.strftime("%Y-%m-%dT%H:%M:%S")),
            "pm2_5_ugm3": (-round(rng.uniform(1, 9), 1) if i in bad_pm else pm25),
            "pm10_ugm3": round(pm25 * rng.uniform(1.4, 2.1), 1),
            "no2_ugm3": round(rng.uniform(8, 95), 1),
            "o3_ugm3": round(rng.uniform(20, 140), 1),
            "temperature_c": (-999 if i in bad_temp else round(rng.uniform(6, 24), 1)),
            "relative_humidity_pct": (rng.choice([104, 118, 135]) if i in bad_hum
                                      else rng.randint(35, 92)),
        })

    out = ROOT / "air_quality_readings" / "data"
    out.mkdir(parents=True, exist_ok=True)
    # utf-8-sig writes a byte-order mark, and the semicolon matches how European
    # spreadsheet exports usually arrive - both exercised on purpose.
    pd.DataFrame(rows).to_csv(out / "air_quality_hourly_march_2025.csv",
                              index=False, sep=";", encoding="utf-8-sig")

    return {
        "name": "Urban Air Quality Sensor Readings - March 2025",
        "headline": "Hourly pollutant and weather readings from urban monitoring stations in Greece.",
        "description": (
            "Hourly readings from six urban air quality monitoring stations in Athens, Piraeus, "
            "Thessaloniki and Patras during March 2025. Each row records particulate matter "
            "(PM2.5, PM10), nitrogen dioxide and ozone concentrations alongside air temperature and "
            "relative humidity, with the station's coordinates. Station names are in Greek. "
            "Synthetic data, generated for validating the dataset profiler deployment."
        ),
        "fields_of_science": ["EARTH AND RELATED ENVIRONMENTAL SCIENCES"],
        "keywords": ["air quality", "pollution", "sensors", "environment", "Greece"],
        "country": "GR",
        "license": "CC BY 4.0",
    }


# ---------------------------------------------------------------------------
# 3. University course enrolments (Excel, two sheets)
# ---------------------------------------------------------------------------

def course_enrolments(rng):
    courses_spec = [
        ("CS101", "Introduction to Programming", "Computer Science", 6),
        ("CS240", "Data Structures and Algorithms", "Computer Science", 7.5),
        ("CS355", "Database Systems", "Computer Science", 6),
        ("MA110", "Linear Algebra", "Mathematics", 6),
        ("MA215", "Probability and Statistics", "Mathematics", 7.5),
        ("PH120", "Classical Mechanics", "Physics", 6),
        ("EC201", "Microeconomics", "Economics", 5),
        ("EC310", "Econometrics", "Economics", 7.5),
    ]
    semester_variants = ["FALL", "Autumn"]

    courses = []
    for idx, (code, title, dept, ects) in enumerate(courses_spec):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        semester = rng.choice(["Fall", "Spring"])
        if idx in (2, 5):
            semester = rng.choice(semester_variants)
        courses.append({
            "course_code": code,
            "course_title": title,
            "department": dept,
            "ects_credits": ects,
            "semester": semester,
            "instructor_email": f"{first[0].lower()}.{last.lower()}@university.example.edu",
        })

    n = 520
    bad_sid = _pick(rng, 0.12, n)       # bare digits among S2024-00123
    bad_grade = _pick(rng, 0.02, n)     # grades outside the 0-10 scale
    bad_att = _pick(rng, 0.03, n)       # attendance above 100 %
    bad_status = _pick(rng, 0.10, n)    # Active / enrolled among active
    bad_year = _pick(rng, 0.10, n)      # 2024-2025 among 2024/25

    enrolments = []
    for i in range(n):
        cohort = rng.choice([2022, 2023, 2024])
        serial = rng.randint(1, 450)
        status = rng.choice(["active", "active", "active", "completed", "withdrawn"])
        grade = round(rng.uniform(3.5, 10), 1) if status == "completed" else None
        if i in bad_grade:
            grade = rng.choice([-1.0, 11.5, 14.0])
        enrolments.append({
            "enrolment_id": 70000 + i,
            "student_id": (f"{str(cohort)[2:]}{serial:05d}" if i in bad_sid
                           else f"S{cohort}-{serial:05d}"),
            "course_code": rng.choice(courses_spec)[0],
            "academic_year": "2024-2025" if i in bad_year else "2024/25",
            "grade": grade,
            "attendance_pct": (rng.choice([108, 115, 130]) if i in bad_att
                               else rng.randint(40, 100)),
            "enrolment_status": (rng.choice(["Active", "enrolled", "ACTIVE"]) if i in bad_status
                                 else status),
        })

    out = ROOT / "course_enrolments" / "data"
    out.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out / "course_enrolments_2024_25.xlsx", engine="openpyxl") as xw:
        pd.DataFrame(courses).to_excel(xw, sheet_name="courses", index=False)
        pd.DataFrame(enrolments).to_excel(xw, sheet_name="enrolments", index=False)

    return {
        "name": "University Course Enrolments 2024/25",
        "headline": "Course catalogue and student enrolment records for one academic year.",
        "description": (
            "Course catalogue and student enrolment records for the 2024/25 academic year across "
            "four departments. The workbook holds two sheets: the courses offered, with credits, "
            "semester and instructor contact, and the individual enrolments, with the student, "
            "course, final grade on a 0-10 scale, attendance and enrolment status. Synthetic data, "
            "generated for validating the dataset profiler deployment."
        ),
        "fields_of_science": ["EDUCATIONAL SCIENCES"],
        "keywords": ["education", "university", "enrolment", "courses"],
        "country": "GR",
        "license": "CC BY 4.0",
    }


def request_body(meta: dict) -> dict:
    """A ProfilingRequest, exactly as POST /profiler/trigger_profile expects it."""
    return {
        "profile_specification": {
            "id": ID_PLACEHOLDER,
            "name": meta["name"],
            "description": meta["description"],
            "headline": meta["headline"],
            "fields_of_science": meta["fields_of_science"],
            "languages": ["en"],
            "keywords": meta["keywords"],
            "country": meta["country"],
            "published_url": "",
            "doi": "",
            "date_published": "2026-09-16",
            "cite_as": "",
            "license": meta["license"],
            "uploaded_by": "ADMIN",
            "data_connectors": [
                {"type": "RawDataPath", "dataset_id": ID_PLACEHOLDER},
            ],
        },
        "only_light_profile": False,
    }


def main():
    rng = random.Random(SEED)
    for name, build in (("clinic_appointments", clinic_appointments),
                        ("air_quality_readings", air_quality_readings),
                        ("course_enrolments", course_enrolments)):
        meta = build(rng)
        (ROOT / name / "request.json").write_text(
            json.dumps(request_body(meta), indent=2, ensure_ascii=False) + "\n")
        size = sum(p.stat().st_size for p in (ROOT / name / "data").iterdir())
        print(f"  {name:22} {size / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
