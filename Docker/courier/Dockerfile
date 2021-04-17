FROM python:3.7-alpine
WORKDIR /Alpaczka_app

ENV FLASK_APP courier_app.py
ENV FLASK_RUN_HOST 0.0.0.0
ENV FLASK_RUN_PORT 8882
ENV CRYPTOGRAPHY_DONT_BUILD_RUST 1

COPY ./Alpaczka_app /Alpaczka_app

RUN apk add --no-cache gcc musl-dev linux-headers openssl-dev libffi-dev
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["flask", "run", "--cert", "adhoc"]