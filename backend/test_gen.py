import urllib.request, urllib.error, json

req = urllib.request.Request(
    'http://localhost:8000/projects/test-template/generate-org',
    data=json.dumps({'stage': 'seed', 'industry': 'tech_saas', 'success_level': 50}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST'
)

try:
    r = urllib.request.urlopen(req)
    d = json.loads(r.read().decode())
    print(f"OK - roles: {len(d['roles'])}, deps: {len(d['dependencies'])}, debt: {d['diagnostics']['structural_debt']}")
    print(f"\nROLES:")
    for rid, role in d['roles'].items():
        print(f"  {rid}: {role['name']}")
    if d.get('projection'):
        print(f"\nDEPARTMENTS ({len(d['projection']['departments'])}):")
        for dept in d['projection']['departments']:
            print(f"  {dept['id']}: {dept['semantic_label']} → {len(dept['role_ids'])} roles: {dept['role_ids']}")
            print(f"    density: {dept['internal_density']}, ext_deps: {dept['external_dependencies']}")
    else:
        print("\nNo projection!")
except urllib.error.HTTPError as e:
    print(f"FAIL ({e.code}): {e.read().decode()[:500]}")
