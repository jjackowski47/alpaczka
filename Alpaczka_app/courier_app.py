from functools import wraps
import os
import redis
import hashlib
import random
import uuid
from flask import Flask, render_template, session
from flask import request, redirect, make_response, url_for
from authlib.integrations.flask_client import OAuth

from flask_socketio import SocketIO, join_room, emit

db = redis.Redis(host="alpaczka_redis-db_1", port=6379, decode_responses=True)
app = Flask(__name__, static_url_path="")

SESSION_SECRET_KEY = "SESSION_SECRET_KEY"
app.secret_key = os.environ.get(SESSION_SECRET_KEY)
app.permanent_session_lifetime = 240

OAUTH_BASE_URL = "https://dev-jojgo946.us.auth0.com"
OAUTH_ACCESS_TOKEN_URL = OAUTH_BASE_URL + "/oauth/token"
OAUTH_AUTHORIZE_URL = OAUTH_BASE_URL + "/authorize"
OAUTH_CALLBACK_URL = "https://localhost:7002/callback"
OAUTH_CLIENT_ID = "M9isfJfdlr0sw09JnHV0kLIlSeEKfxd9"
OAUTH_CLIENT_SECRET = 'TZmEZR7ICKdNBZ3U3LnoP-rXmBU-Z1OmAMiubOO8SHGIVS_NsR9IDIbPxswnPbkR'
OAUTH_SCOPE = "openid profile"
NICKNAME = "couriername"

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
def handle_on_parcel_picked_up():
    emit("refresh", room="courier_room")


@socket_io.on("parcels picked up from parcel locker")
def handle_on_parcels_picked_up_from_parcel_locker():
    emit("refresh", room="courier_room")


@socket_io.on("disconnect")
def handle_on_disconnect():
    app.logger.debug("Disconnected -> Bye")


oauth = OAuth(app)
auth0 = oauth.register(
    "alpaczka-courier-app-auth0",
    api_base_url=OAUTH_BASE_URL,
    client_id=OAUTH_CLIENT_ID,
    client_secret=OAUTH_CLIENT_SECRET,
    access_token_url=OAUTH_ACCESS_TOKEN_URL,
    authorize_url=OAUTH_AUTHORIZE_URL,
    client_kwargs={"scope": OAUTH_SCOPE})


def authorization_required(fun):
    @wraps(fun)
    def authorization_decorator(*args, **kwds):
        if "couriername" not in session:
            return redirect("/login")

        return fun(*args, **kwds)

    return authorization_decorator


@app.route("/service-worker.js")
def service_worker():
    return app.send_static_file("service-worker.js")


@app.route("/offline")
def offline():
    return render_template("offline.html")


@app.route("/error")
def error():
    return render_template("pwa_error.html")


@app.route("/", methods=["GET"])
def index():
    isLoggedCourier = "couriername" in session
    if isLoggedCourier:
        return redirect(url_for("parcels"))
    else:
        return redirect(url_for("login"))


@app.route("/oauthLogin")
def login_with_oauth():
    return auth0.authorize_redirect(
        redirect_uri=OAUTH_CALLBACK_URL,
        audience="https://alpaczka")


@app.route("/login", methods=["GET", "POST"])
def login():
    isLoggedCourier = "couriername" in session
    if request.method == "POST":
        login_hash = "courier_" + \
            hashlib.sha512(request.form["login"].encode()).hexdigest()
        password_hash = hashlib.sha512(
            request.form["password"].encode()).hexdigest()
        if (db.sismember("couriers", login_hash) and password_hash == db.hget(login_hash, "password")):
            session["couriername"] = login_hash
            session.permanent = True
            return redirect(url_for("parcels"))
        else:
            return redirect(url_for("login"))
    else:
        return render_template("courier_app/login.html", isLogged=isLoggedCourier)


@app.route("/callback")
def oauth_callback():
    auth0.authorize_access_token()
    resp = auth0.get("userinfo")
    nickname = resp.json()["nickname"]
    nickname_hash = "courier_" + hashlib.sha512(nickname.encode()).hexdigest()
    if not db.sismember('couriers', nickname_hash):
        new_user = {"files_key": uuid.uuid4().hex, }
        db.sadd('couriers', nickname_hash)
        db.hmset(nickname_hash, new_user)

    session["couriername"] = nickname_hash
    session.permanent = True
    session_id = "session_" + uuid.uuid4().hex
    session["session_id"] = session_id

    return make_response(redirect(url_for("parcels")))


@app.route("/pickup", methods=["GET", "POST"])
@authorization_required
def pickup():
    isLoggedCourier = "couriername" in session
    if isLoggedCourier:
        if request.method == "GET":
            return make_response(render_template(
                "courier_app/pickup.html", isLogged=isLoggedCourier))
        else:
            parcel_id = request.form["parcel_id"]
            if db.exists(parcel_id):
                if db.hget(parcel_id, "status") == "nowa":
                    files_key = db.hget(session["couriername"], "files_key")
                    db.hset(parcel_id, "status", 'przekazana')
                    db.lpush(files_key, parcel_id)
                    return make_response(render_template("courier_app/pickup.html", pickupSuccess=True, isLogged=isLoggedCourier))
                else:
                    return make_response(render_template("courier_app/pickup.html", wrongStatus=True, isLogged=isLoggedCourier))
            else:
                return make_response(render_template("courier_app/pickup.html", wrongId=True, isLogged=isLoggedCourier))
    else:
        return redirect(url_for("login"))


@app.route("/parcels", methods=["GET"])
@authorization_required
def parcels():
    isLoggedCourier = "couriername" in session
    if isLoggedCourier:
        start = int(request.args.get('start', '0'))
        limit = int(request.args.get('limit', '4'))

        files_key = db.hget(session["couriername"], "files_key")
        length = db.llen(files_key)

        paginated_files = db.lrange(files_key, start, start + limit - 1)
        prev_page = url_for('parcels', start=start-limit,
                            limit=limit) if start-limit >= 0 else None
        next_page = url_for('parcels', start=start+limit,
                            limit=limit) if start+limit < length else None

        parcels = [db.hgetall(parcel) for parcel in paginated_files]

        return make_response(render_template(
            "courier_app/parcels.html", isLogged=isLoggedCourier, files=parcels, start=start, prev=prev_page, next=next_page, length=length))
    else:
        return redirect(url_for("login"))


@app.route("/generateCode", methods=["GET", "POST"])
@authorization_required
def generate_code():
    parcel_lockers_ids = db.smembers("parcel_lockers")
    parcel_lockers = [db.hgetall(parcel_locker_id)
                      for parcel_locker_id in parcel_lockers_ids]
    isLoggedCourier = "couriername" in session
    if isLoggedCourier:
        if request.method == "GET":
            return render_template("courier_app/generateCode.html", isLogged=isLoggedCourier, parcel_lockers=parcel_lockers)
        else:
            parcel_locker_id = request.form["parcel_locker_id"]
            if db.sismember("parcel_lockers", parcel_locker_id):
                code = str(random.randint(0, 999999)).zfill(6)
                db.set(parcel_locker_id+code, "active_code", ex=60)
                return render_template("courier_app/generateCode.html", isLogged=isLoggedCourier, code=code, parcel_lockers=parcel_lockers)
            else:
                return render_template("courier_app/generateCode.html", isLogged=isLoggedCourier, wrongLockerId=True, parcel_lockers=parcel_lockers)
    else:
        return redirect(url_for("login"))


@ app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    url_params = "returnTo=" + url_for("login", _external=True, isLogged=False)
    url_params += "&"
    url_params += "client_id=" + OAUTH_CLIENT_ID
    return redirect(auth0.api_base_url + "/v2/logout?" + url_params)


@ app.errorhandler(400)
def page_unauthorized(error):
    return render_template("errors/400.html", error=error)


@ app.errorhandler(401)
def page_unauthorized(error):
    return render_template("errors/401.html", error=error)


@ app.errorhandler(403)
def page_unauthorized(error):
    return render_template("errors/403.html", error=error)


@ app.errorhandler(404)
def page_unauthorized(error):
    return render_template("errors/404.html", error=error)


@ app.errorhandler(500)
def page_not_found(error):
    return render_template("errors/500.html", error=error)


if __name__ == "__main__":
    socket_io.run(app, host="0.0.0.0", port=8882, debug=True)
