#!/usr/bin/env python3
import json
import urllib.request

# Get token
login_data = json.dumps({'username': 'operator', 'password': 'operator123'}).encode()
req = urllib.request.Request('http://127.0.0.1:8000/api/auth/login', data=login_data, headers={'Content-Type': 'application/json'})
auth = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
token = auth.get('access_token') or auth.get('token')
headers = {'Authorization': f'Bearer {token}'}

# Get current data
print("=== CURRENT DATA (24 hours) ===")
req_data = urllib.request.Request('http://127.0.0.1:8000/api/data/current?hours=24', headers=headers)
data_resp = json.loads(urllib.request.urlopen(req_data, timeout=30).read().decode())
records = data_resp.get('data', [])

# Find times around 8 PM
for rec in records:
    ts = rec['timestamp']
    hour = int(ts.split('T')[1].split(':')[0])
    if 18 <= hour <= 22:  # 6 PM to 10 PM
        print(f"{hour:02d}:00 - BOD: {float(rec['BOD']):5.1f} | COD: {float(rec['COD']):5.1f} | DO: {float(rec['DO']):4.1f} | pH: {float(rec['pH']):4.2f}")

print("\n=== ALERTS ===")
req_alerts = urllib.request.Request('http://127.0.0.1:8000/api/alerts?source=both', headers=headers)
alerts_resp = json.loads(urllib.request.urlopen(req_alerts, timeout=30).read().decode())
alerts = alerts_resp.get('alerts', [])

for alert in alerts:
    ts = alert['time']
    hour = int(ts.split('T')[1].split(':')[0])
    print(f"{hour:02d}:00 [{alert['severity']}] {alert['message']} (source: {alert['source']})")

print(f"\nTotal alerts: {len(alerts)}")
print("DO_DANGEROUS threshold: 3.0")
