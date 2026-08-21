"""Official Content Generator — Template + LLM Hybrid Engine.

Generates formal Tamil Nadu government documents using Jinja2 templates.
Optionally enhances content via local Ollama LLM (qwen2.5:7b) with
deterministic fallback when LLM is unavailable.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import jinja2
import requests

import config
from modules.official_content.templates import TEMPLATE_REGISTRY

logger = logging.getLogger("OfficialContentGenerator")

# Jinja2 environment for rendering templates
_jinja_env = jinja2.Environment(undefined=jinja2.Undefined)


# ---------------------------------------------------------------------------
# LLM Prompts for each template type (Tamil-first bilingual)
# ---------------------------------------------------------------------------
LLM_PROMPTS = {
    "press_release": (
        "You are the official Public Relations Officer (செய்தி மக்கள் தொடர்பு அலுவலர்) for the Erode District Collectorate (ஈரோடு மாவட்ட ஆட்சியரகம்), Tamil Nadu.\n"
        "Draft an authentic, publication-ready Tamil Government Press Release (செய்தி வெளியீடு) strictly matching the real Erode District DIPR official format and administrative tone.\n\n"
        "### STRUCTURE & RULES:\n"
        "1. LEAD PARAGRAPH (தொடக்கப் பத்தி):\n"
        "   - Start with the exact context: 'ஈரோடு மாவட்டம், [இடம்/வட்டம்]யில் [பொருள்] குறித்து மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப., அவர்கள் இன்று ({date}) நேரில் பார்வையிட்டு ஆய்வு மேற்கொண்டார் / உத்தரவிட்டார் / வழங்கினார்.' (அல்லது 'மாண்புமிகு தமிழ்நாடு முதலமைச்சர் அவர்களின் அறிவிப்பிற்கிணங்க / உத்தரவின்படி, ஈரோடு மாவட்டத்தில்...').\n\n"
        "2. DETAILED BODY PARAGRAPHS (செய்தி விவரங்கள்):\n"
        "   - Write 2 to 4 rich, flowing paragraphs in formal government Tamil (அரசு தமிழ் நடை).\n"
        "   - Use formal transitions: 'தொடர்ந்து, ...', 'மேலும், ...', 'அதன்படி, ...'.\n"
        "   - Thoroughly integrate all key points, statistics, numbers, rupee values (ரூ. ... இலட்சம் / கோடி), beneficiary counts, village/taluk names provided in the user's input.\n"
        "   - Naturally reference Erode district taluks and locations (ஈரோடு, பெருந்துறை, பவானி, கோபிசெட்டிபாளையம், சத்தியமங்கலம், மொடக்குறிச்சி, அந்தியூர், கொடுமுடி, நம்பியூர், தாளவாடி) when relevant.\n"
        "   - Detail administrative directives, quality inspection points, welfare delivery, or grievance resolution measures.\n\n"
        "3. PARTICIPATING OFFICIALS (உடனிருந்த அலுவலர்கள்):\n"
        "   - End with a dedicated paragraph starting with 'இந்நிகழ்வின் போது,' or 'இந்த ஆய்வின்போது,' or 'இந்நிகழ்ச்சியில்,' mentioning relevant district officers (e.g. மாவட்ட வருவாய் அலுவலர் திரு.சு.சாந்தகுமார், திட்ட இயக்குநர் (ஊரக வளர்ச்சி முகமை), வருவாய் கோட்டாட்சியர், வட்டாட்சியர், வட்டார வளர்ச்சி அலுவலர்கள், துறை சார்ந்த அலுவலர்கள் உடனிருந்தனர் / கலந்து கொண்டனர்).\n\n"
        "4. STRICT FORMATTING:\n"
        "   - Pure formal government Tamil.\n"
        "   - Output ONLY the body paragraphs. Do NOT include 'செ.வெ.எண்' header or 'வெளியீடு' footer (the master template handles them).\n"
        "   - Do NOT invent false data; enrich the provided facts into standard government press release wording.\n\n"
        "Input Data:\n"
        "பொருள் (Subject): {subject}\n"
        "முக்கிய குறிப்புகள் (Key Points): {details}\n"
        "நாள் (Date): {date}\n\n"
        "Generate the official Erode District Press Release body in Tamil:"
    ),
    "circular": (
        "You are the senior administrative drafting officer for the Erode District Collectorate (ஈரோடு மாவட்ட ஆட்சியர் அலுவலகம்), Tamil Nadu.\n"
        "Draft an authentic, formal, and authoritative Tamil Nadu Government Official Circular (அதிகாரப்பூர்வ அலுவலக சுற்றறிக்கை) issued under the orders of the District Collector (மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப.).\n\n"
        "### STRUCTURE & DIRECTIVES:\n"
        "1. ADMINISTRATIVE PURPOSE & CONTEXT (அலுவலக சுற்றறிக்கை நோக்கம்):\n"
        "   - Open with authoritative administrative language: 'ஈரோடு மாவட்டத்தில் {subject} தொடர்பாக, அனைத்து துறை அலுவலர்கள், வட்டாட்சியர்கள், வட்டார வளர்ச்சி அலுவலர்கள் மற்றும் களப்பணியாளர்கள் பின்பற்றி செயல்பட வேண்டிய முக்கிய வழிகாட்டு நெறிமுறைகள் இச்சுற்றறிக்கை மூலம் வெளியிடப்படுகிறது.'\n\n"
        "2. DETAILED ACTION POINTS & DIRECTIVES (துறை வாரியான நெறிமுறைகள் & உத்தரவுகள்):\n"
        "   - Write 2 to 4 structured, cohesive paragraphs in formal directive government Tamil (ஆணை நடை தமிழ்).\n"
        "   - Use formal administrative terms: 'உத்தரவிடப்படுகிறது', 'அறிவுறுத்தப்படுகிறது', 'கண்டிப்புடன் கடைபிடிக்கப்பட வேண்டும்', 'நடவடிக்கை மேற்கொள்ளப்பட வேண்டும்'.\n"
        "   - Thoroughly incorporate all points, deadlines, review mechanisms, inspection squads, guidelines, and figures provided in the user's input.\n"
        "   - Explicitly mention the concerned administrative divisions/taluks of Erode (ஈரோடு, பெருந்துறை, பவானி, கோபிசெட்டிபாளையம், சத்தியமங்கலம், மொடக்குறிச்சி, அந்தியூர், கொடுமுடி, நம்பியூர், தாளவாடி) where applicable.\n\n"
        "3. TIMELINE & COMPLIANCE WARNING (காலக்கெடு மற்றும் ஒழுங்கு நடவடிக்கை எச்சரிக்கை):\n"
        "   - Detail the reporting timelines (e.g. வாராந்திர முன்னேற்ற அறிக்கை / உடனடி கள ஆய்வு அறிக்கை).\n"
        "   - State clearly that any delay, negligence, or non-compliance will lead to disciplinary action under the Tamil Nadu Civil Services (Discipline & Appeal) Rules as ordered by District Collector Thiru S. Kandasamy IAS.\n\n"
        "4. STRICT FORMATTING:\n"
        "   - Pure formal government administrative Tamil.\n"
        "   - Output ONLY the body paragraphs (do NOT include header lines, reference numbers, or signature blocks as the master template includes them).\n"
        "   - Do NOT invent false figures; convert the provided details into authentic administrative circular prose.\n\n"
        "Input Data:\n"
        "பொருள் (Subject): {subject}\n"
        "முக்கிய வழிகாட்டுதல்கள் (Key Guidelines/Details): {details}\n"
        "நாள் (Date): {date}\n\n"
        "Generate the official Erode District Circular body in Tamil:"
    ),
    "memo": (
        "You are the senior administrative drafting officer for the Erode District Collectorate (ஈரோடு மாவட்ட ஆட்சியர் அலுவலகம்), Tamil Nadu.\n"
        "Draft an authentic, formal, and structured Tamil Nadu Government Office Memorandum / Official Order (அலுவலகக் குறிப்பாணை / ஆணை) issued under the orders of the District Collector (மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப.) or District Revenue Officer (மாவட்ட வருவாய் அலுவலர் திரு.சு.சாந்தகுமார்).\n\n"
        "### STRUCTURE & DIRECTIVES:\n"
        "1. ORDER / MEMO CONTEXT (தொடக்கப் பத்தி / ஆணை விவரம்):\n"
        "   - Open with clear government context: 'ஈரோடு மாவட்டத்தில் {subject} தொடர்பாக, புதிய நடைமுறைகள் / வழிகாட்டு நெறிமுறைகள் / உதவித்தொகை ஆணைகள் வெளியிடப்பட்டு மாவட்ட ஆட்சித்தலைவர் / மாவட்ட வருவாய் அலுவலர் அவர்கள் ஆணை பிறப்பித்துள்ளார் / வழங்கியுள்ளார்.'\n\n"
        "2. DETAILED TERMS, CLAUSES & STATISTICS (விதிமுறைகள் / நெறிமுறைகள் / தகுதிகள்):\n"
        "   - If the user provides multiple conditions, rules, guidelines, eligibility criteria, or financial breakdown (ரூ. ... இலட்சம் / கோடி, தவணை விவரங்கள், இணையதள முகவரி www...gov.in, கல்வி உதவித்தொகை, மானியம்), format them into clear numbered points (1., 2., 3...) or bold subheadings (எ.கா: 'அறிவிக்கை செய்யப்பட்டுள்ள விவரங்கள்', 'விண்ணப்பிக்கும் முறை', 'கட்டண விவரம்', 'கடைசி நாள்').\n"
        "   - Naturally incorporate all statistics, beneficiaries count, taluks/schools, amounts, and dates given in the input.\n\n"
        "3. DIRECTIVE CLOSING / COMPLIANCE (முடிவுரை & வழிகாட்டுதல்):\n"
        "   - End with clear administrative instructions: 'எனவே, நிர்ணயிக்கப்பட்டுள்ள கால அளவையும் தற்போது தெரிவிக்கப்பட்டுள்ள வழிமுறைகளையும் தவறாமல் பின்பற்றி பயனடையுமாறு / செயல்படுமாறு ஈரோடு மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப. அவர்கள் தெரிவித்துள்ளார்கள்.'\n"
        "   - If officials / bank managers / educational officers are participating, include them appropriately.\n\n"
        "4. STRICT FORMATTING:\n"
        "   - Pure formal government administrative Tamil.\n"
        "   - Output ONLY the body paragraphs (do NOT output header lines, reference numbers, or footer as the master template includes them).\n"
        "   - Do NOT invent false figures; enrich the provided details into authentic administrative order/memo prose.\n\n"
        "Input Data:\n"
        "பொருள் (Subject): {subject}\n"
        "விவரங்கள் / குறிப்புகள் (Details/Points): {details}\n"
        "நாள் (Date): {date}\n\n"
        "Generate the official Erode District Office Memorandum body in Tamil:"
    ),
    "meeting_minutes": (
        "You are the senior administrative recording officer for the Erode District Collectorate (ஈரோடு மாவட்ட ஆட்சியர் அலுவலகம்), Tamil Nadu.\n"
        "Draft the authentic, formal, and structured proceedings of an official government review meeting (கூட்ட நடவடிக்கைகள்) chaired by the District Collector (மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப.).\n\n"
        "### STRUCTURE & DIRECTIVES:\n"
        "1. OPENING PROCEEDINGS (தொடக்கப் பத்தி):\n"
        "   - Formal opening: '{subject} கூட்டம் {date} அன்று காலை 10.30 மணிக்கு மாவட்ட ஆட்சித்தலைவர் அவர்களின் தலைமையில் மாவட்ட ஆட்சியரக கூட்டரங்கில் நடைபெற்றது. இக்கூட்டத்தில் மாவட்ட வருவாய் அலுவலர், துறை சார்ந்த அலுவலர்கள், சங்கப் பிரதிநிதிகள் மற்றும் பொதுமக்கள் பலர் கலந்து கொண்டனர்.'\n\n"
        "2. REPRESENTATIONS & DEMANDS (சங்கங்களின் கோரிக்கைகள் / விவாதப் பொருட்கள்):\n"
        "   - Use bold subheadings for each association / speaker / topic (எ.கா: 'விவசாய சங்கங்களின் கோரிக்கைகள்:', 'கீழ்பவானி பாசன விவசாயிகள் சங்கம்:', 'சங்கப் பிரதிநிதிகள் கோரிக்கை:').\n"
        "   - Write out their points clearly in formal administrative Tamil based on user input.\n"
        "   - Add department action tags where applicable: '(நடவடிக்கை: நீர்வள ஆதாரத்துறை, வேளாண்மைத்துறை, மின்சார வாரியம், மாவட்ட வருவாய் அலுவலர்)'.\n\n"
        "3. DEPARTMENTAL RESPONSES & ACTIONS (அலுவலர்களின் பதில்கள் & துறைவாரியான முடிவுகள்):\n"
        "   - Department subheadings (எ.கா: 'நீர்வள ஆதாரத்துறை:', 'வேளாண்மைத்துறை:', 'தமிழ்நாடு மின்சார வாரியம்:', 'உணவு பாதுகாப்புத்துறை:', 'மாவட்ட வருவாய் அலுவலர்:').\n"
        "   - Detail the official status, sanction decisions, and timeline for action.\n\n"
        "4. DISTRICT COLLECTOR'S CONCLUDING DIRECTIVES (மாவட்ட ஆட்சித்தலைவர் அவர்களின் உத்தரவுகள்):\n"
        "   - Concluding instructions under 'மாவட்ட ஆட்சித்தலைவர்:' emphasizing immediate time-bound redressal of grievances, field inspections, and transparent execution.\n\n"
        "5. STRICT FORMATTING:\n"
        "   - Pure formal government administrative Tamil.\n"
        "   - Output ONLY the body proceedings content. Do NOT include top header line or bottom signature blocks (the master template handles them).\n\n"
        "Input Data:\n"
        "பொருள் (Subject): {subject}\n"
        "கூட்ட விவாதங்கள் & முடிவுகள் (Proceedings / Points): {details}\n"
        "நாள் (Date): {date}\n\n"
        "Generate the official Erode District Meeting Minutes body in Tamil:"
    ),
}


def _format_circular_fallback(subject: str, details: str, date_str: str) -> str:
    """Build an authentic Erode District Collectorate circular fallback without LLM."""
    clean_subject = subject.strip()
    points = [p.strip() for p in details.split("\n") if p.strip()]

    p1 = (
        f"ஈரோடு மாவட்டத்தில் {clean_subject} தொடர்பாக, அனைத்து துறைத் தலைவர்கள், வட்டாட்சியர்கள், "
        f"வட்டார வளர்ச்சி அலுவலர்கள், நகராட்சி மற்றும் பேரூராட்சி ஆணையர்கள் மற்றும் அனைத்து நிலை அலுவலர்களும் "
        f"முறையாகப் பின்பற்றி துரிதமாக செயல்படுத்த வேண்டிய முக்கிய வழிகாட்டு நெறிமுறைகள் இதன்மூலம் தெரிவிக்கப்படுகிறது."
    )

    body_paras = []
    if points:
        first_group = points[:len(points)//2 + 1] if len(points) > 1 else points
        second_group = points[len(points)//2 + 1:] if len(points) > 1 else []

        p_directives = " ".join(first_group)
        body_paras.append(
            f"1. நிர்வாக வழிகாட்டுதல்கள்: {p_directives}. மேற்படி பணிகளை எவ்வித சுணக்கமும் இன்றி, "
            f"அரசு நிர்ணயித்துள்ள உரிய விதிமுறைகளுக்கு உட்பட்டு உடனடியாக செயல்படுத்திட வேண்டும்."
        )

        if second_group:
            p_action = " ".join(second_group)
            body_paras.append(
                f"2. கள ஆய்வு மற்றும் கண்காணிப்பு: {p_action}. துறை சார்ந்த அலுவலர்கள் தங்கள் எல்லைக்குட்பட்ட "
                f"பகுதிகளில் நேரடி களஆய்வு மேற்கொண்டு, பணிகளின் முன்னேற்றம் குறித்த அறிக்கையினை மாவட்ட ஆட்சியர் "
                f"அலுவலகத்திற்கு குறிப்பிட்ட காலத்திற்குள் சமர்ப்பிக்க வேண்டும்."
            )
    else:
        body_paras.append(
            f"அரசு நலத்திட்டங்கள் மற்றும் வளர்ச்சிப் பணிகளை எவ்வித தாமதமும் இன்றி குறிப்பிட்ட காலத்திற்குள் "
            f"நிறைவேற்றிட அனைத்து அலுவலர்களும் ஒருங்கிணைந்து முழு ஈடுபாட்டுடன் செயல்பட வேண்டும்."
        )

    p_warning = (
        "இச்சுற்றறிக்கையில் குறிப்பிடப்பட்டுள்ள நெறிமுறைகளை அனைத்து அலுவலர்களும் கண்டிப்புடன் பின்பற்ற வேண்டும். "
        "பணிகளில் சுணக்கம் அல்லது அலட்சியம் காட்டும் அலுவலர்கள் மீது தமிழ்நாடு அரசு பணியாளர் ஒழுங்கு விதிகளின் கீழ் "
        "கடுமையான ஒழுங்கு நடவடிக்கை மேற்கொள்ளப்படும் என மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப., அவர்கள் "
        "உத்தரவிட்டுள்ளார்."
    )

    all_paras = [p1] + body_paras + [p_warning]
    return "\n\n".join(all_paras)


def _format_memo_fallback(subject: str, details: str, date_str: str) -> str:
    """Build an authentic Erode District Office Memorandum / Order fallback without LLM."""
    clean_subject = subject.strip()
    points = [p.strip() for p in details.split("\n") if p.strip()]

    p_intro = (
        f"ஈரோடு மாவட்டத்தில் {clean_subject} தொடர்பாக, புதிய நடைமுறைகள் மற்றும் வழிகாட்டு நெறிமுறைகள் "
        f"செயல்படுத்தப்பட்டு வருவது குறித்து மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப., அவர்கள் "
        f"தெரிவித்துள்ளார்கள்."
    )

    body_sections = []
    if points:
        numbered_points = []
        for idx, pt in enumerate(points, 1):
            if pt and (pt[0].isdigit() or pt.startswith("-") or pt.startswith("*")):
                numbered_points.append(pt)
            else:
                numbered_points.append(f"{idx}. {pt}")
        body_sections.append("\n".join(numbered_points))
    else:
        body_sections.append(
            "1. தொடர்புடைய அனைத்து அலுவலர்களும் அரசு நிர்ணயித்துள்ள உரிய விதிமுறைகளுக்கு உட்பட்டு துரிதமாக செயல்பட வேண்டும்.\n"
            "2. பொதுமக்கள் மற்றும் தகுதியான பயனாளிகள் உரிய வழிகாட்டுதல்களை தவறாமல் பின்பற்றி பயனடையுமாறு அறிவுறுத்தப்படுகிறது."
        )

    p_close = (
        "எனவே, நிர்ணயிக்கப்பட்ட கால அளவையும் தற்போது தெரிவிக்கப்பட்டுள்ள வழிமுறைகளையும் தவறாமல் பின்பற்றி "
        "பயனடையுமாறு / உரிய நடவடிக்கை எடுக்குமாறு ஈரோடு மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப., அவர்கள் "
        "தெரிவித்துள்ளார்கள்."
    )

    all_paras = [p_intro] + body_sections + [p_close]
    return "\n\n".join(all_paras)


def _format_meeting_minutes_fallback(subject: str, details: str, date_str: str) -> str:
    """Build an authentic Erode District Meeting Minutes fallback without LLM."""
    clean_subject = subject.strip()
    points = [p.strip() for p in details.split("\n") if p.strip()]

    p_intro = (
        f"{clean_subject} கூட்டம் {date_str} அன்று காலை 10.30 மணிக்கு மாவட்ட ஆட்சித்தலைவர் "
        f"அவர்களின் தலைமையில் மாவட்ட ஆட்சியரக கூட்டரங்கில் நடைபெற்றது. இக்கூட்டத்தில் மாவட்ட "
        f"வருவாய் அலுவலர், பல்வேறு துறை அலுவலர்கள், விவசாய / தொழில் சங்கப் பிரதிநிதிகள் மற்றும் பொதுமக்கள் "
        f"திரளாக கலந்து கொண்டனர்."
    )

    body_sections = []
    if points:
        first_group = points[:len(points)//2 + 1] if len(points) > 1 else points
        second_group = points[len(points)//2 + 1:] if len(points) > 1 else []

        body_sections.append("சங்கப் பிரதிநிதிகள் மற்றும் பொதுமக்களின் கோரிக்கைகள்:")
        for idx, pt in enumerate(first_group, 1):
            body_sections.append(f"{idx}. {pt}")
        body_sections.append("(நடவடிக்கை: வருவாய்த்துறை, நீர்வள ஆதாரத்துறை, வேளாண்மைத்துறை, ஊரக வளர்ச்சி முகமை)")

        if second_group:
            body_sections.append("\nஅலுவலர்களின் பதில்கள் மற்றும் எடுக்கப்பட்ட நடவடிக்கைகள்:")
            for pt in second_group:
                body_sections.append(f"• துறை சார்ந்த நடவடிக்கை: {pt}. பணிகளை விரைந்து முடித்திட உரிய ஆணை பிறப்பிக்கப்பட்டது.")
    else:
        body_sections.append(
            "கூட்டத்தில் பெறப்பட்ட அனைத்து மனுக்கள் மற்றும் கோரிக்கைகள் குறித்து விரிவாக விவாதிக்கப்பட்டது. "
            "துறை சார்ந்த அலுவலர்கள் தங்கள் எல்லைக்குட்பட்ட பகுதிகளில் நேரடி ஆய்வு மேற்கொண்டு மனுக்களுக்கு "
            "உடனுக்குடன் தீர்வு காண உத்தரவிடப்பட்டது."
        )

    p_collector = (
        "மாவட்ட ஆட்சித்தலைவர்:\n"
        "இக்கூட்டத்தில் பெறப்படும் அனைத்து மனுக்கள் மற்றும் கோரிக்கைகளுக்கு துறை அலுவலர்கள் எவ்வித தாமதமும் இன்றி "
        "உடனுக்குடன் உரிய நடவடிக்கை எடுக்க வேண்டும். மனுக்களின் மீது எடுக்கப்பட்ட விவரங்களை மனுதாரருக்கு "
        "தெரிவிப்பதோடு, அடுத்த ஆய்வுக் கூட்டத்திற்குள் உரிய முன்னேற்ற அறிக்கையினை சமர்ப்பிக்க வேண்டும் என்று "
        "மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப., அவர்கள் அறிவுறுத்தினார்."
    )

    all_content = [p_intro, "\n".join(body_sections), p_collector]
    return "\n\n".join(all_content)


def _format_press_release_fallback(subject: str, details: str, date_str: str) -> str:
    """Build an authentic Erode District DIPR press release fallback without LLM."""
    clean_subject = subject.strip()
    points = [p.strip() for p in details.split("\n") if p.strip()]

    # Paragraph 1: Lead paragraph
    lead_para = (
        f"ஈரோடு மாவட்டம், மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப., அவர்கள் தலைமையில் "
        f"{clean_subject} குறித்த முக்கிய ஆய்வு மற்றும் பணிகள் இன்று ({date_str}) "
        f"மாவட்ட ஆட்சித்தலைவர் அலுவலகம் மற்றும் களப்பகுதிகளில் நேரில் பார்வையிட்டு ஆய்வு மேற்கொள்ளப்பட்டது."
    )

    # Paragraph 2 & 3: Detailed body points
    body_paras = []
    if points:
        first_group = points[:len(points)//2 + 1] if len(points) > 1 else points
        second_group = points[len(points)//2 + 1:] if len(points) > 1 else []

        p1_text = " ".join(first_group)
        body_paras.append(
            f"ஈரோடு மாவட்டத்தில் பொதுமக்களின் நலன் கருதி மேற்கொள்ளப்பட்டு வரும் வளர்ச்சித் திட்டப் பணிகளில், "
            f"{p1_text}. இப்பணிகளை விரைவாகவும், அரசு நிர்ணயித்த தரக்கட்டுப்பாடுகளுக்கு உட்பட்டும் முடித்திட "
            f"மாவட்ட ஆட்சித்தலைவர் அவர்கள் துறை அலுவலர்களுக்கு உத்தரவிட்டுள்ளார்."
        )

        if second_group:
            p2_text = " ".join(second_group)
            body_paras.append(
                f"தொடர்ந்து, {p2_text}. திட்டப் பணிகளின் முன்னேற்றம் மற்றும் பயனாளிகளுக்கு சென்றடையும் "
                f"சேவைகள் குறித்து அலுவலர்களிடம் விரிவாக கேட்டறிந்து, பணிகளை துரிதப்படுத்த அறிவுறுத்தப்பட்டது."
            )
    else:
        body_paras.append(
            f"ஈரோடு மாவட்டத்தில் செயல்படுத்தப்பட்டு வரும் அரசு நலத்திட்டங்கள் மற்றும் வளர்ச்சிப் பணிகள் "
            f"செம்மையாக நடைபெறுவதை உறுதிசெய்யும் வகையில், துறை அலுவலர்கள் ஒருங்கிணைந்து செயல்பட வேண்டும் "
            f"என்று மாவட்ட ஆட்சித்தலைவர் அவர்கள் அறிவுறுத்தினார்."
        )

    # Paragraph 4: Accompanying Officials
    officials_para = (
        "இந்நிகழ்வின் போது, மாவட்ட வருவாய் அலுவலர் திரு.சு.சாந்தகுமார், திட்ட இயக்குநர் (ஊரக வளர்ச்சி முகமை), "
        "வருவாய் கோட்டாட்சியர், வட்டாட்சியர், வட்டார வளர்ச்சி அலுவலர்கள் மற்றும் தொடர்புடைய துறை சார்ந்த "
        "அலுவலர்கள் பலர் கலந்து கொண்டனர்."
    )

    all_paras = [lead_para] + body_paras + [officials_para]
    return "\n\n".join(all_paras)


# ---------------------------------------------------------------------------
# Deterministic fallback content (no LLM needed)
# ---------------------------------------------------------------------------
FALLBACK_BODIES = {
    "press_release": "{details}",  # Dynamic generator used in generate()
    "circular": (
        "அனைத்து துறைத் தலைவர்கள் மற்றும் வட்டாட்சியர்களின் கவனத்திற்கு:\n\n"
        "பொருள்: {subject}\n\n"
        "{details}\n\n"
        "மேற்கண்ட விவரங்களை கவனத்தில் கொண்டு உடனடியாக தேவையான நடவடிக்கை "
        "எடுக்குமாறு அறிவுறுத்தப்படுகிறது.\n\n"
        "இந்த சுற்றறிக்கை பெறப்பட்ட உடனேயே ஒப்புகை அனுப்பவும்."
    ),
    "memo": (
        "குறிப்பாணை விவரம்:\n\n"
        "பொருள்: {subject}\n\n"
        "{details}\n\n"
        "மேற்கண்ட விவரங்கள் உரிய அலுவலர்களின் கவனத்திற்கும் "
        "தேவையான நடவடிக்கைக்கும் சமர்ப்பிக்கப்படுகிறது.\n\n"
        "உரிய நடவடிக்கை எடுத்து அறிக்கை சமர்ப்பிக்குமாறு கேட்டுக்கொள்ளப்படுகிறது."
    ),
    "meeting_minutes": (
        "கூட்டப் பொருள்: {subject}\n\n"
        "கூட்ட நடவடிக்கைகள்:\n\n"
        "{details}\n\n"
        "முடிவுகள்:\n"
        "1. மேற்கண்ட விவரங்கள் குறித்து உரிய நடவடிக்கை எடுக்க முடிவு செய்யப்பட்டது.\n"
        "2. அடுத்த கூட்ட நாள் தனியாக தெரிவிக்கப்படும்.\n"
        "3. சம்பந்தப்பட்ட அனைத்து அலுவலர்களும் நடவடிக்கை அறிக்கையை "
        "15 நாட்களுக்குள் சமர்ப்பிக்க வேண்டும்."
    ),
}


def _generate_ref_number(prefix: str) -> str:
    """Generate an authentic reference / press release sequence number."""
    now = datetime.now()
    if prefix == "PR":
        # DIPR standard Press Release sequence number (e.g. 14, 39, 59)
        seq = (int(now.strftime("%H%M%S")) % 90) + 10
        return str(seq)
    seq = now.strftime("%H%M%S")
    return f"ERD/{prefix}/{now.year}/{seq}"


def _try_ollama(prompt: str) -> Optional[str]:
    """Attempt to generate content via local Ollama LLM. Returns None on failure."""
    try:
        response = requests.post(
            f"{config.OLLAMA_API_BASE}/api/generate",
            json={
                "model": config.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "num_predict": 1024,
                },
            },
            timeout=config.OLLAMA_TIMEOUT_SEC,
        )
        if response.status_code == 200:
            data = response.json()
            generated = data.get("response", "").strip()
            if generated and len(generated) > 20:
                logger.info("Ollama LLM generated content successfully.")
                return generated
    except requests.exceptions.ConnectionError:
        logger.info("Ollama not available — using deterministic fallback.")
    except requests.exceptions.Timeout:
        logger.warning("Ollama timed out — using deterministic fallback.")
    except Exception as e:
        logger.warning(f"Ollama error: {e} — using deterministic fallback.")
    return None


class OfficialContentGenerator:
    """Generates official Tamil Nadu government documents."""

    def generate(
        self,
        template_type: str,
        subject: str,
        details: str,
        officer_id: str = "OFC001",
    ) -> Dict[str, Any]:
        """Generate an official document.

        Args:
            template_type: One of 'press_release', 'circular', 'memo', 'meeting_minutes'
            subject: Document subject line
            details: Key points / context for the document
            officer_id: Officer ID creating the document

        Returns:
            Dict with content_id, generated_text, ref_number, template_type, metadata
        """
        if template_type not in TEMPLATE_REGISTRY:
            raise ValueError(
                f"Unknown template_type '{template_type}'. "
                f"Valid: {list(TEMPLATE_REGISTRY.keys())}"
            )

        registry_entry = TEMPLATE_REGISTRY[template_type]
        ref_number = _generate_ref_number(registry_entry["ref_prefix"])
        now = datetime.now()
        date_str = now.strftime("%d.%m.%Y")
        content_id = f"cnt_{uuid.uuid4().hex[:12]}"

        # --- Generate body content ---
        content_body = None
        source = "fallback"

        # Try LLM first
        llm_prompt = LLM_PROMPTS.get(template_type, "")
        if llm_prompt:
            formatted_prompt = llm_prompt.format(subject=subject, details=details, date=date_str)
            content_body = _try_ollama(formatted_prompt)
            if content_body:
                source = "ollama"

        # Fallback to deterministic template
        if not content_body:
            if template_type == "press_release":
                content_body = _format_press_release_fallback(subject=subject, details=details, date_str=date_str)
            elif template_type == "circular":
                content_body = _format_circular_fallback(subject=subject, details=details, date_str=date_str)
            elif template_type == "memo":
                content_body = _format_memo_fallback(subject=subject, details=details, date_str=date_str)
            elif template_type == "meeting_minutes":
                content_body = _format_meeting_minutes_fallback(subject=subject, details=details, date_str=date_str)
            else:
                fallback = FALLBACK_BODIES.get(template_type, "{subject}\n\n{details}")
                content_body = fallback.format(subject=subject, details=details or "[விவரம் வழங்கப்படவில்லை]")

        # --- Build participants/resolutions for meeting minutes ---
        participants_section = "- தெரிவிக்கப்படும் (To be updated)"
        resolutions_section = "- கூட்ட முடிவுகளின்படி நடவடிக்கை எடுக்கப்படும்."

        if template_type == "meeting_minutes" and details:
            # Extract any numbered items as resolutions
            lines = [l.strip() for l in details.split("\n") if l.strip()]
            numbered = [l for l in lines if l and l[0].isdigit()]
            if numbered:
                resolutions_section = "\n".join(f"  {r}" for r in numbered)

        # --- Render final document ---
        template = _jinja_env.from_string(registry_entry["template"])
        generated_text = template.render(
            ref_number=ref_number,
            date=date_str,
            officer_id=officer_id,
            subject=subject,
            content_body=content_body,
            participants_section=participants_section,
            resolutions_section=resolutions_section,
        )

        return {
            "content_id": content_id,
            "template_type": template_type,
            "template_title_ta": registry_entry["title_ta"],
            "template_title_en": registry_entry["title_en"],
            "ref_number": ref_number,
            "subject": subject,
            "details": details,
            "generated_text": generated_text,
            "content_body": content_body,
            "officer_id": officer_id,
            "created_at": now.isoformat(),
            "date_display": date_str,
            "source": source,
            "status": "generated",
        }
