# simple script to export sessions collection to JSON for backup
from db import sessions
import json

all_docs = list(sessions.find())
for d in all_docs:
    d['_id'] = str(d['_id'])
with open('sessions_backup.json', 'w') as f:
    json.dump(all_docs, f, indent=2)

print('exported', len(all_docs))