from flask import Flask, render_template, request, redirect, session, jsonify
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = "secret123"

# DB CONNECTION
def get_db():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME"),
        port=int(os.environ.get("DB_PORT")),
        connection_timeout=5
    )

@app.route('/')
def home():
    return render_template('home.html')

# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (request.form['email'], request.form['password'])
        )
        user = cursor.fetchone()
        db.close()

        if user:
            session['user_id'] = user['id']
            session['user'] = user['name']
            return redirect('/dashboard')
        else:
            error = "Invalid credentials"

    return render_template('login.html', error=error)

# REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s,%s,%s)",
            (request.form['name'], request.form['email'], request.form['password'])
        )
        db.commit()
        db.close()

        return redirect('/login')

    return render_template('register.html')

# DASHBOARD
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('dashboard.html', user=session['user'])

# REPORT
@app.route('/report', methods=['GET','POST'])
def report():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """INSERT INTO items 
            (item_name, location, date_reported, description, type, user_id)
            VALUES (%s,%s,%s,%s,%s,%s)""",
            (
                request.form['item_name'],
                request.form['location'],
                request.form['date'],
                request.form['description'],
                request.form['type'],
                session['user_id']
            )
        )

        db.commit()
        db.close()
        return redirect('/dashboard')

    return render_template('report.html')

# SEARCH PAGE
@app.route('/search')
def search():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('search.html')

# SEARCH API
@app.route('/search_items')
def search_items():
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify([])

    db = get_db()
    cursor = db.cursor(dictionary=True)

# MAIN QUERY ------------------------------
    cursor.execute("""
    SELECT i.*
    FROM items i
    LEFT JOIN claims c ON i.id = c.item_id
    WHERE LOWER(i.item_name) LIKE %s
    AND LOWER(i.type) = 'found'
    AND c.item_id IS NULL
""", (f"%{query.lower()}%",))

    data = cursor.fetchall()
    db.close()

    return jsonify(data)

# CLAIM
@app.route('/claim/<int:item_id>')
def claim(item_id):
    if 'user_id' not in session:
        return redirect('/login')

    db = get_db()
    cursor = db.cursor()

    # check if already claimed
    cursor.execute("SELECT * FROM claims WHERE item_id=%s", (item_id,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO claims (item_id, user_id) VALUES (%s,%s)",
            (item_id, session['user_id'])
        )
        db.commit()

    db.close()
    return redirect('/search')

# MY ITEMS
@app.route('/my_items')
def my_items():
    if 'user_id' not in session:
        return redirect('/login')

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM items WHERE user_id=%s",(session['user_id'],))
    data = cursor.fetchall()
    db.close()

    return render_template('my_items.html', items=data)

# MY CLAIMS
@app.route('/my_claims')
def my_claims():
    if 'user_id' not in session:
        return redirect('/login')

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT i.item_name, i.location, i.description
        FROM claims c
        JOIN items i ON c.item_id = i.id
        WHERE c.user_id = %s
    """, (session['user_id'],))

    data = cursor.fetchall()
    db.close()

    return render_template('my_claims.html', claims=data)

# PROFILE
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect('/login')

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT name, email FROM users WHERE id=%s", (session['user_id'],))
    user = cursor.fetchone()

    db.close()

    return render_template('profile.html', user=user)
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == "__main__":
    app.run(debug=True)
