import os
import redis
from flask import Flask, send_file, render_template, abort, redirect
from model.waybill import *
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity

app = Flask(__name__, static_url_path="")
db = redis.Redis(host="alpaczka_redis-db_1", port=6379, decode_responses=True)

FILES_PATH = "upload/waybills/"
TOKEN_EXPIRATION_TIME = 240
LOGIN_JWT_SECRET = "LOGIN_JWT_SECRET"

app.config["JWT_SECRET_KEY"] = os.environ.get(LOGIN_JWT_SECRET)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = TOKEN_EXPIRATION_TIME
app.config["JWT_TOKEN_LOCATION"] = "cookies"

jwt = JWTManager(app)


def jwt_page_unauthorized(error):
    return render_template("errors/401.html", error=error)


jwt.unauthorized_loader(jwt_page_unauthorized)


@app.route("/waybill/download/<string:waybill_hash>", methods=["GET"])
@jwt_required
def downlowad_waybill(waybill_hash):
    if get_jwt_identity() == "user" and db.exists(waybill_hash):
        filepath = os.path.join("upload/waybills/", waybill_hash + ".pdf")
        if not os.path.isfile(filepath):
            form = db.hgetall(waybill_hash)
            waybill = to_waybill(form)
            waybill.generate_and_save(
                waybill_hash, form["package_img_extension"], FILES_PATH
            )

        return send_file(filepath, attachment_filename=waybill_hash + ".pdf")
    else:
        abort(400)


@app.route("/waybill/remove/<string:waybill_hash>", methods=["GET"])
@jwt_required
def remove_waybill(waybill_hash):
    if get_jwt_identity() == "user" and db.exists(waybill_hash):
        files_key = db.hget(waybill_hash, "files_key")
        img_extension = db.hget(waybill_hash, "package_img_extension")
        db.lrem(files_key, 0, waybill_hash)
        db.delete(waybill_hash)
        filepath = os.path.join("upload/waybills/", waybill_hash + ".pdf")
        imgpath = os.path.join("upload/package_img/",
                               waybill_hash + img_extension)
        if os.path.isfile(filepath):
            os.remove(filepath)
        if os.path.isfile(imgpath):
            os.remove(imgpath)
        return redirect("https://localhost:7000/package")
    else:
        abort(400)


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


def to_waybill(form):
    sender = to_sender(form)
    recipient = to_recipient(form)

    return Waybill(sender, recipient)


def to_sender(form):
    name = form.get("sender_name")
    surname = form.get("sender_surname")
    phone = form.get("sender_phone_number")
    address = to_sender_address(form)

    return Person(name, surname, phone, address)


def to_recipient(form):
    name = form.get("recipient_name")
    surname = form.get("recipient_surname")
    phone = form.get("recipient_phone_number")
    address = to_recipient_address(form)

    return Person(name, surname, phone, address)


def to_sender_address(form):
    street = form.get("sender_street")
    city = form.get("sender_city")
    postal_code = form.get("sender_postal_code")
    country = form.get("sender_country")
    addr = Address(street, city, postal_code, country)
    return addr


def to_recipient_address(form):
    street = form.get("recipient_street")
    city = form.get("recipient_city")
    postal_code = form.get("recipient_postal_code")
    country = form.get("recipient_country")
    addr = Address(street, city, postal_code, country)
    return addr


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8881, debug=True)
