import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, session, redirect, flash
from cs50 import SQL
from datetime import date, timedelta, timezone, datetime
from werkzeug.security import generate_password_hash, check_password_hash

# create flask app
app = Flask(__name__)

# load hidden variable form the .env file
load_dotenv()

# database  & session configuration
db = SQL("sqlite:///fitness.db")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

# route for homepage
@app.route('/')
def index():
    # check if the user is logged in
    if not session.get('user_id'):
        return redirect('/login')
    
    # get protein and calorie goal for the user
    rows = db.execute("SELECT username, calorie_goal, protein_goal FROM users WHERE id = ?", session['user_id'])
    calorie_goal = rows[0]['calorie_goal']
    protein_goal = rows[0]['protein_goal']
    username = rows[0]['username']

    # get current date
    today = date.today()

    # query nutrition table and get the aggregate sum for calories and protein
    rows1 = db.execute("SELECT SUM(calories) AS total_cal, SUM(protein) AS total_protein, SUM(carbs) AS total_carbs, SUM(fats) AS total_fats FROM nutrition WHERE user_id = ? AND DATE(timestamp, '+5 hours', '+30 minutes') = DATE('now', '+5 hours', '+30 minutes')", session['user_id'])
    total_cal = rows1[0]["total_cal"] or 0
    total_protein = rows1[0]["total_protein"] or 0
    total_carbs = rows1[0]["total_carbs"] or 0
    total_fats = rows1[0]["total_fats"] or 0

    # calculate remaining cal and protein
    remaining_cal = calorie_goal - total_cal
    remaining_protein =  protein_goal - total_protein

    # calculate protein percent and calorie percent
    cal_percent_protein = min((total_protein / protein_goal) * 100, 100) if protein_goal > 0 else 0
    cal_percent_calories = min((total_cal / calorie_goal) * 100, 100) if calorie_goal > 0 else 0

    # query database to get meals from nutrition table for today
    meals_today = db.execute("SELECT id, food_name, calories, protein, carbs, fats FROM nutrition WHERE user_id = ? AND DATE(timestamp, '+5 hours', '+30 minutes') = DATE('now', '+5 hours', '+30 minutes')", session['user_id'])


    return render_template('index.html', meals_today=meals_today, cal_percent_calories=cal_percent_calories, cal_percent_protein=cal_percent_protein, today = today, username = username, remaining_cal = remaining_cal, remaining_protein = remaining_protein, calorie_goal = calorie_goal, protein_goal = protein_goal, total_cal = total_cal, total_protein = total_protein, total_carbs = total_carbs, total_fats = total_fats)

# route to log a meal
@app.route('/log', methods = ["GET", "POST"])
def log():
    # check if the user is logged in
    if not session.get('user_id'):
        return redirect('/login')

    # log a meal
    if request.method == "POST":

        # grab food name and check if user entered it
        food_name = request.form.get("food_name").strip()
        if not food_name:
            flash("must enter name for the food")
            return redirect("/log")
        
        # grab protein and calories and do safety check
        calories = request.form.get("calories")
        protein = request.form.get("protein")

        if not calories or not protein:
            flash("Calories and protein are required", "danger")
            return redirect('/log')
        
        calories = int(calories)
        protein = float(protein)

        # grab other macros
        carbs = float(request.form.get("carbs") or 0)
        fats = float(request.form.get("fats") or 0)

        # check for negative macros
        if calories < 0 or protein < 0 or carbs < 0 or fats < 0:
            flash("Macros must be positive", "danger")
            return redirect('/log')

        # get the current user id
        user_id = session["user_id"]

        # insert to database
        db.execute("INSERT INTO nutrition (user_id, food_name, calories, protein, carbs, fats) VALUES (?, ?, ?, ?, ?, ?)", user_id, food_name, calories, protein, carbs, fats)

        flash("Meal logged successfully!", "success")
        return redirect("/")
    
    else:
        return render_template("log.html")

# route to edit goals
@app.route('/editgoals', methods = ["POST"])
def editgoals():
    # check if the user is logged in
    if not session.get('user_id'):
        return redirect('/login')
    
    # grab new goals from the form
    calories_goal = request.form.get("calories_goal")
    protein_goal = request.form.get("protein_goal")

    # check if calories_goal and protein_goal is entered by user
    if not calories_goal or not protein_goal:
        flash("Must enter new goals for calories and protein")
        return redirect('/')

    # type cast calories_goal and protein_goal to int
    calories_goal = int(calories_goal)
    protein_goal = float(protein_goal)

    # check if goals are positive
    if calories_goal < 0 or protein_goal < 0:
        flash("calories and protein goals must be positive", "danger")
        return redirect("/")

    # insert new goals to the users table
    db.execute("UPDATE users SET calorie_goal = ?, protein_goal = ? WHERE id = ?", calories_goal, protein_goal, session['user_id'])

    return redirect('/')



# route for user registration
@app.route('/register', methods=["GET", "POST"])
def register():
    """Register a new user"""
    if request.method == "POST":

        # grab user data
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation_password")

        # check if user filled all details in the form
        if not username or not password or not confirmation:
            flash("Must provide all fields", "danger")
            return render_template("register.html")
        
        # check if password matches with confirmation
        if password != confirmation:
            flash("Passwords do not match", "danger")
            return render_template("register.html")
        
        # check if the username already exists
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) != 0:
            flash("Username already taken", "danger")
            return render_template("register.html")
        
        # register the user
        hash_value = generate_password_hash(password)
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash_value)

        # redirect user to homepage
        return redirect("/")
    
    else:
        return render_template('register.html')

# route for login
@app.route('/login', methods = ["GET", "POST"])
def login():
    # clear old sessions
    session.clear()

    if request.method == "POST":

        # grab user data
        username = request.form.get("username")
        password = request.form.get("password")

        # check if user exists in database
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) == 0:
            flash("user does not exist")
            return redirect('/register')
        
        # verify my user's password with hash value
        if check_password_hash(rows[0]["hash"], password):
            # start the session
            session["user_id"] = rows[0]["id"]
            flash("Login successful", "success")
            return redirect ("/")
        else:
            flash("Password is incorrect", "danger")
            return render_template("login.html")
    else:
        return render_template("login.html")

# route for logout
@app.route('/logout')
def logout():
    # clear old user id
    session.clear()
    flash("successfully logged out", "info")
    return redirect('/')

# route for deleting a meal
@app.route('/delete', methods=["POST"])
def delete():
    # check if a user is logged in
    if not session.get('user_id'):
        return redirect('/login')
    
    # grab meal id from form
    meal_id = request.form.get('meal_id')

    # delete that meal entry from database
    db.execute("DELETE FROM nutrition WHERE user_id = ? AND id = ?", session['user_id'], meal_id)

    flash("Meal Successfully deleted", "success")
    return redirect("/")

# route to show progress
@app.route('/progress')
def progress():
    # catch url parameter
    period = request.args.get('period', '7')
    days = int(period)

    # setup indian standard time to query database
    ist_offset = timedelta(hours=5, minutes=30)
    ist_timezone = timezone(ist_offset)

    # calculate how many days ago we want to query the database
    now_ist = datetime.now(ist_timezone)
    cutoff_date = (now_ist - timedelta(days=days)).strftime('%Y-%m-%d')

    # query database to calculate sum of calories for all days since cutoff date
    daily_data = db.execute("SELECT DATE(timestamp, '+5 hours', '+30 minutes') as log_date, SUM(calories) as total_cal FROM nutrition WHERE user_id = ? AND log_date >= ? GROUP BY log_date ORDER BY log_date ASC", session['user_id'], cutoff_date)

    # query database to calculate sum of each macros for all days since cutoff date
    macros = db.execute("SELECT SUM(protein) as p, SUM(carbs) as c, SUM(fats) as f FROM nutrition WHERE user_id = ? AND DATE(timestamp, '+5 hours', '+30 minutes') >= ?", session['user_id'], cutoff_date)[0]

    # extract data into simple lists
    chart_dates = [row['log_date'] for row in daily_data]
    chart_calories = [row['total_cal'] for row in daily_data]

    return render_template("progress.html", dates=chart_dates, calories=chart_calories, current_period=days, macros = macros)

if __name__ == "__main__":
    app.run(debug=True)