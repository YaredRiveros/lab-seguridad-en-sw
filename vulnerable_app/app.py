from flask import Flask, request, render_template, g
import sqlite3
import os
import subprocess
import platform
import logging
from logging.handlers import RotatingFileHandler
import re
import time

# --- Logging setup ---
logger = logging.getLogger('vuln_app')
logger.setLevel(logging.INFO)
log_handler = RotatingFileHandler(os.path.join(os.path.dirname(__file__), 'vuln_app.log'), maxBytes=1000000, backupCount=3)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
log_handler.setFormatter(formatter)
logger.addHandler(log_handler)

# Simple in-memory throttle/ban store: {ip: [(timestamp, pattern_match), ...]}
ip_events = {}
ban_store = {}  # {ip: ban_expiry_timestamp}

# Suspicious tokens regex (basic)
suspicious_re = re.compile(r"[\'\";\-\/\*\*]|&&|\||/\*|\*/")

def is_banned(ip):
    expiry = ban_store.get(ip)
    if expiry and expiry > time.time():
        return True
    if expiry and expiry <= time.time():
        del ban_store[ip]
    return False

def record_event(ip, suspicious):
    now = time.time()
    events = ip_events.setdefault(ip, [])
    events.append((now, suspicious))
    # keep last 100 events
    if len(events) > 100:
        del events[:-100]
    # simple rule: si en las últimas 60s hay 5 eventos con suspicious=True -> ban 300s
    window = [e for e in events if e[0] > now - 60]
    suspicious_count = sum(1 for e in window if e[1])
    if suspicious_count >= 5:
        ban_store[ip] = now + 300
        logger.warning(f"IP {ip} temporalmente baneada por comportamiento sospechoso")


app = Flask(__name__)
DATABASE = os.path.join(os.path.dirname(__file__), 'data.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/')
def index():
    # Simple index so the root path responds even if templates are missing
    try:
        return render_template('index.html')
    except Exception:
        return ("Vulnerable app - root. Usa /search (POST) y /ping?host=...", 200, {'Content-Type': 'text/plain; charset=utf-8'})


@app.route('/ping')
def ping_query():
    """Vulnerable: acepta payloads vía query string, ejecuta shell=True (intencionalmente inseguro).
    Ejemplo: /ping?host=127.0.0.1; ls
    """
    client_ip = request.remote_addr or 'unknown'
    host = request.args.get('host', '')
    # IDS: check ban
    if is_banned(client_ip):
        logger.info(f"Blocked request from banned IP {client_ip} to /ping with host={host}")
        return ("Blocked", 403)
    # check suspicious tokens
    suspicious = bool(suspicious_re.search(host))
    record_event(client_ip, suspicious)
    logger.info(f"Request from {client_ip} endpoint=/ping params=host={host} UA={request.headers.get('User-Agent')} suspicious={suspicious}")
    if platform.system() == 'Windows':
        cmd = "ping -n 1 %s" % host
    else:
        cmd = "ping -c 1 %s" % host
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, universal_newlines=True, timeout=10)
        logger.info(f"Executed command for {client_ip}: {cmd}")
        return f"Comando ejecutado: {cmd}\n\n{output}", 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except subprocess.CalledProcessError as e:
        logger.error(f"Command error for {client_ip}: {cmd} -> {e}")
        output = e.output
        return f"Comando ejecutado: {cmd}\n\n{output}", 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except Exception as e:
        logger.exception(f"Unexpected error executing command for {client_ip}: {cmd}")
        output = str(e)
        return f"Comando ejecutado: {cmd}\n\n{output}", 500, {'Content-Type': 'text/plain; charset=utf-8'}

# Vulnerable: construye la consulta concatenando la entrada del usuario
@app.route('/search', methods=['POST'])
def search():
    username = request.form.get('username', '')
    db = get_db()
    # ¡Vulnerable a SQL injection!
    query = "SELECT id, username, bio FROM users WHERE username = '%s'" % username
    cur = db.cursor()
    try:
        cur.execute(query)
        rows = cur.fetchall()
    except Exception as e:
        rows = []
        error = str(e)
        return render_template('results.html', rows=rows, error=error, query=query)

    return render_template('results.html', rows=rows, error=None, query=query)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
