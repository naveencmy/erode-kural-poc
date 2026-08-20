"""Generate 5 Realistic Tamil Nadu Administrative Datasets for Erode Collectorate.

Datasets:
1. Erode Taluk-wise Budget Allocation & Expenditure 2025-26 (.xlsx)
2. Revenue Department Patta Transfer & Survey Cases 2026 (.xlsx)
3. Social Welfare Monthly Pension Schemes Disbursal (.xlsx)
4. PWD Irrigation Tanks & Water Bodies Status (.csv)
5. Police Law & Order Public Grievance Petition Tracking (.csv)
"""

import os
import sys
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pandas as pd
import config
from modules.data_viz.ingestion import ingest_dataset_file


SAMPLE_DIR = config.DATA_DIR / "sample_datasets"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


def create_all_sample_datasets():
    """Create all 5 real-world administrative files."""
    files_created = []

    # Dataset 1: Erode Taluk Budget 2025-26 (Excel)
    # Includes intentional outlier in Sathyamangalam (major hill conservation project)
    budget_data = {
        "வட்டம்": ["ஈரோடு", "பெருந்துறை", "பவானி", "கொடுமுடி", "மொடக்குறிச்சி", "அந்தியூர்", "கோபிசெட்டிபாளையம்", "சத்தியமங்கலம்", "நம்பியூர்", "தாளவாடி"],
        "ஒதுக்கப்பட்ட_பட்ஜெட்": [14500000, 8900000, 11200000, 6400000, 7800000, 9100000, 13400000, 48500000, 5200000, 7100000],
        "செலவிடப்பட்ட_தொகை": [12800000, 7600000, 9800000, 5900000, 6900000, 8100000, 11900000, 45200000, 4800000, 6200000],
        "திட்டங்கள்_எண்ணிக்கை": [42, 28, 35, 18, 22, 29, 39, 85, 16, 21],
        "நிதி_ஆண்டு": ["2025-26"] * 10,
        "செயலாக்க_விழுக்காடு": [88.3, 85.4, 87.5, 92.2, 88.5, 89.0, 88.8, 93.2, 92.3, 87.3],
    }
    df_budget = pd.DataFrame(budget_data)
    budget_path = SAMPLE_DIR / "erode_taluk_budget_2026.xlsx"
    df_budget.to_excel(budget_path, index=False, sheet_name="Budget_Allocation")
    files_created.append(budget_path)

    # Dataset 2: Revenue Patta Transfer & Survey Cases 2026 (Excel)
    patta_data = {
        "வட்டம்": ["ஈரோடு", "பெருந்துறை", "பவானி", "கொடுமுடி", "மொடக்குறிச்சி", "அந்தியூர்", "கோபிசெட்டிபாளையம்", "சத்தியமங்கலம்", "நம்பியூர்", "தாளவாடி"],
        "பெறப்பட்ட_மனுக்கள்": [1420, 850, 1120, 540, 780, 910, 1250, 980, 460, 510],
        "தீர்க்கப்பட்ட_வழக்குகள்": [1280, 760, 990, 490, 710, 820, 1140, 890, 410, 450],
        "நிலுவை_வழக்குகள்": [140, 90, 130, 50, 70, 90, 110, 90, 50, 60],
        "சராசரி_தீர்வு_நாட்கள்": [14, 18, 16, 12, 15, 17, 15, 19, 13, 21],
        "மாதம்": ["ஜூலை 2026"] * 10,
    }
    df_patta = pd.DataFrame(patta_data)
    patta_path = SAMPLE_DIR / "erode_revenue_patta_cases.xlsx"
    df_patta.to_excel(patta_path, index=False, sheet_name="Patta_Cases")
    files_created.append(patta_path)

    # Dataset 3: Social Welfare Pension Schemes (Excel)
    pension_data = {
        "வட்டம்": ["ஈரோடு", "பெருந்துறை", "பவானி", "கொடுமுடி", "மொடக்குறிச்சி", "அந்தியூர்", "கோபிசெட்டிபாளையம்", "சத்தியமங்கலம்", "நம்பியூர்", "தாளவாடி"],
        "முதியோர்_உதவித்தொகை_பயனாளிகள்": [8450, 5120, 6890, 3450, 4780, 5600, 7890, 6120, 2980, 3140],
        "விதவை_உதவித்தொகை_பயனாளிகள்": [3210, 1980, 2650, 1240, 1850, 2150, 3010, 2340, 1120, 1190],
        "மாற்றுத்திறனாளிகள்_உதவித்தொகை": [1540, 920, 1280, 610, 890, 1020, 1450, 1110, 540, 580],
        "மாதாந்திர_பட்டுவாடா_தொகை": [19785000, 12030000, 16230000, 7950000, 11280000, 13155000, 18525000, 14355000, 6960000, 7365000],
        "திட்டம்": ["NSAP_OAP"] * 10,
    }
    df_pension = pd.DataFrame(pension_data)
    pension_path = SAMPLE_DIR / "erode_social_welfare_pension.xlsx"
    df_pension.to_excel(pension_path, index=False, sheet_name="Pension_Beneficiaries")
    files_created.append(pension_path)

    # Dataset 4: PWD Water Bodies & Encroachments (CSV)
    pwd_data = {
        "வட்டம்": ["ஈரோடு", "பெருந்துறை", "பவானி", "கொடுமுடி", "மொடக்குறிச்சி", "அந்தியூர்", "கோபிசெட்டிபாளையம்", "சத்தியமங்கலம்", "நம்பியூர்", "தாளவாடி"],
        "மொத்த_குளங்கள்_ஏரிகள்": [45, 62, 78, 34, 48, 89, 71, 94, 38, 52],
        "தூர்வாரப்பட்ட_குளங்கள்": [38, 54, 69, 31, 42, 79, 64, 82, 34, 44],
        "ஆக்கிரமிப்பு_எண்ணிக்கை": [18, 12, 15, 6, 8, 22, 14, 19, 5, 9],
        "மீட்கப்பட்ட_பரப்பளவு_ஏக்கர்": [12.4, 8.6, 11.2, 4.5, 6.1, 15.8, 9.7, 14.1, 3.8, 6.5],
        "ஆண்டு": [2026] * 10,
    }
    df_pwd = pd.DataFrame(pwd_data)
    pwd_path = SAMPLE_DIR / "erode_pwd_water_bodies.csv"
    df_pwd.to_csv(pwd_path, index=False, encoding="utf-8")
    files_created.append(pwd_path)

    # Dataset 5: Police Law & Order Public Grievance Petitions (CSV)
    police_data = {
        "வட்டம்": ["ஈரோடு", "பெருந்துறை", "பவானி", "கொடுமுடி", "மொடக்குறிச்சி", "அந்தியூர்", "கோபிசெட்டிபாளையம்", "சத்தியமங்கலம்", "நம்பியூர்", "தாளவாடி"],
        "பெறப்பட்ட_புகார்கள்": [320, 180, 240, 95, 140, 190, 260, 210, 85, 110],
        "விசாரிக்கப்பட்ட_மனுக்கள்": [295, 168, 222, 89, 131, 176, 242, 195, 80, 102],
        "நிலுவையில்_உள்ளவை": [25, 12, 18, 6, 9, 14, 18, 15, 5, 8],
        "சிவில்_தகராறுகள்": [140, 85, 110, 45, 65, 90, 115, 95, 38, 50],
        "குடும்ப_வழக்குகள்": [95, 52, 68, 28, 42, 54, 78, 62, 24, 32],
    }
    df_police = pd.DataFrame(police_data)
    police_path = SAMPLE_DIR / "erode_police_grievance_tracking.csv"
    df_police.to_csv(police_path, index=False, encoding="utf-8")
    files_created.append(police_path)

    return files_created


def seed_and_ingest_all(officer_id: str = "DRO_ERODE_01"):
    """Create sample files and ingest into SQLite database."""
    from pipeline.database import init_db
    init_db()
    files = create_all_sample_datasets()
    results = []
    for f in files:
        res = ingest_dataset_file(f, officer_id=officer_id)
        results.append(res)
    return results


if __name__ == "__main__":
    seeded = seed_and_ingest_all()
    print(f"Successfully created and ingested {len(seeded)} datasets into Module 2.")

