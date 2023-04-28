from re import I
from flask import Flask, render_template, request, redirect, url_for
from flask_login import login_user, login_required, current_user, logout_user, LoginManager, UserMixin
from flask_mysqldb import MySQL
import bcrypt
import pandas as pd
from functools import wraps

app = Flask(__name__)
login_manager = LoginManager(app)
app.secret_key = 'my_secret_key'
 
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'cityjail'
 
mysql = MySQL(app)

class User(UserMixin):
    def __init__(self, username, power, id=None):
        self.id = id
        self.username = username
        self.power = power

    def get_power(self):
        return self.power

@login_manager.user_loader
def load_user(user_id):
    if not user_id:
        return None
    else:
        data = runStatement(f'''SELECT * FROM users WHERE username="{user_id}"''')
        user = None
        if len(data) > 0:
            user = User(username=data.iloc[0]["username"], power=data.iloc[0]["power"], id=data.iloc[0]["username"])
        return user

# if unauthorized, will automatically redirect user to login
def login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect("/")
        return func(*args, **kwargs)
    return decorated_view

# Functions for obtaining db information and verifying user. Will return a dataframe of the results
def runStatement(statement):
    cursor = mysql.connection.cursor()
    cursor.execute(statement)
    results = cursor.fetchall()
    column_names = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(results, columns=column_names)
    cursor.close()
    return df


def hashPassword(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def checkPassword(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def addUser(username, password, security_level):
    runStatement('''INSERT INTO users VALUES(%s,%s,%s)''', username, password, security_level)

def removeAlias(criminial_id, alias):
    runStatement("DELETE FROM Aliases WHERE criminal_id=%s AND alias=%s", criminial_id, alias)

def addAlias(criminal_id, alias):
    runStatement("INSERT INTO Aliases VALUES(%s,%s)", criminal_id, alias)

def changeCriminalName(criminal_id, newFirst, newLast):
    runStatement(f'UPDATE Criminals SET First="{newFirst}" AND Last="{newLast}" WHERE Criminal_ID="{criminal_id}"')

# Default route
@app.route("/")
def index():
    return render_template("login.html")

@app.route("/home")
@login_required
def home():
    crim = runStatement("SELECT * FROM criminals")
    return render_template("logged_home.html", tables=[crim.to_html(classes='data')], data=crim, power=current_user.get_power())

# When user attempts login
@app.route('/', methods=['POST'])
def login_post():
    if(request.method == "POST"):
        username = request.form.get('username')
        password = request.form.get('password')
        data = runStatement(f'''SELECT username, password, power FROM users WHERE username="{username}"''')
        if len(data) == 0:
            return render_template("login.html", error="Username or Password is Incorrect, try again!")
        elif checkPassword(password, data.iloc[0]["password"]):
            user = User(username=data.iloc[0]["username"], power=data.iloc[0]["power"], id=data.iloc[0]["username"])
            login_user(user)
            return redirect(url_for('home'))
        else:
            return render_template("login.html", error="Username or Password is Incorrect, try again!")

# When getting a criminal's information
@app.route("/criminals/<string:criminal_id>")
@login_required
def showCriminal(criminal_id):
    return render_template("criminal.html", data=runStatement("SELECT * FROM criminals WHERE criminal_id=" + criminal_id), 
                           aliases=runStatement("SELECT * FROM Alias WHERE criminal_id=" + criminal_id),
                           crimes=runStatement("SELECT * FROM Crimes WHERE criminal_id=" + criminal_id),
                           sentences=runStatement("SELECT * FROM Sentences WHERE criminal_id=" + criminal_id),
                           power=current_user.get_power())

# to search
@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    results = []
    if request.method=="POST":
        search = request.form["search"]
        searchType = request.form["search-type"]
        searchTypeDivided = searchType.split(",")
        searchTypeDivided[1] = searchTypeDivided[1].capitalize()
        filteredResults = runStatement(f"SELECT * FROM {searchTypeDivided[0]} WHERE {searchTypeDivided[1]} LIKE '{search}%'")

        for index, filteredResult in filteredResults.iterrows():
            results.append(f"<a href=/{searchTypeDivided[0]}/{filteredResult[0]}>" + filteredResult[searchTypeDivided[1]] 
                           + "<a>" + "<br>")
        results = " ".join(results)
    return render_template("search.html", results=results, searchType=searchTypeDivided[0])

#to logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

    
if __name__ == "__main__":
    app.run(debug=True)
