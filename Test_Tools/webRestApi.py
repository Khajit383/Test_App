import requests
import json

def getAuth(ip):
    r = requests.post('http://' + ip + '/xt/auth', json={"username":"admin", "password":"123adftech123"}, timeout=0.1)
    auth = json.loads(r.content)['auth']
    return {'auth' : auth}

def xt_web_GET(ip,path):
    cookie = getAuth(ip)
    print (cookie)
    r_dl = requests.get('http://' + ip + '/'+ path,cookies=cookie)
    print (r_dl.content)

def xt_web_PATCH(ip,path,json_payload):
    cookie = getAuth(ip)
    print (cookie)
    r_dl = requests.patch('http://' + ip + '/'+ path, json=json_payload, cookies=cookie)
    print (r_dl.content)

def xt_web_PATCH_file(ip,path,filename):
    cookie = getAuth(ip)
    print (cookie)
    filedata = ""
    try:
        fp = open(filename, "r")
        filedata = fp.read()
    except:
        print ("could not open file")
    r_dl = requests.patch('http://' + ip + '/'+ path, data=filedata, cookies=cookie)
    print (r_dl.content)

def xt_web_DELETE(ip,path,json_payload):
    cookie = getAuth(ip)
    print (cookie)
    r_dl = requests.delete('http://' + ip + '/'+ path, json=json_payload, cookies=cookie)
    print (r_dl.content)

def xt_web_POST(ip,path,json_payload):
    cookie = getAuth(ip)
    print (cookie)
    r_dl = requests.post('http://' + ip + '/'+ path, json=json_payload, cookies=cookie)
    print (r_dl.content)

def xt_download(ip,path,filename):
    cookie = getAuth(ip)
    r_dl = requests.get('http://' + ip + '/'+ path,cookies=cookie)
    f = open(filename,'wb+')
    f.write(r_dl.content)
    f.close()


def test_json(ip = "192.168.1.100", path = "xt/serial/2/modbus/csv"):
    cookie = getAuth(ip)
    f = open("modbus_json", 'r')
    json_payload = f.read()
    f.close
    r_dl = requests.patch('http://' + ip + '/'+ path, payload=json_payload, cookies=cookie)
    print (r_dl.content)
