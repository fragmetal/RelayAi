import os
import logging
from flask import Flask, render_template, make_response, request
from threading import Thread

app = Flask(__name__)

# Set the Flask logger to log only messages at WARNING level or higher
app.logger.setLevel(logging.WARNING)

# Configure the Werkzeug logger to log only messages at WARNING level or higher
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)


@app.route('/')
def index():
  return "Alive"


@app.after_request
def after_request(response):
  if request.method == 'OPTIONS':
    response = make_response()
  return response


def run():
  app.run(host='0.0.0.0', port=8080)


def keep_alive():
  t = Thread(target=run)
  t.start()


if __name__ == "__main__":
  keep_alive()
