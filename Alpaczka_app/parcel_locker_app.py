import redis
import hashlib
import os
from flask import Flask, render_template, abort
from flask import request, redirect, make_response, url_for
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    set_access_cookies,
    get_jwt_identity,
    jwt_required,
)

from flask_socketio import SocketIO, join_room, emit

LOGIN_JWT_SECRET = "LOGIN_JWT_SECRET"

db = redis.Redis(host="alpaczka_redis-db_1", port=6379, decode_responses=True)
app = Flask(__name__, static_url_path="")

app.config["JWT_TOKEN_LOCATION"] = "cookies"
app.config["JWT_SECRET_KEY"] = os.environ.get(LOGIN_JWT_SECRET)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 240

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


@socket_io.on("parcel inserted")
def handle_on_parcel_inserted():
    emit("refresh parcel locker parcels list", room="parcel_locker_room")


@socket_io.on("disconnect")
def handle_on_disconnect():
    app.logger.debug("Disconnected -> Bye")


jwt = JWTManager(app)


def jwt_page_unauthorized(error):
    return render_template("errors/401.html", error=error)


jwt.unauthorized_loader(jwt_page_unauthorized)


@app.route("/", methods=["GET"])
def index():
    parcel_lockers_ids = db.smembers("parcel_lockers")
    parcel_lockers = [db.hgetall(parcel_locker_id)
                      for parcel_locker_id in parcel_lockers_ids]
    response = make_response(render_template(
        "parcel_locker_app/index.html", parcel_lockers=parcel_lockers))
    return response


@app.route("/insert", methods=["GET", "POST"])
def insert():
    parcel_lockers_ids = db.smembers("parcel_lockers")
    parcel_lockers = [db.hgetall(parcel_locker_id)
                      for parcel_locker_id in parcel_lockers_ids]

    if request.method == "GET":
        return render_template("parcel_locker_app/insert.html", parcel_lockers=parcel_lockers)
    else:
        parcel_id = request.form["parcel_id"]
        if db.exists(parcel_id):
            if db.hget(parcel_id, "status") == "nowa":
                db.hset(parcel_id, "status", 'w paczkomacie')
                choosen_parcel_locker_id = request.form["parcel_lockers"]
                parcels_key = db.hget(choosen_parcel_locker_id, "parcels_key")
                db.lpush(parcels_key, parcel_id)
                return make_response(render_template("parcel_locker_app/insert.html", parcel_lockers=parcel_lockers, pickupSuccess=True))
            else:
                return make_response(render_template("parcel_locker_app/insert.html", parcel_lockers=parcel_lockers, wrongStatus=True))
        else:
            return make_response(render_template("parcel_locker_app/insert.html", parcel_lockers=parcel_lockers, wrongId=True))


@app.route("/pickup", methods=["GET", "POST"])
def pickup():
    parcel_lockers_ids = db.smembers("parcel_lockers")
    parcel_lockers = [db.hgetall(parcel_locker_id)
                      for parcel_locker_id in parcel_lockers_ids]

    if request.method == "GET":
        return render_template("parcel_locker_app/pickup.html", parcel_lockers=parcel_lockers)
    else:
        code, choosen_parcel_locker_id, courier_id = request.form[
            "code"], request.form["parcel_lockers"], "courier_" + hashlib.sha512(request.form["courier_id"].encode()).hexdigest()
        if db.sismember("couriers", courier_id):
            if code and db.exists(choosen_parcel_locker_id+code):
                response = make_response(
                    redirect(url_for("pickup_list", parcel_locker=choosen_parcel_locker_id, courier_id=courier_id)))
                access_token = create_access_token(
                    identity="courier")
                set_access_cookies(response, access_token,
                                   240)
                return response
            else:
                return render_template("parcel_locker_app/pickup.html", parcel_lockers=parcel_lockers, wrongCode=True)
        else:
            return render_template("parcel_locker_app/pickup.html", parcel_lockers=parcel_lockers, wrongCourierId=True)


@app.route("/pickupList", methods=["GET"])
@jwt_required
def pickup_list():
    if get_jwt_identity() == "courier":
        start = int(request.args.get('start', '0'))
        limit = int(request.args.get('limit', '4'))

        parcel_locker = request.args.get("parcel_locker", None)
        courier_id = request.args.get("courier_id", None)
        if parcel_locker and db.sismember("parcel_lockers", parcel_locker):
            parcels_key = db.hget(parcel_locker, "parcels_key")
            length = db.llen(parcels_key)

            paginated_files = db.lrange(parcels_key, start, start + limit - 1)
            prev_page = url_for('pickup_list', parcel_locker=parcel_locker, courier_id=courier_id, start=start-limit,
                                limit=limit) if start-limit >= 0 else None
            next_page = url_for('pickup_list', parcel_locker=parcel_locker, courier_id=courier_id, start=start+limit,
                                limit=limit) if start+limit < length else None

            parcels = [db.hgetall(parcel) for parcel in paginated_files]
            response = make_response(render_template("parcel_locker_app/pickup_parcels.html", parcel_locker=parcel_locker,
                                                     files=parcels, start=start, prev=prev_page, next=next_page, length=length))
            refresh_jwt(request, response)
            return response
        else:
            return redirect(url_for("pickup"))
    else:
        return redirect(url_for("pickup"))


@app.route("/changeStatus", methods=["POST"])
def changeStatus():
    courier_id, parcel_locker_id, parcel_id = request.json.get(
        "courier_id"), request.json.get("parcel_locker_id"), request.json.get("parcel_id")
    parcel_locker_parcels_key, courier_parcels_key = db.hget(
        parcel_locker_id, "parcels_key"), db.hget(courier_id, "files_key")
    db.lrem(parcel_locker_parcels_key, 1, parcel_id)
    db.hset(parcel_id, "status", 'odebrana z paczkomatu')
    db.lpush(courier_parcels_key, parcel_id)
    return make_response("OK", 200)


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


def refresh_jwt(request, response):
    if request.cookies.get("access_token_cookie"):
        access_token = create_access_token(identity="courier")
        set_access_cookies(response, access_token, 240)


if __name__ == "__main__":
    socket_io.run(app, host="0.0.0.0", port=8883, debug=True)
