from flask import Flask, render_template, jsonify, request, send_file
from flask_socketio import SocketIO
from flask_cors import CORS
from datetime import datetime
import json
import csv
import io
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
CORS(app)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

tracking_data = []
geofences = []
device_status = {}
alerts_history = []
violation_states = {}


def point_in_polygon(lat, lon, polygon):
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]['lat'], polygon[i]['lng']
        xj, yj = polygon[j]['lat'], polygon[j]['lng']
        if ((yi > lon) != (yj > lon)) and (lat < (xj - xi) * (lon - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def check_geofence_violations(lat, lon, device_id):
    violations = []
    current_state_key = f"{device_id}_violations"
    if current_state_key not in violation_states:
        violation_states[current_state_key] = set()
    current_violations = violation_states[current_state_key]
    new_violations = set()

    for fence in geofences:
        if not fence.get('active', True):
            continue
        is_inside = point_in_polygon(lat, lon, fence['coordinates'])
        fence_key = f"{fence['id']}_{fence['type']}"

        if fence['type'] == 'safe_zone' and not is_inside:
            new_violations.add(fence_key)
            violation = {
                'fence_id': fence['id'],
                'fence_name': fence['name'],
                'type': 'exit_safe_zone',
                'message': f'ALERT: Animal outside safe zone [{fence["name"]}]',
                'device_id': device_id,
                'timestamp': datetime.now().isoformat(),
                'severity': 'danger',
                'continuous': True
            }
            violations.append(violation)
            alerts_history.append(violation)
        elif fence['type'] == 'restricted_zone' and is_inside:
            new_violations.add(fence_key)
            violation = {
                'fence_id': fence['id'],
                'fence_name': fence['name'],
                'type': 'entered_restricted_zone',
                'message': f'ALERT: Animal in restricted zone [{fence["name"]}]',
                'device_id': device_id,
                'timestamp': datetime.now().isoformat(),
                'severity': 'danger',
                'continuous': True
            }
            violations.append(violation)
            alerts_history.append(violation)

    violation_states[current_state_key] = new_violations
    if len(alerts_history) > 200:
        alerts_history[:] = alerts_history[-200:]
    return violations


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/gps', methods=['POST'])
def receive_gps():
    try:
        data = request.get_json()
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        device_id = data.get('device_id', 'unknown')
        rssi = data.get('rssi', 0)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        data_point = {
            'latitude': lat,
            'longitude': lon,
            'timestamp': timestamp,
            'device_id': device_id,
            'rssi': rssi,
            'speed': data.get('speed', 0),
            'altitude': data.get('altitude', 0)
        }

        tracking_data.append(data_point)
        if len(tracking_data) > 2000:
            tracking_data[:] = tracking_data[-2000:]

        device_status[device_id] = {
            'last_seen': timestamp,
            'rssi': rssi,
            'status': 'online',
            'battery': data.get('battery', 100),
            'latitude': lat,
            'longitude': lon
        }

        violations = check_geofence_violations(lat, lon, device_id)
        socketio.emit('gps_update', {'data': data_point, 'violations': violations})

        return jsonify({'success': True, 'message': 'GPS data received', 'violations': len(violations)}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/api/tracking-data')
def api_tracking_data():
    limit = request.args.get('limit', type=int, default=500)
    return jsonify(tracking_data[-limit:])


@app.route('/api/latest-position')
def api_latest_position():
    latest = {}
    for point in reversed(tracking_data):
        device_id = point.get('device_id', 'unknown')
        if device_id not in latest:
            latest[device_id] = point
    return jsonify(list(latest.values()))


@app.route('/api/device-status')
def api_device_status():
    return jsonify(device_status)


@app.route('/api/geofences', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_geofences():
    global geofences
    if request.method == 'GET':
        return jsonify(geofences)
    elif request.method == 'POST':
        fence = request.json
        fence['id'] = datetime.now().timestamp()
        fence['created_at'] = datetime.now().isoformat()
        fence['active'] = True
        geofences.append(fence)
        save_geofences()
        socketio.emit('geofence_update', {'action': 'created', 'fence': fence})
        return jsonify({'success': True, 'fence': fence})
    elif request.method == 'PUT':
        fence_id = request.json.get('id')
        updated_fence = request.json
        for i, fence in enumerate(geofences):
            if fence['id'] == fence_id:
                geofences[i] = updated_fence
                save_geofences()
                socketio.emit('geofence_update', {'action': 'updated', 'fence': updated_fence})
                return jsonify({'success': True, 'fence': updated_fence})
        return jsonify({'success': False, 'message': 'Fence not found'}), 404
    elif request.method == 'DELETE':
        fence_id = request.args.get('id', type=float)
        geofences = [f for f in geofences if f['id'] != fence_id]
        save_geofences()
        socketio.emit('geofence_update', {'action': 'deleted', 'fence_id': fence_id})
        return jsonify({'success': True})


@app.route('/api/alerts')
def api_alerts():
    limit = request.args.get('limit', type=int, default=100)
    return jsonify(alerts_history[-limit:])


@app.route('/api/statistics')
def api_statistics():
    stats = {
        'total_points': len(tracking_data),
        'active_devices': len(device_status),
        'active_geofences': len([f for f in geofences if f.get('active', True)]),
        'total_alerts': len(alerts_history),
        'last_update': tracking_data[-1]['timestamp'] if tracking_data else None,
        'devices': device_status
    }
    return jsonify(stats)


@app.route('/api/heatmap-data')
def api_heatmap_data():
    heatmap_points = []
    for point in tracking_data[-500:]:
        heatmap_points.append([point['latitude'], point['longitude'], 1.0])
    return jsonify(heatmap_points)


@app.route('/api/export-csv')
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Timestamp', 'Device ID', 'Latitude', 'Longitude', 'RSSI', 'Speed', 'Altitude'])
    for point in tracking_data:
        writer.writerow([
            point['timestamp'],
            point.get('device_id', 'unknown'),
            point['latitude'],
            point['longitude'],
            point.get('rssi', 0),
            point.get('speed', 0),
            point.get('altitude', 0)
        ])
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    output.close()
    filename = f'tracking_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name=filename)


@app.route('/api/clear-data', methods=['POST'])
def clear_data():
    global tracking_data, alerts_history, violation_states
    tracking_data = []
    alerts_history = []
    violation_states = {}
    return jsonify({'success': True, 'message': 'Data cleared'})


def save_geofences():
    try:
        with open('geofences.json', 'w') as f:
            json.dump(geofences, f, indent=2)
    except Exception as e:
        print(f"Error saving geofences: {e}")


def load_geofences():
    global geofences
    try:
        if os.path.exists('geofences.json'):
            with open('geofences.json', 'r') as f:
                geofences = json.load(f)
    except Exception as e:
        print(f"Error loading geofences: {e}")


if __name__ == '__main__':
    load_geofences()
    print("=" * 60)
    print("Animal Tracking Dashboard Server")
    print("=" * 60)
    print("Mode: threading (SocketIO)")
    print("Dashboard URL: http://localhost:5001")
    print("API endpoint: http://localhost:5001/api/gps")
    print("=" * 60)
    socketio.run(app, debug=True, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)

