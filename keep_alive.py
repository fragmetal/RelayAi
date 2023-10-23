import os
import sys
import logging

from flask import Flask, render_template, make_response, request
from threading import Thread
from jinja2 import TemplateNotFound

app = Flask(__name__)

# Disable the development server warning
cli = sys.modules['flask.cli']
cli.show_server_banner = lambda *x: None

# Disable request logs
log = logging.getLogger('werkzeug')
log.disabled = True


@app.route('/')
def index():
  try:
    return render_template('index.html')
  except TemplateNotFound:
    return make_response("Template not found", 404)


def run():
  app.run(host='0.0.0.0', port=9999)


def keep_alive():
  t = Thread(target=run)
  t.start()