import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import datetime

from helpers import apology, login_required, send_email

import os



# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True



# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response




# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///card.db")

@app.route("/", methods = ["GET", "POST"])
@login_required
def index():

    #If the user presses a button on the index page, it will bring them to a different page.
    if request.method == "POST":
        if request.form.get("button") == "create":
            return redirect("/create")
        elif request.form.get("button") == "approval":
            return redirect("/approval")
    #For the Get method, the Jinja HTML page checks if the user_id of the current user matches either Eura or Shelly's account. If it does, the approve applications button will appear so Eura and Shelly can approve VIP applications.
    else:
        name = db.execute("SELECT firstname FROM users WHERE id = ?", session["user_id"])[0]["firstname"]
        shelly_id = db.execute("SELECT id FROM users WHERE firstname LIKE UPPER(?) AND lastname LIKE UPPER(?)", "%shelly%", "%liu%")[0]["id"]
        eura_id = db.execute("SELECT id FROM users WHERE firstname LIKE UPPER(?) AND lastname LIKE UPPER(?)", "%eura%", "%choi%")[0]["id"]

        # This is the code that we used to put the card templates into the database. We commented it out because we no longer need it.
        # html_card = """
        # <html>
        #     <body>
        #         <h2 style="color: #E8889D; text-align: center;">Happy Birthday {friend_name}!</h2>
        #         <img src="{image}" style="display: block; margin: auto;" />
        #         <h3 style="color: #E8889D; text-align: center;">{message}</h3>
        #         <h3 style="color: #E8889D; text-align: center;">From, {name}</h4>
        #     </body>
        # </html>
        # """

        # text_card = """
        # Happy Birthday {friend_name}!
        # {message}
        # From, {name}
        # """

        # db.execute("INSERT INTO templates(name, html, text) VALUES (?, ?, ?)", "VIP Card", html_card, text_card)

        return render_template("index.html", name=name, shelly_id = shelly_id, eura_id = eura_id)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)


        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        usernames = []

        for i in db.execute("SELECT username FROM users"):
            usernames.append(i["username"])

        if not request.form.get("username"):
            return apology("must provide username", 400)

        if not request.form.get("firstname"):
            return apology("must provide first name", 400)

        if not request.form.get("lastname"):
            return apology("must provide last name", 400)

        elif request.form.get("username") in usernames:
            return apology("username is already taken", 400)

        elif not request.form.get("password"):
            return apology("must provide password", 400)

        elif not request.form.get("email"):
            return apology("must provide email", 400)

        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("password fields don't match", 400)

        username = request.form.get("username")
        password = request.form.get("password")

        firstname = request.form.get("firstname")
        lastname = request.form.get("lastname")
        email = request.form.get("email")

        p_hash = generate_password_hash(password)

        db.execute("INSERT INTO users (username, hash, firstname, lastname, email) VALUES (?, ?, ?, ?, ?)", username, p_hash, firstname, lastname, email)

        return redirect("/login")

    else:

        return render_template("register.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/create", methods = ["GET", "POST"])
@login_required
def create():

    if request.method == "POST":

        friend = request.form.get("friend")
        template = request.form.get("template")
        message = request.form.get("message")

        #In order to send an email to the friend, we must retrieve the friend's email from the friend table of card.db
        friend_email = db.execute("SELECT email FROM friends WHERE firstname = ? AND user_id = ?", friend, session["user_id"])[0]["email"]

        name = db.execute("SELECT firstname FROM users WHERE id = ? ", session["user_id"])[0]["firstname"]

        #These SQL commands select the HTML and the plaintext strings of the card that the user chose
        text = db.execute("SELECT text FROM templates WHERE name = ?", template)[0]["text"]
        html = db.execute("SELECT html FROM templates WHERE name = ?", template)[0]["html"]

        #Using string.format, we input personalized elements into the HTML and plaintext emails such as the friend's name and the user's name. For VIP users, we also include the image URL into the card HTML so the image that the user wants is included in the card.
        if request.form.get("image"):
            image = request.form.get("image")
            send_email(friend_email, "Happy Birthday!", text.format(friend_name = friend, name = name, message = message), html.format(friend_name = friend, name = name, message = message, image = image))
        else:
            send_email(friend_email, "Happy Birthday!", text.format(friend_name = friend, name = name, message = message), html.format(friend_name = friend, name = name, message = message))

        return redirect("/")
    else:

        #This selects the friend's firstnames and the templates of the cards from the database so that the select field in the form of the create card page has the different options
        friends = [f["firstname"] for f in db.execute("SELECT firstname FROM friends WHERE user_id = ?", session["user_id"])]
        templates = [t["name"] for t in db.execute("SELECT name FROM templates")]

        vip_id = [v["id"] for v in db.execute("SELECT id FROM users WHERE vip = 1")]

        #If the user is a VIP member, an extra option for the VIP template is added to the select field
        if (session["user_id"] in vip_id):
            return render_template("create.html", friends = friends, templates = templates, vip_id = vip_id)
        else:
            templates.remove("VIP Card")
            return render_template("create.html", friends = friends, templates = templates, vip_id = vip_id)

@app.route("/friend", methods = ["GET", "POST"])
@login_required
def friend():

    if request.method == "POST":

        firstname = request.form.get("firstname")
        lastname = request.form.get("lastname")
        month = request.form.get("month")
        day = request.form.get("day")
        year = request.form.get("year")
        email = request.form.get("email")

        db.execute("INSERT INTO friends (user_id, firstname, lastname, month, day, year, email) VALUES (?, ?, ?, ?, ?, ?, ?)", session["user_id"], firstname, lastname, month, day, year, email)

        return redirect("/")


    else:

        return render_template("friend.html")

@app.route("/calendar", methods = ["GET"])
@login_required
def calendar():
    #Retrieve user's friends' birthdays
    birthdays = db.execute("SELECT firstname, lastname, month, day, year FROM friends WHERE user_id = ?", session["user_id"])
    calendar = []
    #Loop through the information to configure information retrieved into format accepted by calendar code
    for i in birthdays:
        event = i["firstname"] + " " + i["lastname"]
        if datetime.datetime.today().month > i["month"]:
            date = datetime.datetime(datetime.datetime.today().year + 1, i["month"], i["day"]).strftime("%Y-%m-%d")
        else:
            date = datetime.datetime(datetime.datetime.today().year, i["month"], i["day"]).strftime("%Y-%m-%d")
        calendar.append({"title": event, "start": date, "allDay" : True})
    print(calendar)
    #Return user to calendar site
    return render_template("calendar.html", birthdays = calendar)

@app.route("/templates", methods = ["GET"])
@login_required
def templates():
    vip_id = [v["id"] for v in db.execute("SELECT id FROM users WHERE vip = 1")]
    return render_template("templates.html", vip_id = vip_id)

#code taken from https://blog.miguelgrinberg.com/post/handling-file-uploads-with-flask
@app.route('/vip', methods=['GET','POST'])
def vip():
    if request.method == "POST":
        #This part of our code is adapted from https://blog.miguelgrinberg.com/post/handling-file-uploads-with-flask for inserting and submitting images
        uploaded_file = request.files['file']
        if uploaded_file.filename != '':
            uploaded_file.save("./submissions/" + uploaded_file.filename)
        firstname = db.execute("SELECT firstname FROM users WHERE id = ?", session["user_id"])[0]["firstname"]
        lastname = db.execute("SELECT lastname FROM users WHERE id = ?", session["user_id"])[0]["lastname"]
        #This creates the email to yaybirthdaycards telling us that someone submitted a VIP application
        html="""
        <html>
            <body>
                <h1>{firstname} {lastname} has submitted a request to become a VIP member! Their submission file name is {filename} </h1>
            </body>
        </html>
        """
        text="""
        {firstname} {lastname} has submitted a request to become a VIP member! Their submission file name is {filename}
        """
        send_email("yaybirthdaycards@gmail.com", "New VIP Submission", text.format(firstname = firstname, lastname = lastname, filename = uploaded_file.filename), html.format(firstname = firstname, lastname = lastname, filename = uploaded_file.filename))

        return redirect("/")
    else:
        return render_template("vip.html")

@app.route('/approval', methods=['GET','POST'])
def approval():
    if request.method == "POST":
        user = request.form.get("users")

        #Changes the status of the user to be a VIP
        db.execute("UPDATE users SET vip=1 WHERE firstname = ?", user)

        #This creates the email telling the user that their VIP application was approved
        email = db.execute("SELECT email FROM users WHERE firstname = ?", user)[0]["email"]
        html="""
        <html>
            <body>
                <h1 style = "color: #E8889D; text-align: center;">Congratulations! Your request to become a VIP member of Birthday Cards has been approved!</h1>
            </body>
        </html>
        """
        text="""
            Congratulations! Your request to become a VIP member of Birthday Cards has been approved!
        """
        send_email(email, "Congratulations!", text, html)

        return redirect("/")
    else:
        #Displays all the users of our website
        users = [u["firstname"] for u in db.execute("SELECT firstname FROM users")]
        return render_template("approval.html", users=users)