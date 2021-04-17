from flask import request, redirect, make_response, url_for
from flask import Flask, render_template, session, abort
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import redis
import uuid
import os
from flask_socketio import SocketIO, join_room, emit

from authlib.integrations.flask_client import OAuth
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    unset_jwt_cookies,
    set_access_cookies,
)

USERS = "users"
TOKEN_EXPIRATION_TIME = 240
UPLOAD_FOLDER = "upload/package_img"
SESSION_SECRET_KEY = "SESSION_SECRET_KEY"
LOGIN_JWT_SECRET = "LOGIN_JWT_SECRET"
ACTIVE_USERS_SESSIONS = "active_users_sessions"

OAUTH_BASE_URL = "https://dev-jojgo946.us.auth0.com"
OAUTH_ACCESS_TOKEN_URL = OAUTH_BASE_URL + "/oauth/token"
OAUTH_AUTHORIZE_URL = OAUTH_BASE_URL + "/authorize"
OAUTH_CALLBACK_URL = "https://localhost:7000/callback"
OAUTH_CLIENT_ID = "SIOMbb0PE5dWA8L6jnP1jj5Gbut5WeqQ"
OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET")
OAUTH_SCOPE = "openid profile"
NICKNAME = "username"

db = redis.Redis(host="alpaczka_redis-db_1", port=6379, decode_responses=True)
app = Flask(__name__, static_url_path="")

app.secret_key = os.environ.get(SESSION_SECRET_KEY)
app.permanent_session_lifetime = TOKEN_EXPIRATION_TIME

app.config["JWT_TOKEN_LOCATION"] = "cookies"
app.config["JWT_SECRET_KEY"] = os.environ.get(LOGIN_JWT_SECRET)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = TOKEN_EXPIRATION_TIME
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


socket_io = SocketIO(app, cors_allowed_origins="*")


@socket_io.on("connect")
def handle_on_connect():
    app.logger.debug("Connected -> OK")
    emit("connection response", {"data": "Correctly connected"})


@socket_io.on("join")
def handle_on_join(data):
    useragent = data['useragent']
    room_id = data['room_id']
    join_room(room_id)
    app.logger.debug("Useragent: %s added to the room: %s" %
                     (useragent, room_id))


@socket_io.on("parcel picked up")
def handle_on_parcel_picked_up(data):
    emit("refresh status", data, room="app_room")


@socket_io.on("parcels picked up from parcel locker")
def handle_on_parcels_picked_up_from_parcel_locker():
    emit("refresh", room="app_room")


@socket_io.on("parcel inserted")
def handle_on_parcel_inserted(data):
    emit("change status to inserted", data, room="app_room")


@socket_io.on("disconnect")
def handle_on_disconnect():
    app.logger.debug("Disconnected -> Bye")


jwt = JWTManager(app)
oauth = OAuth(app)

auth0 = oauth.register(
    "alpaczka-app-auth0",
    api_base_url=OAUTH_BASE_URL,
    client_id=OAUTH_CLIENT_ID,
    client_secret=OAUTH_CLIENT_SECRET,
    access_token_url=OAUTH_ACCESS_TOKEN_URL,
    authorize_url=OAUTH_AUTHORIZE_URL,
    client_kwargs={"scope": OAUTH_SCOPE})


def authorization_required(fun):
    @wraps(fun)
    def authorization_decorator(*args, **kwds):
        if "username" not in session:
            return redirect("/login")

        return fun(*args, **kwds)

    return authorization_decorator


@app.route("/", methods=["GET"])
def index():
    isLoggedUser = "username" in session
    response = make_response(render_template(
        "index.html", isLogged=isLoggedUser))
    if isLoggedUser:
        refresh_cookies(request, response)
    else:
        remove_session()
    return response


@app.route("/registration", methods=["GET", "POST"])
def registration():
    isLoggedUser = "username" in session
    if not isLoggedUser:
        if request.method == "POST":
            new_user = request.form.to_dict(flat=True)
            new_user["password"] = hashlib.sha512(
                new_user["password"].encode()
            ).hexdigest()
            new_user_hash = hashlib.sha512(
                new_user["login"].encode()).hexdigest()
            new_user["files_key"] = hashlib.sha512(
                (new_user["login"] + "_files").encode()
            ).hexdigest()
            del new_user["second_password"]
            del new_user["login"]
            db.sadd(USERS, new_user_hash)
            db.hmset(new_user_hash, new_user)
            return render_template("registration.html", registration_success=True)
        elif request.method == "GET":
            return render_template("registration.html")
    else:
        return redirect(url_for("index", isLogged=isLoggedUser))


@app.route("/oauthLogin")
def login_with_oauth():
    return auth0.authorize_redirect(
        redirect_uri=OAUTH_CALLBACK_URL,
        audience="https://alpaczka")


@app.route("/callback")
def oauth_callback():
    auth0.authorize_access_token()
    resp = auth0.get("userinfo")
    nickname = resp.json()["nickname"]
    nickname_hash = hashlib.sha512(nickname.encode()).hexdigest()
    if not db.sismember(USERS, nickname_hash):
        new_user = {"files_key": hashlib.sha512(
            (nickname + "_files").encode()).hexdigest(), }
        db.sadd(USERS, nickname_hash)
        db.hmset(nickname_hash, new_user)

    session["username"] = nickname_hash
    session.permanent = True
    session_id = "session_" + uuid.uuid4().hex
    session["session_id"] = session_id
    db.hset(ACTIVE_USERS_SESSIONS, session_id, nickname_hash)
    db.set(session_id, "active", ex=TOKEN_EXPIRATION_TIME)

    response = make_response(redirect(url_for("package")))
    access_token = create_access_token(identity="user")
    set_access_cookies(response, access_token,
                       TOKEN_EXPIRATION_TIME)
    return response


@app.route("/login", methods=["GET", "POST"])
def login():
    isLoggedUser = "username" in session
    if not isLoggedUser:
        if request.method == "POST":
            user_hash = hashlib.sha512(
                request.form["login"].encode()).hexdigest()
            password_hash = hashlib.sha512(
                request.form["password"].encode()
            ).hexdigest()
            if (
                db.sismember(USERS, user_hash)
                and db.hget(user_hash, "password") == password_hash
            ):
                session["username"] = user_hash
                session.permanent = True

                session_id = "session_" + uuid.uuid4().hex
                session["session_id"] = session_id
                db.hset(ACTIVE_USERS_SESSIONS, session_id, user_hash)
                db.set(session_id, "active", ex=TOKEN_EXPIRATION_TIME)

                response = make_response(redirect(url_for("package")))
                access_token = create_access_token(identity="user")
                set_access_cookies(response, access_token,
                                   TOKEN_EXPIRATION_TIME)
                return response
            else:
                return render_template("login.html", wrongCredentials=True)
        elif request.method == "GET":
            return render_template(
                "login.html", sessionExpired=request.args.get("sessionExpired")
            )
    else:
        return redirect(url_for("index", isLogged=isLoggedUser))


@app.route("/logout", methods=["GET"])
@authorization_required
def logout():
    isLoggedUser = "username" in session
    if isLoggedUser:
        db.delete(session["session_id"])
        db.hdel(ACTIVE_USERS_SESSIONS, session["session_id"])
        session.clear()
        url_params = "returnTo=" + \
            url_for("index", _external=True, isLogged=False)
        url_params += "&"
        url_params += "client_id=" + OAUTH_CLIENT_ID
        response = redirect(auth0.api_base_url + "/v2/logout?" + url_params)
        unset_jwt_cookies(response)
        return response
    else:
        return redirect(url_for("index", isLogged=isLoggedUser))


@app.route("/user/<username>", methods=["GET"])
def check_login_availability(username):
    users = db.smembers("users")
    username_hash = hashlib.sha512(username.encode()).hexdigest()
    if username_hash not in users:
        return make_response("login available", 404)
    else:
        return make_response("login unavailable", 200)


@app.route("/package", methods=["GET"])
@authorization_required
def package():
    isLoggedUser = "username" in session
    if isLoggedUser:

        start = int(request.args.get('start', '0'))
        limit = int(request.args.get('limit', '4'))

        files_key = db.hget(session["username"], "files_key")
        length = db.llen(files_key)

        paginated_files = db.lrange(files_key, start, start + limit - 1)
        prev_page = url_for('package', start=start-limit,
                            limit=limit) if start-limit >= 0 else None
        next_page = url_for('package', start=start+limit,
                            limit=limit) if start+limit < length else None

        parcels = [db.hgetall(parcel) for parcel in paginated_files]

        response = make_response(
            render_template("package.html", isLogged=isLoggedUser,
                            files=parcels, prev=prev_page, next=next_page, length=length)
        )
        refresh_cookies(request, response)
        return response
    else:
        remove_session()
        return make_response(
            redirect(url_for("login", isLogged=isLoggedUser, sessionExpired=True))
        )


@app.route("/package/form", methods=["GET"])
@authorization_required
def package_form():
    isLoggedUser = "username" in session
    if isLoggedUser:
        response = make_response(
            render_template("package_form.html", isLogged=isLoggedUser)
        )
        refresh_cookies(request, response)
        return response
    else:
        remove_session()
        return make_response(
            redirect(url_for("login", isLogged=isLoggedUser, sessionExpired=True))
        )


@app.route("/register_package", methods=["POST"])
@authorization_required
def register_package():
    isLoggedUser = "username" in session
    if isLoggedUser:
        response = redirect(url_for("package", isLogged=isLoggedUser))
        refresh_cookies(request, response)

        file_id = uuid.uuid4().hex
        uploaded_file = request.files["package_photo"]
        file_extension = os.path.splitext(uploaded_file.filename)[1]
        uploaded_file.save(
            os.path.join(app.config["UPLOAD_FOLDER"],
                         file_id + file_extension)
        )

        package_info = request.form.to_dict(flat=True)
        package_info["creation_date"] = (
            datetime.now() + timedelta(hours=1)
        ).strftime("%d/%m/%Y %H:%M:%S")
        package_info["package_img_extension"] = file_extension
        files_key = db.hget(session["username"], "files_key")
        package_info["files_key"] = files_key
        package_info["status"] = "nowa"
        package_info["uid"] = file_id
        db.lpush(files_key, file_id)
        db.hmset(file_id, package_info)
        return response
    else:
        remove_session()
        return make_response(
            redirect(
                url_for("login", isLogged=isLoggedUser, sessionExpired=True))
        )


@app.route("/initRedis", methods=["GET"])
def init_redis():
    if not (db.exists("couriers") and db.exists("parcel_lockers")):
        couriers = ["courier1", "courier2", "courier3", "courier4", "courier5"]
        couriers_hashes = ["courier_" + hashlib.sha512(
            courier.encode()).hexdigest() for courier in couriers]

        couriers_passwords = ["Courier1#", "Courier2#",
                              "Courier3#", "Courier4#", "Courier5#"]
        couriers_passwords_hashes = [hashlib.sha512(
            password.encode()).hexdigest() for password in couriers_passwords]

        couriers_file_keys = [uuid.uuid4().hex for i in range(0, 5)]

        parcel_lockers_ids = [uuid.uuid4().hex for i in range(0, 5)]
        parcel_lockers_names = ["Lamomat", "Futromat",
                                "Alpakomat", "Mlekomat", "Plujomat"]
        parcel_lockers_parcels_keys = [uuid.uuid4().hex for i in range(0, 5)]

        for i in range(0, 5):
            db.sadd("couriers", couriers_hashes[i])
            db.sadd("parcel_lockers", parcel_lockers_ids[i])

        i = 0
        for courier_hash in couriers_hashes:
            db.hset(courier_hash, "password", couriers_passwords_hashes[i])
            db.hset(courier_hash, "files_key", couriers_file_keys[i])
            i += 1
        i = 0
        for parcel_lockers_id in parcel_lockers_ids:
            db.hset(parcel_lockers_id, "name", parcel_lockers_names[i])
            db.hset(parcel_lockers_id, "id", parcel_lockers_id)
            db.hset(parcel_lockers_id, "parcels_key",
                    parcel_lockers_parcels_keys[i])
            i += 1

        return make_response("Poprawnie zainicjowano baze danych", 200)
    else:
        return make_response("Baza danych już zainicjowana", 200)


@app.errorhandler(400)
def page_unauthorized(error):
    return render_template("errors/400.html", error=error)


@app.errorhandler(401)
def page_unauthorized(error):
    return render_template("errors/401.html", error=error)


@app.errorhandler(403)
def page_unauthorized(error):
    return render_template("errors/403.html", error=error)


@app.errorhandler(404)
def page_unauthorized(error):
    return render_template("errors/404.html", error=error)


@app.errorhandler(500)
def page_not_found(error):
    return render_template("errors/500.html", error=error)


def refresh_cookies(request, response):
    if request.cookies.get("access_token_cookie"):
        access_token = create_access_token(identity="user")
        set_access_cookies(response, access_token, TOKEN_EXPIRATION_TIME)
        db.set(session["session_id"], "active", ex=TOKEN_EXPIRATION_TIME)


def remove_session():
    users_to_check = db.hkeys(ACTIVE_USERS_SESSIONS)
    active_users = db.keys(pattern=u"session_*")
    inactive_user = None
    for user_to_check in users_to_check:
        if user_to_check not in active_users:
            inactive_user = user_to_check
    if inactive_user:
        db.hdel(ACTIVE_USERS_SESSIONS, str(inactive_user))


if __name__ == "__main__":
    socket_io.run(app, host="0.0.0.0", port=8880, debug=True)
