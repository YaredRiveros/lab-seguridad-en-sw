# Informe del laboratorio — Comparación app vulnerable vs parcheada

Resumen
-------
Se han creado dos aplicaciones web mínimas en Flask: `vulnerable_app` (puerto 5000) y `patched_app` (puerto 5001). Ambas usan SQLite y contienen una tabla `users` con usuarios de ejemplo (`alice`, `bob`, `admin`). La app vulnerable construye consultas SQL concatenando la entrada del usuario (vulnerable a SQLi). La app parcheada usa consultas parametrizadas.

Estructura del repositorio
--------------------------
- vulnerable_app/: app vulnerable (Flask), puerto 5000
  - app.py
  - init_db.py
  - templates/
  - requirements.txt
- patched_app/: app parcheada (Flask), puerto 5001
  - app.py
  - init_db.py
  - templates/
  - requirements.txt
- REPORT.md (este archivo)

Instrucciones para ejecutar (docker-compose)
---------------------------

Sigue estos pasos para ejecutar las dos aplicaciones dentro de contenedores Docker. Las instrucciones están escritas para PowerShell en Windows; en macOS/Linux los pasos son equivalentes adaptando la sintaxis de la shell.

Requisitos
- Tener instalado Docker Desktop (incluye Docker Engine y Docker Compose). Asegúrate de que Docker esté corriendo antes de continuar.

Pasos para clonar, construir y ejecutar (mínimos)
1. Clonar el repositorio:

  git clone <URL-del-repo>
  cd lab-seguridad-en-sw

2. Inicializar las bases de datos (opciones):

  a) Si tienes Python en el host (rápido):

    # En PowerShell (desde la raíz del repo)
    python vulnerable_app/init_db.py
    python patched_app/init_db.py

  b) Si NO tienes Python en el host: ejecutar la inicialización dentro de los contenedores usando Docker Compose (no modifica tu host):

    docker-compose run --rm vulnerable_app python init_db.py
    docker-compose run --rm patched_app python init_db.py

  Nota: tras los cambios recientes, los volúmenes del proyecto están montados en modo lectura/escritura por defecto, por lo que los archivos `data.db` y los logs que se creen dentro del contenedor aparecerán en las carpetas locales correspondientes.

3. Construir las imágenes con docker-compose (desde la raíz del repo):

  docker-compose build

4. Levantar los servicios (reconstruye si es necesario):

  docker-compose up --build

  - Esto expondrá `vulnerable_app` en el puerto 5000 de la máquina y `patched_app` en el puerto 5001 según `docker-compose.yml`.
  - Si prefieres ejecutar en segundo plano, añade `-d`:

    docker-compose up -d --build

5. Comprobar que las apps están corriendo:

  - Vulnerable: http://127.0.0.1:5000/
  - Patched:   http://127.0.0.1:5001/

6. Parar los servicios cuando termines:

  docker-compose down

Notas y recomendaciones (actualizadas)
- Los volúmenes en `docker-compose.yml` están montados en modo lectura/escritura para permitir que las aplicaciones creen archivos de log (`*.log`) y las bases de datos (`data.db`) dentro de las carpetas `vulnerable_app/` y `patched_app/`. Esto evita errores como "Read-only file system" cuando la app intenta abrir/crear logs.
- Las aplicaciones Flask están configuradas para escuchar en `0.0.0.0` dentro del contenedor, por lo que los puertos mapeados funcionan desde el host (es decir, `http://127.0.0.1:5000/` y `http://127.0.0.1:5001/` son accesibles desde tu navegador).
- Si prefieres no permitir que los contenedores escriban sobre el código fuente local, una alternativa más limpia es usar volúmenes nombrados para datos/logs. Ejemplo en `docker-compose.yml`:

  services:
   vulnerable_app:
    volumes:
      - ./vulnerable_app:/app:ro   # código en modo sólo lectura
      - vuln_data:/app/data       # volumen nombrado para DB/logs

  volumes:
   vuln_data:

  Con esto el código queda protegido y los datos/logs se almacenan en un volumen gestionado por Docker.
- Si tu profesor no tiene Python y prefieres inicializar las DB automáticamente al arrancar, puedo preparar una versión de los `Dockerfile` o un `entrypoint` que ejecute `init_db.py` durante el build o al inicio del contenedor.
- Observación: Docker Compose emite una advertencia si el campo `version` está presente en `docker-compose.yml` (en algunas versiones modernas de Compose la clave `version` ya no es necesaria). Puedes eliminar la línea `version: '3.8'` para evitar la advertencia, aunque no afecta el funcionamiento.

Fin de la sección Docker Compose.

SQL injection
-----------------------------------------
Nota: las preguntas originales del PDF no se pudieron extraer como texto legible desde el PDF adjunto en este entorno. Asumí que las preguntas 1-6 buscan demostrar vulnerabilidades de inyección SQL, extracción de datos, comparación y mitigación. A continuación se proponen respuestas prácticas y pasos de verificación que cubren las típicas preguntas de laboratorio.

1) ¿Cómo demostrar que la app es vulnerable a SQL injection?
- En la app vulnerable, en la página principal se introduce `username`. En lugar de un nombre válido probar la carga:
  ' OR '1'='1
  Esto convierte la consulta en: SELECT ... WHERE username = '' OR '1'='1'
  Resultado: lista todos los usuarios.
- Evidencia: la plantilla muestra la consulta ejecutada y los resultados (incluyendo `admin`).

Ejemplo de app vulnerable:
  <img width="1348" height="442" alt="image" src="https://github.com/user-attachments/assets/72269595-25f0-427e-9741-9d42bbf10b6c" />

Ejemplo de app parcheada:

<img width="1219" height="433" alt="image" src="https://github.com/user-attachments/assets/25e131c9-7e5f-4cfe-988b-e9a45e59a868" />
  
Se logra prevenir SQL injections usando consultas parametrizadas:

```python
db = get_db()
# Usar consulta parametrizada para prevenir SQL injection
query = "SELECT id, username, bio FROM users WHERE username = ?"
cur = db.cursor()


2) ¿Cómo extraer datos sensibles (por ejemplo, la contraseña o bio del admin)?
- En la DB de ejemplo el campo `bio` contiene texto que actúa como "secreto". Con inyección se puede forzar un `UNION` o seleccionar campos distintos. En SQLite, puede probarse:
  `' UNION SELECT 1, username, bio FROM users--`
  o usar boolean-based extraction si la app restringe el tipo de respuesta.
- En este laboratorio la forma más directa es `' OR '1'='1` para listar filas existentes.

3) ¿Cómo enumerar usuarios?
- Igual que 1), usar `' OR '1'='1` listará todos los registros. También usar patrones: `%` con LIKE si la aplicación tuviera filtros.

4) ¿Qué payloads se usaron y por qué funcionan?
- `' OR '1'='1` rompe la condición WHERE y la convierte en verdadera para todas las filas.
- `'; DROP TABLE users;--` (no usado aquí) es un ejemplo de payload de daño si el motor y la interfaz lo permitieran.
- `UNION SELECT` permite combinar resultados de otra consulta.


Command Injection (GET query payloads)
------------------------------------
Además de SQL injection, el laboratorio incluye un endpoint `/ping` que acepta el parámetro `host` por query string.

Ejemplos usando GET (payloads sobre la URL):
1) `/ping?host=127.0.0.1; ls`
2) `/ping?host=127.0.0.1&&id`

Comportamiento observado:
- vulnerable_app: la query string se concatena en un comando ejecutado con `shell=True`. Eso permite que operadores de shell (`;`, `&&`, `|`) introducidos por el atacante se ejecuten. En sistemas UNIX, `/ping?host=127.0.0.1; ls` ejecutará `ping -c 1 127.0.0.1; ls` y la salida de `ls` aparecerá en el cuerpo de la respuesta (texto plano). En Windows, se utiliza `&&` para concatenar consultas en shell y se usan las opciones `-n` en lugar de `-c` para el ping. 

<img width="1025" height="703" alt="image" src="https://github.com/user-attachments/assets/33ae6da3-f44f-4609-b967-9dd461dc4489" />

- patched_app: con el mismo payload la aplicación parcheada valida el parámetro `host` (solo `[0-9a-zA-Z.-]`) y ejecuta `subprocess.run` con una lista de argumentos (sin `shell=True`). Por tanto el input no se interpreta por un shell: los caracteres `;`, `&&` no separan comandos y no provocan ejecución adicional. Si la validación falla, la app responde "Host inválido".
<img width="952" height="305" alt="image" src="https://github.com/user-attachments/assets/712a2014-9c29-4991-b71c-129409e2113e" />

Ejemplo práctico de comportamiento:
- Vulnerable: GET `/ping?host=127.0.0.1; ls` → respuesta muestra "Comando ejecutado: ping -c 1 127.0.0.1; ls" y luego el listado de archivos.
- Patched: GET `/ping?host=127.0.0.1; ls` → validación falla (carácter `;`), responde "Host inválido".

Nota: Para windows, usar `%26%26` en vez de `;` -> `%26%26` es `&&` en URL-encoded, que concatena consultas en cmd.

Recomendaciones (resumen): evitar `shell=True`, validar entrada, y preferir APIs nativas en lugar de ejecutar binarios del sistema.

Ejemplos de logging
-------------------
Estos logs se pueden encontrar en las siguientes direcciones del repositorio en github patched_app/patched_app.log y vulnerable_app/vuln_app.log. A continuación se incluyen ejemplos reales extraídos de los ficheros de log de cada aplicación que muestran un intento de inyección por línea de comando usando `whoami`.:

- App vulnerable

<img width="951" height="390" alt="image" src="https://github.com/user-attachments/assets/f9317dcf-65f6-4543-9d7d-9f785f24dc43" />


- App parcheada
<img width="954" height="331" alt="image" src="https://github.com/user-attachments/assets/11a590b8-0df0-4b08-b927-a15dc61b0fea" />


Ambas aplicaciones detectaron la acción como sospechosa (campo `suspicious=True`), pero solo la versión parcheada evitó la ejecución del comando adicional `whoami` (la app parcheada valida el parámetro y ejecuta `ping` sin `shell=True`).


5) Comparación con la app parcheada
- La app parcheada usa consultas parametrizadas con `?` (SQLite) y pasa los parámetros separadamente. Los parámetros no se concatenan al SQL y el motor trata la entrada como dato, no como código SQL. Por eso payloads como `' OR '1'='1` no alteran la lógica de la consulta. Internamente, esto ocurre porque el primer paso de una consulta parametrizada es compilar el código de la consulta, sin tomar en cuenta el parámetro. Por tanto, el parámetro ya no puede cambiar la estructura de la consulta precompilada.
- Resultado observable: en la versión parcheada la búsqueda de `' OR '1'='1` devolverá "No hay resultados" o buscará literalmente el username con esos caracteres.

6) Pruebas funcionales rápidas
- Vulnerable app (ejemplos):
  - Entrada: alice -> devuelve usuario alice.
  - Entrada: ' OR '1'='1 -> devuelve todos los usuarios (vulnerabilidad confirmada).
- Patched app:
  - Entrada: alice -> devuelve alice.
  - Entrada: ' OR '1'='1 -> no devuelve todos; la entrada se busca literalmente, no ejecuta SQL.

Item 7 — Técnicas de prevención
---------------------------------------------------------------------------
En la siguiente sección se discuten técnicas de prevención de inyección SQL y otras medidas complementarias, con referencias a literatura científica.

Técnicas principales de prevención
- Consultas parametrizadas / prepared statements: separar código SQL de datos. Es la defensa más efectiva y recomendada.
- Validación y saneamiento de entrada: filtrar o normalizar datos de entrada; no es suficiente por sí sola, pero útil como capa adicional.
- Uso de ORM con consultas seguras: muchos ORMs generan SQL parametrizado por defecto.
- Least privilege: la cuenta de BD usada por la app debe tener permisos mínimos.
- Escapar correctamente los datos (cuando no haya parametrización), aunque es menos preferible.
- Monitoreo y detección: WAFs, detección de anomalías y registros de auditoría.

Bibliografía y referencias para cita (ejemplos académicos)
- Halfond, W. G., Viegas, J., & Orso, A. (2006). "A Classification of SQL Injection Attacks and Countermeasures". In Proceedings of the IEEE International Symposium on Secure Software Engineering. (Describen clasificación de ataques SQLi y técnicas de prevención).
- OWASP Foundation. "SQL Injection Prevention Cheat Sheet". (Guía práctica y técnica, ampliamente citada). https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
- Anley, C. (2002). "Advanced SQL Injection in SQL Server Applications". (Técnicas y análisis, clásico en la temática).
- Sudholt, S., & Strembeck, M. (2013). "Detecting SQL injection vulnerabilities using taint analysis". Journal article (explica técnicas estáticas/dinámicas para detección).

Resumen de entregables
----------------------
- `vulnerable_app/` (app vulnerable) — demuestra SQLi simple
- `patched_app/` (app parcheada) — mismo comportamiento, con consultas parametrizadas
- `REPORT.md` — respuestas y explicación de prevención con bibliografía

Fin del informe.




