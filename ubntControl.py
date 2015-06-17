from flask import Flask, render_template
import requests
from random import choice
import string
import os.path
from datetime import datetime, timedelta
import time
import json
import traceback

cookie_length = 32
cookie_id_filename = 'cookie.txt'
cookie_timeout = timedelta(hours=1)
http_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
requests_timeout = 4  # timeout in seconds

with open("settings.json") as settings_file:
    settings = json.load(settings_file)
    login_username = settings["username"]
    login_password = settings["password"]
    d = settings["devices"][0]
    device_name = d["name"]
    device_type = d["type"]
    device_ip_address = d["ip_address"]



app = Flask(__name__)
app.debug = True


def generate_new_cookie_and_login():
    f = open(cookie_id_filename, 'w')
    # generate random 32-digit cookie id and write it with a timestamp to a file
    cookie_id = ''.join(choice(string.digits) for i in range(cookie_length))
    f.write(cookie_id + ' ' + str(int(time.mktime(datetime.now().timetuple()))))
    f.close()

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
                return dict(AIROS_SESSIONID=cookie_id)

    return generate_new_cookie_and_login()


def req(method, url, data=None, cookies=None):
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

    response_json, status_code = req(method, url, data=data, cookies=cookies)

    if 'status' in response_json and response_json['status'] == 'success':
        return response_json, status_code
    else:
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
        traceback.print_exc()
        return render_template("error.html", error_message=e.message)

    return render_template('index.html', sensors=data, device_name=device_name)


if __name__ == '__main__':
    app.run()
