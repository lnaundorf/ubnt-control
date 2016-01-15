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
import ServerManager


cookie_length = 32
cookie_id_filename = 'cookie.txt'
cookie_timeout = timedelta(minutes=30)
http_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
requests_timeout = 4  # timeout in seconds
logfile_location = '/var/log/mFi.log'

devices = dict()


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

with open(os.path.join(__location__, "settings.json")) as settings_file:
    settings = json.load(settings_file)
    login_username = settings["username"]
    login_password = settings["password"]

    for d in settings["devices"]:
        if d["name"]:
            devices[d["name"]] = d

    print "devices read from settings file:"
    print str(devices)


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

    for dev in devices.itervalues():
        if dev["type"] == "power_cord":
            r = requests.post('http://' + dev["ip_address"] + '/login.cgi', data=login_string, cookies=cookie_dict, headers=http_headers)

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
    app.logger.debug("Make request. Method=%s, URL=%s, data=%s, cookies=%s", method, url, data, cookies)
    r = None
    if method == "GET":
        r = requests.get(url, data=data, cookies=cookies, timeout=requests_timeout)
    elif method == "POST":
        r = requests.post(url, data=data, cookies=cookies, timeout=requests_timeout)
    elif method == "PUT":
        r = requests.put(url, data=data, cookies=cookies, timeout=requests_timeout)

    return r.json(), r.status_code


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


def get_power_coord_data(ip_address, only_port_id=None):
    response_json, status_code = make_ubnt_request("GET", 'http://' + ip_address + '/sensors')

    if not only_port_id:
        return response_json['sensors']
    else:
        for sensor in response_json['sensors']:
            if sensor['port'] == only_port_id:
                return sensor['output']
        return ""


def get_sensor_data():
    res = list()

    for dev in devices.itervalues():
        dev_data = dict()
        dev_data["name"] = dev["name"]
        dev_data["type"] = dev["type"]

        if dev["type"] == "power_cord":
            dev_data["data"] = get_power_coord_data(dev["ip_address"])
        elif dev["type"] == "server":
            dev_data["data"] = {'output': ServerManager.server_is_up(dev["ip_address"])}

        res.append(dev_data)

    return res


@app.route('/sensors/power')
def get_power_usage():
    return json.dumps(get_sensor_data())


@app.route('/<name>/sensors/<int:id>/')
def get_single_sensor_state(name, id, state):
    dev = devices.get(name, None)

    if dev is not None:
        return get_power_coord_data(dev["ip_address"], only_port_id=id)
    else:
        return ""


@app.route('/<name>/sensors/<int:id>/<int:state>')
def set_sensor_state(name, id, state):
    data = dict(output=state)

    dev = devices.get(name, None)

    if dev is not None:
        if dev["type"] == "power_cord":
            response_json, status_code = make_ubnt_request("PUT", 'http://' + dev["ip_address"] + '/sensors/' + str(id), data=data)
        elif dev["type"] == "server":
            status_code = 200
            if state == 1:
                # start server via wake on lan
                ServerManager.wake_on_lan(dev['mac_address'])
            elif state == 0:
                # shutdown server via ssh
                print "shutdown"
                ServerManager.shutdown(dev['ip_address'], dev['ssh_username'], dev['ssh_password'])


    return "", status_code


@app.route('/')
def index():
    try:
        devices = get_sensor_data()
    except Exception as e:
        app.logger.error("Exception: %s", traceback.format_exc())
        return render_template("error.html", error_message=e.message, stack_trace=traceback.format_exc())

    return render_template('index.html', devices=devices)


if __name__ == '__main__':
    app.run()
