from flask import Flask, render_template, jsonify
import requests
import devices
from random import choice
import string
import os.path
from datetime import datetime, timedelta
import time
import json

cookie_length = 32
cookie_id_filename = 'cookie.txt'
cookie_timeout = timedelta(minutes=5)
http_headers = {'Content-Type' : 'application/x-www-form-urlencoded'}

app = Flask(__name__)
app.debug = True


def generate_new_cookie_and_login():
    f = open(cookie_id_filename, 'w')
    cookie_id = ''.join(choice(string.digits) for i in range(cookie_length))
    f.write(cookie_id + ' ' + str(int(time.mktime(datetime.now().timetuple()))))
    f.close()

    cookie_dict = dict(AIROS_SESSIONID=cookie_id)

    print "dict: " + str(cookie_dict)

    login_string = 'username=' + devices.login_user + '&password=' + devices.login_password
    r = requests.post('http://' + devices.device_ip_address + '/login.cgi', data=login_string, cookies=cookie_dict, headers=http_headers)

    print "login content: " + r.content

    return cookie_dict


def get_cookie_dict():
    if os.path.isfile(cookie_id_filename):
        f = open(cookie_id_filename, 'r')
        parts = f.readline().split(' ')
        f.close()

        if len(parts) >= 2:

            cookie_id = parts[0]
            timestamp = parts[1]

            timedelta = datetime.now() - datetime.fromtimestamp(int(timestamp))

            print "timedelta: " + str(timedelta)
            if timedelta > cookie_timeout:
                # the cookie is too old, login again
                return generate_new_cookie_and_login()
            else:
                return dict(AIROS_SESSIONID=cookie_id)
        else:
            return generate_new_cookie_and_login()
    else:
        return generate_new_cookie_and_login()


def get_sensor_data():
    cookies = get_cookie_dict()
    r = requests.get('http://' + devices.device_ip_address + '/sensors', cookies=cookies)
    response_json = r.json()

    print "status: " + response_json['status']

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
    cookies = get_cookie_dict()
    r = requests.put('http://' + devices.device_ip_address + '/sensors/' + str(id), data=data, cookies=cookies)

    return "", r.status_code





@app.route('/')
def hello_world():
    return render_template('index.html', sensors=get_sensor_data())


if __name__ == '__main__':
    app.run()
