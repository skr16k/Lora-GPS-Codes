# Animal Tracking Dashboard by Shree Krishna Rimal — Run Locally

## Requirements
- Python 3.11

cd C:\Users\acer\Desktop\Animal_tracker_shree-main\Animal_tracker_shree-main\animal_tracking_RESPONSIVE
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py


## 5. Open in your browser
- On the same computer, open: `http://localhost:5001`  
  (or `http://127.0.0.1:5001`)
- The dashboard UI should load.

### Quick connectivity test
- From another PC on the same Wi‑Fi, open a browser and go to `http://<PC_IP>:5001`.
- Or, from that other PC, run: `ping <PC_IP>`
  - If ping fails, the issue is with the network/firewall, not the app code.

## 6. Hardware
If you use the ESP8266 + GPS setup:
- Upload `hardware/ESP8266_Receiver_HTTP.ino` to the ESP8266.
- Upload `tx/tx.ino` to the transmitter board.
- Configure the ESP8266 code to send HTTP requests to:
  - `http://<YOUR_PC_LOCAL_IP>:5001/api/gps`

## Features
- Responsive dashboard (mobile / tablet / desktop)
- Real-time GPS position updates
- Geofencing with alerts
- Heatmap view
- Device status
- CSV export of tracking data
