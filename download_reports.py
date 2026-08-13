import json, os, re, urllib.request

with open('/home/ubuntu/surveillance_mas_research.json') as f:
    data = json.load(f)

outdir = '/home/ubuntu/pfe/research'
summary = []
for i, r in enumerate(data['results'], 1):
    out = r.get('output') or {}
    url = out.get('report_file', '')
    sub = out.get('subtopic', f'topic_{i}')
    slug = re.sub(r'[^a-z0-9]+', '_', sub.lower()).strip('_')[:50] or f'topic_{i}'
    path = os.path.join(outdir, f'{i:02d}_{slug}.md')
    if url:
        try:
            urllib.request.urlretrieve(url, path)
            print(f'OK {path}')
        except Exception as e:
            print(f'FAIL {sub}: {e}')
    summary.append({'subtopic': sub, 'file': path,
                    'key_findings': out.get('key_findings', ''),
                    'stack': out.get('recommended_stack', '')})

with open(os.path.join(outdir, 'summary.json'), 'w') as f:
    json.dump(summary, f, indent=2)
print('done')
