from flask import Flask, render_template
import requests
from random import choice
import string
import os.path
from datetime import datetime, timedelta
import time
import json
import traceback
import logging
from logging.handlers import RotatingFileHandler
from logging import Formatter


cookie_length = 32
cookie_id_filename = 'cookie.txt'
cookie_timeout = timedelta(minutes=30)
http_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
requests_timeout = 4  # timeout in seconds
logfile_location = '/var/log/mFi.log'


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

with open(os.path.join(__location__, "settings.json")) as settings_file:
    settings = json.load(settings_file)
    login_username = settings["username"]
    login_password = settings["password"]
    d = settings["devices"][0]
    device_name = d["name"]
    device_type = d["type"]
    device_ip_address = d["ip_address"]


app = Flask(__name__)
app.debug = True

# Setup logging
handler = RotatingFileHandler(logfile_location, maxBytes=1000000, backupCount=2)
handler.setLevel(logging.INFO)
handler.setFormatter(Formatter('%(asctime)s %(levelname)s: %(message)s'))
app.logger.addHandler(handler)


def generate_new_cookie_and_login():
    f = open(cookie_id_filename, 'w')
    # generate random 32-digit cookie id and write it with a timestamp to a file
    cookie_id = ''.join(choice(string.digits) for i in range(cookie_length))
    f.write(cookie_id + ' ' + str(int(time.mktime(datetime.now().timetuple()))))
    f.close()

    app.logger.info("New cookie generated. ID = %s", cookie_id)
    cookie_dict = dict(AIROS_SESSIONID=cookie_id)

    #print "dict: " + str(cookie_dict)

    login_string = 'username=' + login_username + '&password=' + login_password
    r = requests.post('http://' + device_ip_address + '/login.cgi', data=login_string, cookies=cookie_dict, headers=http_headers)

    return cookie_dict


def get_cookie_dict():
    if os.path.isfile(cookie_id_filename):
        f = open(cookie_id_filename, 'r')
        parts = f.readline().split(' ')
        f.close()

        if len(parts) >= 2:

            cookie_id = parts[0]
            timestamp = parts[1]

            delta = datetime.now() - datetime.fromtimestamp(int(timestamp))

            #print "timedelta: " + str(timedelta)
            if delta <= cookie_timeout:
                # the cookie is not too old
                #app.logger.info("Cookie age is ok")
                return dict(AIROS_SESSIONID=cookie_id)

    app.logger.info("generate new cookie")
    return generate_new_cookie_and_login()


def req(method, url, data=None, cookies=None):
    app.logger.info("Make request. Method=%s, URL=%s, data=%s, cookies=%s", method, url, data, cookies)
    r = None
    if method == "GET":
        r = requests.get(url, data=data, cookies=cookies, timeout=requests_timeout)
    elif method == "POST":
        r = requests.post(url, data=data, cookies=cookies, timeout=requests_timeout)
    elif method == "PUT":
        r = requests.put(url, data=data, cookies=cookies, timeout=requests_timeout)

    return r.json, r.status_code


def make_ubnt_request(method, url, data=None):
    cookies = get_cookie_dict()

    try:
        response_json, status_code = req(method, url, data=data, cookies=cookies)

        if 'status' in response_json and response_json['status'] == 'success':
            return response_json, status_code
    except requests.TooManyRedirects:
        app.logger.warning("Too many redirects. Cookie may be outdated.")

    app.logger.warning("request was unsuccessful: %s. Requesting new cookie.", url)
    cookies = generate_new_cookie_and_login()
    return req(method, url, data=data, cookies=cookies)


def get_sensor_data():
    response_json, status_code = make_ubnt_request("GET", 'http://' + device_ip_address + '/sensors')

    return response_json['sensors']


@app.route('/sensors/power')
def get_power_usage():
    response_json = get_sensor_data()

    res_list = list()

    for s in response_json:
        res_list.append(dict(port_id=s['port'], power=round(s['state']['power'], 2)))

    return json.dumps(res_list)


@app.route('/sensors/<int:id>/<state>')
def set_sensor_state(id, state):
    data = dict(output=state)

    response_json, status_code = make_ubnt_request("PUT", 'http://' + device_ip_address + '/sensors/' + str(id), data=data)

    return "", status_code


@app.route('/')
def index():
    try:
        data = get_sensor_data()
    except Exception as e:
        app.logger.error("Exception: %s", traceback.format_exc())
        return render_template("error.html", error_message=e.message, stack_trace=traceback.format_exc())

    return render_template('index.html', sensors=data, device_name=device_name)


if __name__ == '__main__':
    app.run()
