import sys
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

import sqlite3
conn = sqlite3.connect('collectorate_workflow.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

rows = cur.execute('SELECT content_id, template_type, ref_number, subject, substr(content_body, 1, 300) as body FROM official_content').fetchall()
for r in rows:
    print(dict(r))
