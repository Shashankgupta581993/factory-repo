import sqlite3, json, csv, io, re, subprocess
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

# --- DATABASE LOGIC ---
def init_db():
    conn = sqlite3.connect('factory.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS routing (id INTEGER PRIMARY KEY, order_no TEXT, part_no TEXT, part_name TEXT, op_no INTEGER, op_name TEXT, resource TEXT, setup_time TEXT, time_per_item TEXT, qty INTEGER, due_date TEXT)''')
    conn.commit()
    conn.close()

def parse_time_to_mins(time_str):
    hrs = re.search(r'(\d+)\s*Hour', str(time_str), re.IGNORECASE)
    mins = re.search(r'(\d+)\s*Min', str(time_str), re.IGNORECASE)
    return ((int(hrs.group(1)) if hrs else 0) * 60) + (int(mins.group(1)) if mins else 0)

# --- PURE API SERVER ---
class AppServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if '/api/data' in self.path:
            conn = sqlite3.connect('factory.db')
            rows = conn.execute("SELECT * FROM routing").fetchall()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
            self.end_headers()
            self.wfile.write(json.dumps(rows).encode())
            
        elif '/api/backup' in self.path:
            # 1. Basic Security: Require a secret token to trigger the backup
            query = parse_qs(urlparse(self.path).query)
            if query.get('token', [''])[0] != 'factory-secure-2026':
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden: Invalid Backup Token")
                return
            
            # 2. Get the current day of the week for the rolling 7-day backup
            day_of_week = datetime.now().strftime('%A')
            backup_name = f"factory_backup_{day_of_week}.db"
            
            # 3. Use the VM's native gcloud tool to copy the database to your bucket
            try:
                subprocess.run(
                    ['gcloud', 'storage', 'cp', 'factory.db', f'gs://zero-cost-bucket-shashank-581993/backups/{backup_name}'],
                    check=True, capture_output=True
                )
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "file": backup_name}).encode())
            except subprocess.CalledProcessError as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Backup Failed to upload to Cloud Storage")

    def do_POST(self):
        if '/api/upload' in self.path:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, "Empty payload")
                return
                
            body = self.rfile.read(content_length)
            csv_data = body.split(b'\r\n\r\n')[1].split(b'\r\n----')[0].decode('utf-8')
            reader = csv.reader(io.StringIO(csv_data))
            next(reader, None) # Skip header
            
            conn = sqlite3.connect('factory.db')
            conn.executemany("INSERT INTO routing (order_no, part_no, part_name, op_no, op_name, resource, setup_time, time_per_item, qty, due_date) VALUES (?,?,?,?,?,?,?,?,?,?)", reader)
            conn.commit()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode())
            
        elif '/api/delete' in self.path:
            id = parse_qs(urlparse(self.path).query)['id'][0]
            conn = sqlite3.connect('factory.db')
            conn.execute("DELETE FROM routing WHERE id = ?", (id,))
            conn.commit()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode())

        # --- NEW CODE FOR CI/CD TEST ---
        elif '/api/delete_all' in self.path:
            conn = sqlite3.connect('factory.db')
            conn.execute("DELETE FROM routing")
            conn.commit()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode())

if __name__ == "__main__":
    init_db()
    HTTPServer(('0.0.0.0', 8000), AppServer).serve_forever()