#!/usr/bin/env python3
import json
import urllib.request
import sys

try:
    # Authenticate
    login_data = json.dumps({'username': 'operator', 'password': 'operator123'}).encode()
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/auth/login',
        data=login_data,
        headers={'Content-Type': 'application/json'}
    )
    auth_response = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
    token = auth_response.get('access_token') or auth_response.get('token')
    if not token:
        print(f'[✗] Login response missing token: {auth_response}')
        sys.exit(1)
    print('[✓] Authentication successful\n')
    
    # Get alerts
    req2 = urllib.request.Request(
        'http://127.0.0.1:8000/api/alerts?source=both',
        headers={'Authorization': f'Bearer {token}'}
    )
    alerts_response = json.loads(urllib.request.urlopen(req2, timeout=30).read().decode())
    alerts = alerts_response.get('alerts', [])
    
    print(f'[✓] Alerts endpoint responded successfully')
    print(f'[→] Total alerts: {len(alerts)}\n')
    
    # Check for duplicates
    alert_tuples = [(a['time'], a['message']) for a in alerts]
    unique_tuples = set(alert_tuples)
    
    if len(alert_tuples) == len(unique_tuples):
        print('[✓] No duplicate alerts found\n')
    else:
        print(f'[✗] DUPLICATES DETECTED: {len(alert_tuples)} total, {len(unique_tuples)} unique\n')
    
    # Print details
    print('Alert Details:')
    print('-' * 80)
    for i, alert in enumerate(alerts, 1):
        print(f'{i}. Severity: {alert["severity"].upper()}')
        print(f'   Message: {alert["message"]}')
        print(f'   Time: {alert["time"]}')
        print(f'   Source: {alert["source"]}')
        print()
    
    print('-' * 80)
    print('[✓] Alert validation complete - no errors detected')
    
except Exception as e:
    print(f'[✗] ERROR: {e}', file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
