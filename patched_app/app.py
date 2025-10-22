from flask import Flask, request, render_template, g
import sqlite3
import os
import subprocess
import shlex
import logging
from logging.handlers import RotatingFileHandler
import re
import time

# --- Logging setup ---
logger = logging.getLogger('patched_app')
logger.setLevel(logging.INFO)
log_handler = RotatingFileHandler(os.path.join(os.path.dirname(__file__), 'patched_app.log'), maxBytes=1000000, backupCount=3)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
log_handler.setFormatter(formatter)
logger.addHandler(log_handler)

# Simple in-memory throttle/ban store
ip_events = {}
ban_store = {}

# Suspicious tokens regex
suspicious_re = re.compile(r"[\'\";\-/\*\*]|&&|\||/\*|\*/")

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
    if len(events) > 100:
        del events[:-100]
    window = [e for e in events if e[0] > now - 60]
    suspicious_count = sum(1 for e in window if e[1])
    if suspicious_count >= 5:
        ban_store[ip] = now + 300
        logger.warning(f"IP {ip} temporalmente baneada por comportamiento sospechoso")


def is_sql_error_suspicious(error_msg, query=None):
    """Detecta si un mensaje de error SQL contiene indicios de stacktrace o fragmentos de consulta.

    Retorna True si el mensaje parece contener un traceback, keywords SQL o fragmentos de consulta
    (por ejemplo SELECT/WHERE, comillas, punto y coma, 'syntax error', etc.).
    """
    if not error_msg:
        return False
    low = error_msg.lower()

    # Presencia explícita de traceback
    if 'traceback' in low:
        return True

    # Mensajes típicos de errores de SQL/DB que incluyen fragmentos
    if 'syntax error' in low or 'near "' in low or 'malformed' in low:
        return True

    # Palabras clave SQL visibles en el mensaje
    if re.search(r"\b(select|insert|update|delete|from|where|union|join|drop|table)\b", error_msg, re.IGNORECASE):
        return True

    # Comillas, punto y coma o comentarios de SQL en el mensaje
    if "'" in error_msg or '"' in error_msg or ';' in error_msg or '--' in error_msg:
        return True

    # Si la propia consulta aparece en el mensaje de error
    if query and query.lower() in low:
        return True

    return False


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
    return render_template('index.html')


@app.route('/ping')
def ping():
    client_ip = request.remote_addr or 'unknown'
    host = request.args.get('host', '')
    if is_banned(client_ip):
        logger.info(f"Blocked request from banned IP {client_ip} to /ping with host={host}")
        return ("Blocked", 403)

    # validate host (allow letters, numbers, dot and dash)
    suspicious = not bool(re.fullmatch(r"[0-9A-Za-z\.\-]+", host))
    record_event(client_ip, suspicious)
    logger.info(f"Request from {client_ip} endpoint=/ping params=host={host} UA={request.headers.get('User-Agent')} suspicious={suspicious}")
    if suspicious:
        return (f"Comando ejecutado: \n\nHost inválido", 200, {'Content-Type': 'text/plain; charset=utf-8'})

    # Build argument list and execute without shell
    if os.name == 'nt':
        cmd_list = ['ping', '-n', '1', host]
    else:
        cmd_list = ['ping', '-c', '1', host]
    try:
        proc = subprocess.run(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=10)
        output = proc.stdout
    except Exception as e:
        output = str(e)
    cmd = ' '.join(shlex.quote(p) for p in cmd_list)
    logger.info(f"Executed safe ping for {client_ip}: {cmd}")
    return (f"Comando ejecutado: {cmd}\n\n{output}", 200, {'Content-Type': 'text/plain; charset=utf-8'})


# Parcheada: consulta parametrizada
@app.route('/search', methods=['POST'])
def search():
    client_ip = request.remote_addr or 'unknown'
    username = request.form.get('username', '')
    if is_banned(client_ip):
        logger.info(f"Blocked request from banned IP {client_ip} to /search with username={username}")
        return ("Blocked", 403)
    suspicious = bool(suspicious_re.search(username))
    record_event(client_ip, suspicious)
    logger.info(f"Request from {client_ip} endpoint=/search params=username={username} UA={request.headers.get('User-Agent')} suspicious={suspicious}")

    db = get_db()
    # Usar consulta parametrizada para prevenir SQL injection
    query = "SELECT id, username, bio FROM users WHERE username = ?"
    cur = db.cursor()
    try:
        cur.execute(query, (username,))
        rows = cur.fetchall()
    except Exception as e:
        rows = []
        error = str(e)
        # Detectar si el mensaje de error parece contener stacktrace o fragmentos de consulta
        suspicious_error = is_sql_error_suspicious(error, query=query)
        logger.exception(f"DB error for {client_ip} executing parametrized query: suspicious={suspicious_error} msg={error}")

        # Si es sospechoso, registrar evento y potencialmente banear según umbrales
        if suspicious_error:
            record_event(client_ip, True)

        return render_template('results.html', rows=rows, error=error, query=query)

    return render_template('results.html', rows=rows, error=None, query=query)


if __name__ == '__main__':
    app.run(debug=True, port=5001)
