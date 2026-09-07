from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from pathlib import Path
from functools import wraps

BASE = Path(__file__).resolve().parent
DB_PATH = __import__('os').environ.get('DB_PATH')
DB = Path(DB_PATH) if DB_PATH else (BASE / 'school.db')
app = Flask(__name__)
app.secret_key = 'demo-secret-key-change-me'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

SCHEMA = '''
CREATE TABLE IF NOT EXISTS schools (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, city TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','teacher','student')), school_id INTEGER, first_name TEXT NOT NULL, last_name TEXT NOT NULL, FOREIGN KEY(school_id) REFERENCES schools(id));
CREATE TABLE IF NOT EXISTS subjects (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, teacher_id INTEGER, FOREIGN KEY(teacher_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS grades (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, subject_id INTEGER NOT NULL, value TEXT NOT NULL, weight INTEGER DEFAULT 1, note TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(student_id) REFERENCES users(id), FOREIGN KEY(subject_id) REFERENCES subjects(id));
CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, teacher_id INTEGER NOT NULL, kind TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(student_id) REFERENCES users(id), FOREIGN KEY(teacher_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS excuses (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, date_from TEXT NOT NULL, date_to TEXT NOT NULL, reason TEXT, status TEXT DEFAULT 'pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(student_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS announcements (id INTEGER PRIMARY KEY AUTOINCREMENT, school_id INTEGER NOT NULL, title TEXT NOT NULL, content TEXT NOT NULL, event_date TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(school_id) REFERENCES schools(id));
'''

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys = ON')
    return con

def init_db():
    con = db(); con.executescript(SCHEMA)
    if con.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0:
        con.execute("INSERT INTO schools(name,city) VALUES (?,?)", ('Liceum Demo', 'Olsztyn'))
        sid = con.execute('SELECT id FROM schools LIMIT 1').fetchone()['id']
        users = [
            ('admin','admin','admin',None,'Anna','Administrator'),
            ('nauczyciel','demo123','teacher',sid,'Jan','Kowalski'),
            ('uczen','demo123','student',sid,'Kuba','Nowak'),
            ('uczen2','demo123','student',sid,'Ola','Wiśniewska')]
        for u in users: con.execute('INSERT INTO users(username,password,role,school_id,first_name,last_name) VALUES (?,?,?,?,?,?)',u)
        tid = con.execute("SELECT id FROM users WHERE username='nauczyciel'").fetchone()['id']
        stid = con.execute("SELECT id FROM users WHERE username='uczen'").fetchone()['id']
        con.executemany('INSERT INTO subjects(name,teacher_id) VALUES (?,?)', [('Matematyka',tid),('Informatyka',tid),('Język polski',tid)])
        subs = con.execute('SELECT id,name FROM subjects').fetchall()
        con.executemany('INSERT INTO grades(student_id,subject_id,value,weight,note) VALUES (?,?,?,?,?)', [(stid,subs[0]['id'],'5',2,'Sprawdzian'),(stid,subs[1]['id'],'6',1,'Projekt'),(stid,subs[2]['id'],'4+',1,'Kartkówka')])
        con.execute('INSERT INTO notes(student_id,teacher_id,kind,content) VALUES (?,?,?,?,?)'.replace('?,?,?,?,?','?,?,?,?'), (stid,tid,'Pozytywna','Aktywna praca podczas lekcji i pomoc innym uczniom.'))
        con.execute('INSERT INTO excuses(student_id,date_from,date_to,reason,status) VALUES (?,?,?,?,?)',(stid,'2026-09-03','2026-09-04','Przeziębienie','accepted'))
        con.executemany('INSERT INTO announcements(school_id,title,content,event_date) VALUES (?,?,?,?)',[(sid,'Zebranie z rodzicami','Spotkanie odbędzie się w sali 12.','2026-09-15'),(sid,'Wycieczka klasowa','Szczegóły organizacyjne wkrótce.','2026-09-22')])
    con.commit(); con.close()

@app.context_processor
def common():
    return {'current_user': session.get('user')}

def login_required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapped(*a, **kw):
            if 'user' not in session: return redirect(url_for('login'))
            if role and session['user']['role'] != role:
                return redirect(url_for('dashboard'))
            return fn(*a, **kw)
        return wrapped
    return deco

@app.route('/')
def index(): return redirect(url_for('dashboard')) if 'user' in session else redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username, password, role = request.form['username'].strip(), request.form['password'], request.form['role']
        con=db(); u=con.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?',(username,password,role)).fetchone(); con.close()
        if u:
            session['user']=dict(u); return redirect(url_for('dashboard'))
        flash('Nieprawidłowe dane logowania lub wybrana rola.','error')
    return render_template('login.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/dashboard')
@login_required()
def dashboard():
    u=session['user']; con=db()
    if u['role']=='student':
        grades=con.execute('SELECT g.*,s.name subject FROM grades g JOIN subjects s ON s.id=g.subject_id WHERE g.student_id=? ORDER BY g.created_at DESC',(u['id'],)).fetchall()
        notes=con.execute('SELECT n.*,u.first_name||" "||u.last_name teacher FROM notes n JOIN users u ON u.id=n.teacher_id WHERE n.student_id=? ORDER BY n.created_at DESC',(u['id'],)).fetchall()
        excuses=con.execute('SELECT * FROM excuses WHERE student_id=? ORDER BY date_from DESC',(u['id'],)).fetchall()
        announcements=con.execute('SELECT * FROM announcements WHERE school_id=? ORDER BY event_date',(u['school_id'],)).fetchall()
        return render_template('student.html',grades=grades,notes=notes,excuses=excuses,announcements=announcements)
    if u['role']=='teacher':
        students=con.execute('SELECT * FROM users WHERE role="student" AND school_id=? ORDER BY last_name',(u['school_id'],)).fetchall()
        subjects=con.execute('SELECT * FROM subjects WHERE teacher_id=?',(u['id'],)).fetchall()
        announcements=con.execute('SELECT * FROM announcements WHERE school_id=? ORDER BY event_date',(u['school_id'],)).fetchall()
        return render_template('teacher.html',students=students,subjects=subjects,announcements=announcements)
    schools=con.execute('SELECT * FROM schools ORDER BY name').fetchall()
    teachers=con.execute('SELECT u.*,s.name school FROM users u LEFT JOIN schools s ON s.id=u.school_id WHERE u.role="teacher" ORDER BY u.last_name').fetchall()
    students=con.execute('SELECT u.*,s.name school FROM users u LEFT JOIN schools s ON s.id=u.school_id WHERE u.role="student" ORDER BY u.last_name').fetchall()
    return render_template('admin.html',schools=schools,teachers=teachers,students=students)

@app.route('/teacher/grade', methods=['POST'])
@login_required('teacher')
def add_grade():
    con=db(); con.execute('INSERT INTO grades(student_id,subject_id,value,weight,note) VALUES (?,?,?,?,?)',(request.form['student_id'],request.form['subject_id'],request.form['value'],request.form['weight'],request.form['note'])); con.commit(); con.close(); return redirect(url_for('dashboard'))

@app.route('/teacher/note', methods=['POST'])
@login_required('teacher')
def add_note():
    con=db(); con.execute('INSERT INTO notes(student_id,teacher_id,kind,content) VALUES (?,?,?,?)',(request.form['student_id'],session['user']['id'],request.form['kind'],request.form['content'])); con.commit(); con.close(); return redirect(url_for('dashboard'))

@app.route('/student/excuse', methods=['POST'])
@login_required('student')
def add_excuse():
    con=db(); con.execute('INSERT INTO excuses(student_id,date_from,date_to,reason) VALUES (?,?,?,?)',(session['user']['id'],request.form['date_from'],request.form['date_to'],request.form['reason'])); con.commit(); con.close(); return redirect(url_for('dashboard'))

@app.route('/admin/school', methods=['POST'])
@login_required('admin')
def add_school():
    con=db(); con.execute('INSERT INTO schools(name,city) VALUES (?,?)',(request.form['name'],request.form['city'])); con.commit(); con.close(); return redirect(url_for('dashboard'))

@app.route('/admin/user', methods=['POST'])
@login_required('admin')
def add_user():
    con=db();
    try: con.execute('INSERT INTO users(username,password,role,school_id,first_name,last_name) VALUES (?,?,?,?,?,?)',(request.form['username'],request.form['password'],request.form['role'],request.form['school_id'],request.form['first_name'],request.form['last_name'])); con.commit(); flash('Profil utworzony','ok')
    except sqlite3.IntegrityError: flash('Taki login już istnieje','error')
    con.close(); return redirect(url_for('dashboard'))

@app.route('/admin/announcement', methods=['POST'])
@login_required('admin')
def add_announcement():
    con=db(); con.execute('INSERT INTO announcements(school_id,title,content,event_date) VALUES (?,?,?,?)',(request.form['school_id'],request.form['title'],request.form['content'],request.form['event_date'])); con.commit(); con.close(); return redirect(url_for('dashboard'))

@app.route('/student/excuse/<int:eid>/delete', methods=['POST'])
@login_required('student')
def delete_excuse(eid):
    con=db(); con.execute('DELETE FROM excuses WHERE id=? AND student_id=? AND status="pending"',(eid,session['user']['id'])); con.commit(); con.close(); return redirect(url_for('dashboard'))

init_db()

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(__import__('os').environ.get('PORT', 5000)), debug=False)
