"""Jinja2 Templates for Tamil Nadu Government Official Documents (Tamil and English).

Each template follows the formal structure mandated by the
Tamil Nadu Government Secretariat and District Collectorate for official communications.
"""

# ===========================================================================
# TAMIL TEMPLATES (தமிழ் அரசு ஆவண மாதிரிகள்)
# ===========================================================================

# 1. Press Release — செய்தி குறிப்பு / செய்தி வெளியீடு (DIPR Erode District Standard)
PRESS_RELEASE_TEMPLATE_TA = """செ.வெ.எண் - {{ ref_number }}                                            நாள் - {{ date }}

          ஈரோடு மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப.,
                         அவர்களின் செய்திக்குறிப்பு-
                                    ----

{{ content_body }}

--------------------------------------------------------------------------------
{{ footer_text }}
"""

# 2. Official Circular — அலுவலக சுற்றறிக்கை (Erode District Standard)
CIRCULAR_TEMPLATE_TA = """சுற்றறிக்கை எண் - {{ ref_number }}                                      நாள் - {{ date }}

          ஈரோடு மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப.,
                         அவர்களின் சுற்றறிக்கை-
                                    ----

{{ content_body }}

--------------------------------------------------------------------------------
{{ footer_text }}
"""

# 3. Office Memorandum — அலுவலக குறிப்பாணை (Erode District Standard)
MEMO_TEMPLATE_TA = """குறிப்பாணை எண் - {{ ref_number }}                                      நாள் - {{ date }}

          ஈரோடு மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப.,
                       அவர்களின் அலுவலகக் குறிப்பாணை-
                                    ----

{{ content_body }}

--------------------------------------------------------------------------------
{{ footer_text }}
"""

# 4. Meeting Minutes — கூட்ட நடவடிக்கை பதிவேடு (Erode District Standard)
MEETING_MINUTES_TEMPLATE_TA = """ஈரோடு மாவட்ட ஆட்சித்தலைவர் அவர்கள் தலைமையில் {{ date }} அன்று
     நடைபெற்ற {{ subject }} கூட்ட நடவடிக்கைகள்
                   முன்னிலை: திரு.ச.கந்தசாமி, இ.ஆ.ப.,

எண்: வே/{{ ref_number }}/2026                                    நாள்: {{ date }}
--------------------------------------------------------------------------------
பொருள்: {{ subject }} – கூட்ட நடவடிக்கைகள் – ஒப்புதல் அளித்தல் – தொடர்பாக.
பார்வை: அரசாணை எண்: 78 வேளாண்மை (வே.உ.6) துறை, நாள்: 17.02.2016.
                                    <><><>

{{ content_body }}

--------------------------------------------------------------------------------
                                                ஓம்/-ச.கந்தசாமி
                                                மாவட்ட ஆட்சித்தலைவர்,
                                                ஈரோடு.

/உத்தரவுப்படி/

                                  நேர்முக உதவியாளர்,
                                  மாவட்ட ஆட்சியர் அலுவலகம்,
                                  ஈரோடு.
"""

# ===========================================================================
# ENGLISH TEMPLATES (Government of Tamil Nadu Official Formats)
# ===========================================================================

# 1. Press Release (English)
PRESS_RELEASE_TEMPLATE_EN = """PRESS RELEASE NO: {{ ref_number }}                                       DATE: {{ date }}

       PRESS RELEASE ISSUED BY THE DISTRICT COLLECTOR & DISTRICT MAGISTRATE
                      THIRU S. KANDASAMY, I.A.S., ERODE DISTRICT
                                        ----

{{ content_body }}

--------------------------------------------------------------------------------
{{ footer_text }}
"""

# 2. Official Circular (English)
CIRCULAR_TEMPLATE_EN = """CIRCULAR NO: {{ ref_number }}                                            DATE: {{ date }}

                 OFFICE OF THE DISTRICT COLLECTOR, ERODE DISTRICT
                                OFFICIAL CIRCULAR
                                        ----

{{ content_body }}

--------------------------------------------------------------------------------
{{ footer_text }}
"""

# 3. Office Memorandum (English)
MEMO_TEMPLATE_EN = """MEMORANDUM NO: {{ ref_number }}                                          DATE: {{ date }}

                 OFFICE OF THE DISTRICT COLLECTOR, ERODE DISTRICT
                               OFFICE MEMORANDUM
                                        ----

{{ content_body }}

--------------------------------------------------------------------------------
{{ footer_text }}
"""

# 4. Meeting Minutes (English)
MEETING_MINUTES_TEMPLATE_EN = """PROCEEDINGS OF THE DISTRICT COLLECTOR & DISTRICT MAGISTRATE, ERODE
             PRESENT: THIRU S. KANDASAMY, I.A.S., DISTRICT COLLECTOR

Roc. No: {{ ref_number }}/2026                                         Dated: {{ date }}
--------------------------------------------------------------------------------
Sub: {{ subject }} – Minutes of Review Meeting – Approval and Orders – Issued.
Ref: G.O. Ms. No. 78, Agriculture & Farmers Welfare Department, dated 17.02.2016.
                                    <><><>

{{ content_body }}

--------------------------------------------------------------------------------
                                                Sd/- S. Kandasamy
                                                District Collector,
                                                Erode District.

/ By Order /

                                  Personal Assistant to District Collector,
                                  District Collectorate,
                                  Erode.
"""

# ---------------------------------------------------------------------------
# Template Registry (Bilingual Lookup)
# ---------------------------------------------------------------------------
TEMPLATE_REGISTRY = {
    "press_release": {
        "template": PRESS_RELEASE_TEMPLATE_TA,
        "template_ta": PRESS_RELEASE_TEMPLATE_TA,
        "template_en": PRESS_RELEASE_TEMPLATE_EN,
        "title_ta": "செய்தி குறிப்பு",
        "title_en": "Press Release",
        "ref_prefix": "PR",
        "default_footer_ta": "வெளியீடு செய்தி மக்கள் தொடர்பு அலுவலர், ஈரோடு மாவட்டம்.",
        "default_footer_en": "Issued by: District Public Relations Officer, Erode District.",
    },
    "circular": {
        "template": CIRCULAR_TEMPLATE_TA,
        "template_ta": CIRCULAR_TEMPLATE_TA,
        "template_en": CIRCULAR_TEMPLATE_EN,
        "title_ta": "அலுவலக சுற்றறிக்கை",
        "title_en": "Official Circular",
        "ref_prefix": "CIR",
        "default_footer_ta": "மாவட்ட ஆட்சித்தலைவர் அவர்களின் உத்தரவுப்படி, ஈரோடு மாவட்டம்.",
        "default_footer_en": "By Order of the District Collector, Erode District.",
    },
    "memo": {
        "template": MEMO_TEMPLATE_TA,
        "template_ta": MEMO_TEMPLATE_TA,
        "template_en": MEMO_TEMPLATE_EN,
        "title_ta": "அலுவலக குறிப்பாணை",
        "title_en": "Office Memorandum",
        "ref_prefix": "MEM",
        "default_footer_ta": "மாவட்ட ஆட்சித்தலைவர் அவர்களின் உத்தரவுப்படி, ஈரோடு மாவட்டம்.",
        "default_footer_en": "Personal Assistant to the District Collector, Erode District.",
    },
    "meeting_minutes": {
        "template": MEETING_MINUTES_TEMPLATE_TA,
        "template_ta": MEETING_MINUTES_TEMPLATE_TA,
        "template_en": MEETING_MINUTES_TEMPLATE_EN,
        "title_ta": "கூட்ட நடவடிக்கை பதிவேடு",
        "title_en": "Meeting Minutes",
        "ref_prefix": "MIN",
        "default_footer_ta": "நேர்முக உதவியாளர், மாவட்ட ஆட்சியர் அலுவலகம், ஈரோடு.",
        "default_footer_en": "Personal Assistant to District Collector, District Collectorate, Erode.",
    },
}

