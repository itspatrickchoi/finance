import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

import datetime

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


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # ok, none of the print messages happen inside the if and else...wtf..
    if request.method == "POST":
        print("homiee")
        return apology("POST TODO")
    else:
        print("homeeeee")

        # create own list i guess with all information for table

        users_stocks = db.execute("SELECT * FROM users_stocks WHERE user_id = ?", session["user_id"])

        stocks_value = 0

        lookups = [None] * len(users_stocks) # I CANNOT do just lookups = [{}] because in for-loop I can't assign anything to the ith dictionary because it doesn't exist yet, took me over an hour, goddamn! Didn't come up yesterday when I only had one dictionary in the list. Stackoverflow saved me.
        for i in range(len(users_stocks)):
            lookups[i] = lookup(users_stocks[i]['stock'])
            lookups[i]['total'] = lookup(users_stocks[i]['stock'])['price'] * users_stocks[i]['shares']
            stocks_value += lookups[i]['total']

        print(lookups)
        # OH FCK, I think I need to add user_id as foreign key to companies table...or wait..sketch schema again..

        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]['cash']
        grandtotal = cash + stocks_value

        return render_template("index.html", lookups=lookups, cash=cash, grandtotal=grandtotal)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        quote = lookup(request.form.get("symbol"))

        # Ensures symbol entered
        if not request.form.get("symbol"):
            return apology("missing symbol", 400)
        # Ensures shares field is filled and not negative
        elif not request.form.get("shares"):        # or int(request.form.get("shares")) < 0:  #actually better to make field in html non-negative by setting min=1
            return apology("missing shares", 400)
        elif type(request.form.get("shares")) != int:
            print(type(request.form.get("shares")))
            return apology("invalid shares", 400)

        # HOW TO STOP FRACTIONAL BUT ALLOW 112.0??

        # Ensures symbol is valid
        elif quote is None:
            return apology("Invalid symbol", 400)

        name = quote['name']
        price = float(quote['price'])
        symbol = quote['symbol']
        shares = float(request.form.get("shares"))

        current_time = datetime.datetime.now().strftime("%x, %X")
        print("this is the time: " + str(current_time))

        # ----------->> AH, NOT create table here but in sqlite3 finance.db in the terminal instead

        # cash = db.execute("SELECT cash FROM users")
        # print(cash)
        # print(cash[1]['cash']) # cash of 2nd username in list
        cash = db.execute("SELECT cash FROM users where id = ?", session["user_id"])
        cash = cash[0]['cash']
        print(cash)
        print(price*shares)

        if cash < (price*shares):
            return apology("not enough cash", 400)
        cash -= price * shares
        print(cash)

        # update new cash value of user
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"])

        # add new entry to transactions by user
        db.execute("INSERT INTO transactions (user_id, stock, shares, datetime, price) VALUES (?, ?, ?, ?, ?)", session["user_id"], symbol, shares, current_time, price)

        # if user does not own that stock in his portfolio yet, add it into the table
        if not db.execute("SELECT * FROM users_stocks WHERE user_id = ? AND stock = ?", session["user_id"], symbol):
            db.execute("INSERT INTO users_stocks (user_id, stock, shares) VALUES (?, ?, ?)", session["user_id"], symbol, shares)
        # else just update the new share count of the stock he owns in his portfolio
        else:
            shares_owned = db.execute("SELECT shares FROM users_stocks WHERE user_id = ? AND stock = ?", session["user_id"], symbol)
            print(shares_owned)
            print(type(shares_owned))
            db.execute("UPDATE users_stocks SET shares = ? WHERE user_id = ? AND stock = ?", shares_owned[0]['shares']+shares, session["user_id"], symbol)

        return redirect("/")

    else:
        return render_template("buy.html")

    # Finally finished with buy()!!! after a whole week and clocking ~24 hours!! And current status is all checks in check50 are fulfilled except the sell() which I haven't implemented yet. And of buy() the "handles valid purchase, expected to find "112.00" in page"


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    history = db.execute("SELECT * FROM transactions WHERE user_id = ?", session["user_id"])
    print(history)
    rows_history = len(history)
    print(rows_history)
    return render_template("history.html", history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        print("user logged in: " + str(session["user_id"]))

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        quote = lookup(request.form.get("symbol"))
        if quote is None:
            return apology("Invalid symbol", 400)
        name = quote['name']
        price = quote['price']
        symbol = quote['symbol']
        print(quote)
        print(price)
        return render_template("quoted.html", name=name, symbol=symbol, price=price)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # TODO
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # get a list of existant usernames,...experimentation
        # usernames = db.execute("SELECT username FROM users WHERE username = ?", request.form.get("username"))
        # print(usernames)
        # print("hello" + str(usernames[0])) # instead of username['name']


        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure username does not already exist
        elif db.execute("SELECT username FROM users WHERE username = ?", request.form.get("username")): # ah yes, after 38 minutes or so I solved this one too, seemingly
            # print("hello")
            return apology("this username already exists", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure password confirmation
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("password confirmation doesn't match", 400)

        # Hash valid password of user
        username = request.form.get("username")
        password = request.form.get("password")
        hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)

        # Insert user and password to the user table
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash)

        return redirect("/") # or render_template("login.html", 200) or redirect("/login")

    else:
        return render_template("register.html")

    # relatively easy and smooth, after around 1 hour, I got it mostly. Had to figure out how to make "username already exists" without internal server error for like 38 minutes
    # or maybe not fully solved, coz check50 still doesn't think "registration rejects duplicate username" is fulfilled...


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method = "POST":
        
        quote = lookup(request.form.get("symbol"))

        name = quote['name']
        price = float(quote['price'])
        symbol = quote['symbol']
        shares = float(request.form.get("shares"))

        current_time = datetime.datetime.now().strftime("%x, %X")
        print("this is da time: " + str(current_time))

        shares_owned = db.execute("SELECT shares FROM users_stocks where user_id = ? AND stock = ?", session["user_id"], symbol)
        shares_owned = shares_owned[0]['shares']
        print(shares_owned)

        if cash < (price*shares):
            return apology("not enough cash", 400)
        cash -= price * shares
        print(cash)

        # update new cash value of user
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"])

        # add new entry to transactions by user
        db.execute("INSERT INTO transactions (user_id, stock, shares, datetime, price) VALUES (?, ?, ?, ?, ?)", session["user_id"], symbol, shares, current_time, price)

        # if user does not own that stock in his portfolio yet, add it into the table
        if not db.execute("SELECT * FROM users_stocks WHERE user_id = ? AND stock = ?", session["user_id"], symbol):
            db.execute("INSERT INTO users_stocks (user_id, stock, shares) VALUES (?, ?, ?)", session["user_id"], symbol, shares)
        # else just update the new share count of the stock he owns in his portfolio
        else:
            shares_owned = db.execute("SELECT shares FROM users_stocks WHERE user_id = ? AND stock = ?", session["user_id"], symbol)
            print(shares_owned)
            print(type(shares_owned))
            db.execute("UPDATE users_stocks SET shares = ? WHERE user_id = ? AND stock = ?", shares_owned[0]['shares']+shares, session["user_id"], symbol)
        
        return redirect("/")
    return apology("TODO")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
