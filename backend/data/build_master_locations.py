"""Build SQLite master locations database for Erode District revenue administration."""

import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
DB_PATH = DATA_DIR / "master_locations.db"

# Official Administrative hierarchy for Erode District
ERODE_TALUKS_AND_VILLAGES = [
    {
        "taluk_ta": "ஈரோடு",
        "taluk_en": "Erode",
        "villages": [
            ("சூரம்பட்டி", "Surampatti", "Erode"),
            ("காசிபாளையம்", "Kasipalayam", "Erode"),
            ("பெரியசேமூர்", "Periyasemur", "Erode"),
            ("வீரப்பன்சத்திரம்", "Veerappanchatram", "Erode"),
            ("திண்டல்", "Thindal", "Erode"),
            ("வில்லரசம்பட்டி", "Villarasampatti", "Erode"),
            ("மேட்டுநாசுவன்பாளையம்", "Mettunasuvanpalayam", "Erode"),
            ("நசியனூர்", "Nasiyanur", "Erode"),
            ("கதிரம்பட்டி", "Kathirampatti", "Erode"),
            ("இரங்கம்பாளையம்", "Rangampalayam", "Erode"),
            ("சூரியம்பாளையம்", "Suriyampalayam", "Erode"),
            ("பவளத்தாம்பாளையம்", "Pavalathampalayam", "Erode"),
            ("சித்தோடு", "Chithode", "Erode"),
            ("குமாரவலசு", "Kumaravalasu", "Erode"),
        ]
    },
    {
        "taluk_ta": "மொடக்குறிச்சி",
        "taluk_en": "Modakkurichi",
        "villages": [
            ("மொடக்குறிச்சி", "Modakkurichi", "Modakkurichi"),
            ("எழுமாத்தூர்", "Elumathur", "Modakkurichi"),
            ("கணபதிபாளையம்", "Ganapathipalayam", "Modakkurichi"),
            ("அவல்பூந்துறை", "Avalpoondurai", "Modakkurichi"),
            ("ஆனந்தம்பாளையம்", "Ananthampalayam", "Modakkurichi"),
            ("கந்தசாமிபாளையம்", "Kanthasamypalayam", "Modakkurichi"),
            ("நஞ்சை ஊத்துக்குளி", "Nanjai Uthukuli", "Modakkurichi"),
            ("புஞ்சை லக்காபுரம்", "Punjai Lakkapuram", "Modakkurichi"),
        ]
    },
    {
        "taluk_ta": "கொடுமுடி",
        "taluk_en": "Kodumudi",
        "villages": [
            ("கொடுமுடி", "Kodumudi", "Kodumudi"),
            ("உஞ்சலூர்", "Unjalur", "Kodumudi"),
            ("வெள்ளோட்டம்பரப்பு", "Vellottambarappu", "Kodumudi"),
            ("கொளத்துப்பாளையம்", "Kolathupalayam", "Kodumudi"),
            ("பாசூர்", "Pasur", "Kodumudi"),
            ("ஆவுடையார்பாறை", "Avudayarpari", "Kodumudi"),
        ]
    },
    {
        "taluk_ta": "பெருந்துறை",
        "taluk_en": "Perundurai",
        "villages": [
            ("பெருந்துறை", "Perundurai", "Perundurai"),
            ("சென்னிமலை", "Chennimalai", "Perundurai"),
            ("விஜயமங்கலம்", "Vijayamangalam", "Perundurai"),
            ("திங்களூர்", "Thingalur", "Perundurai"),
            ("கருக்குப்பாளையம்", "Karukkupalayam", "Perundurai"),
            ("சீனாபுரம்", "Seenapuram", "Perundurai"),
            ("மொண்டிபாளையம்", "Mondipalayam", "Perundurai"),
            ("துடுப்பதி", "Thudupathi", "Perundurai"),
            ("முள்ளம்பட்டி", "Mullampatti", "Perundurai"),
        ]
    },
    {
        "taluk_ta": "பவானி",
        "taluk_en": "Bhavani",
        "villages": [
            ("பவானி", "Bhavani", "Bhavani"),
            ("கவிந்தபாடி", "Kavindapadi", "Bhavani"),
            ("ஆப்பக்கூடல்", "Appakudal", "Bhavani"),
            ("ஜம்பை", "Jambai", "Bhavani"),
            ("ஒரிச்சேரி", "Oricheri", "Bhavani"),
            ("சன்னியாசிபட்டி", "Sanniyasipatti", "Bhavani"),
            ("வருணபுரம்", "Varunapuram", "Bhavani"),
            ("மைலம்பாடி", "Mylambadi", "Bhavani"),
        ]
    },
    {
        "taluk_ta": "அந்தியூர்",
        "taluk_en": "Anthiyur",
        "villages": [
            ("அந்தியூர்", "Anthiyur", "Anthiyur"),
            ("அம்மாபேட்டை", "Ammapet", "Anthiyur"),
            ("குருவரெட்டியூர்", "Guruvareddiyur", "Anthiyur"),
            ("பர்கூர்", "Bargur", "Anthiyur"),
            ("பிரம்மதேசம்", "Brammadesam", "Anthiyur"),
            ("செண்பகப்புதூர்", "Shenbagaputhur", "Anthiyur"),
            ("வேம்பத்தி", "Vembathi", "Anthiyur"),
        ]
    },
    {
        "taluk_ta": "கோபிசெட்டிபாளையம்",
        "taluk_en": "Gobichettipalayam",
        "villages": [
            ("கோபிசெட்டிபாளையம்", "Gobichettipalayam", "Gobichettipalayam"),
            ("டி.என்.பாளையம்", "TN Palayam", "Gobichettipalayam"),
            ("லக்கம்பட்டி", "Lakkampatti", "Gobichettipalayam"),
            ("கள்ளிப்பட்டி", "Kallipatti", "Gobichettipalayam"),
            ("கொடிவேரி", "Kodiveri", "Gobichettipalayam"),
            ("நஞ்சைபுளியம்பட்டி", "Nanjaipuliampatti", "Gobichettipalayam"),
            ("சிறுவலூர்", "Siruvalur", "Gobichettipalayam"),
            ("குண்டேரிப்பள்ளம்", "Kunderipallam", "Gobichettipalayam"),
        ]
    },
    {
        "taluk_ta": "சத்தியமங்கலம்",
        "taluk_en": "Sathyamangalam",
        "villages": [
            ("சத்தியமங்கலம்", "Sathyamangalam", "Sathyamangalam"),
            ("பவானிசாகர்", "Bhavanisagar", "Sathyamangalam"),
            ("புஞ்சைபுளியம்பட்டி", "Punjaipuliampatti", "Sathyamangalam"),
            ("அலத்துக்கோம்பை", "Alathucombai", "Sathyamangalam"),
            ("பண்ணாரி", "Bannari", "Sathyamangalam"),
            ("ராஜன் நகர்", "Rajan Nagar", "Sathyamangalam"),
            ("கொத்தமங்கலம்", "Kothamangalam", "Sathyamangalam"),
        ]
    },
    {
        "taluk_ta": "தாளவாடி",
        "taluk_en": "Thalavadi",
        "villages": [
            ("தாளவாடி", "Thalavadi", "Thalavadi"),
            ("திம்பம்", "Dhimbam", "Thalavadi"),
            ("ஆசனூர்", "Hasanur", "Thalavadi"),
            ("திங்களூர்மலை", "Thingalur Hills", "Thalavadi"),
            ("கெட்டவாடி", "Gettavadi", "Thalavadi"),
        ]
    },
    {
        "taluk_ta": "நம்பியூர்",
        "taluk_en": "Nambiyur",
        "villages": [
            ("நம்பியூர்", "Nambiyur", "Nambiyur"),
            ("மலையப்பாளையம்", "Malayampalayam", "Nambiyur"),
            ("கெட்டிச்செவியூர்", "Getticheviyur", "Nambiyur"),
            ("வேமாண்டாம்பாளையம்", "Vemandampalayam", "Nambiyur"),
        ]
    }
]


def build_locations_db() -> None:
    """Create and seed the master locations database."""
    conn = sqlite3.connect(str(DB_PATH))
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS taluks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            taluk_ta TEXT UNIQUE NOT NULL,
            taluk_en TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS villages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            taluk_id INTEGER REFERENCES taluks(id),
            village_ta TEXT NOT NULL,
            village_en TEXT NOT NULL,
            firka TEXT,
            UNIQUE(taluk_id, village_ta)
        );

        CREATE INDEX IF NOT EXISTS idx_village_ta ON villages(village_ta);
        CREATE INDEX IF NOT EXISTS idx_taluk_ta ON taluks(taluk_ta);
        """)

        cursor = conn.cursor()
        for item in ERODE_TALUKS_AND_VILLAGES:
            cursor.execute(
                "INSERT OR IGNORE INTO taluks (taluk_ta, taluk_en) VALUES (?, ?)",
                (item["taluk_ta"], item["taluk_en"])
            )
            cursor.execute("SELECT id FROM taluks WHERE taluk_ta = ?", (item["taluk_ta"],))
            taluk_id = cursor.fetchone()[0]

            for v_ta, v_en, firka in item["villages"]:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO villages (taluk_id, village_ta, village_en, firka)
                    VALUES (?, ?, ?, ?)
                    """,
                    (taluk_id, v_ta, v_en, firka)
                )

    conn.close()
    print(f"Master locations DB built successfully at {DB_PATH}")


if __name__ == "__main__":
    build_locations_db()
