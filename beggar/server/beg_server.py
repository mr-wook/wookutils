#!/bin/env python3

if True:
    from   configparser import ConfigParser
    from   flask import Flask, request, jsonify
    import grp
    import json
    import ldap3
    import logging
    import os
    import pwd
    import shutil
    import zlib_utility_functions
    import zlib

    if os.getenv('DMITRI_MOCK', 0):
        import dmitri_mock as ds
    else:
        import dmitri_script as ds


class Jimmy(ds.BasicClient):
    # This loads the project file with the specified name into the D-Mitri system.
    # By default it will look for the project to load in the "Support Files" folder.  If you
    # want you can modify filePath to look elsewhere, though.
    # adapted from class dmitri_script.OpenProjectClient:
    def __init__(self):
      self._sendConfig = True          # set to False if you'd rather just load the Project but not send config
      self._loadMixerSettings = False  # set to True if you'd like the project's saved Mixer Settings to be loaded in

    def ConnectedToServer(self, fp):
         if ("/" in fp):
            filePath = fp
         else:
            filePath = "/tmp/supportfiles/" + fp
        self._filepath = filePath
         self.Log("Loading project file [%s]" % filePath)
         projectMsg = self.ReadAndInflateProjectFile(filePath) # Read the local project file and inflate it;
         if (projectMsg != None):
            # print projectMsg  # uncomment if you'd like to see the whole project printed to stdout!
            if self._sendConfig:
               projectMsg.PutBool("sendconfig", True)
            if self._loadMixerSettings == False:
               self.RemoveMixerSettingsFromProjectMessage(projectMsg)
            self.SendMessageToServer(projectMsg, "cued")
            self.Log("Sent project file [%s] to D-Mitri system." % filePath)
      else:
         self.Log("Usage:  upload_project.py support_file_name.dmitriProject")

      self.EndEventLoop()

    # Returns a Message object representing the loaded Project on success, or returns None on failure
    def ReadAndInflateProjectFile(self, filePath = None):
        if filePath == None:
            filePath = self._filepath
        infile = open(filePath, 'rb')
        if (infile != None):
            header, numInflatedBytes = struct.unpack("<2L", infile.read(8))
        if (header == zlib_utility_functions.ZLIB_CODEC_HEADER_INDEPENDENT):
            zlibCompressedData = infile.read()
            if (zlibCompressedData != None):
                infMsg = ds.message.Message()
                dobj = zlib.decompressobj()
                idata = dobj.decompress(zlibCompressedData, numInflatedBytes)
                idata = idata + dobj.flush()
                infMsg.Unflatten(cStringIO.StringIO(idata))
                return infMsg.GetMessage("project")
            else:
                self.Log("Error, couldn't read project file [%s]" % filePath)
         else:
            self.Log("Error, wrong header in file [%s] (wrong file type?)" % filePath)
         infile.close()
      else:
         self.Log("Error, couldn't open project file [%s]" % filePath)

      return None  # Failure

    # Removes the Mixer Settings message from the given Project Message so that they won't get loaded in
    def RemoveMixerSettingsFromProjectMessage(self, projectMsg):
      subMsg = projectMsg.GetMessage(storage_reflect_constants.PR_NAME_NODECHILDREN)
      if subMsg:
         subMsg = subMsg.GetMessage(qnet_protocol.CUEPROJECT_NODENAME_MIXERCONFIG)
         if (subMsg):
            subMsg = subMsg.GetMessage(storage_reflect_constants.PR_NAME_NODEDATA)
            if (subMsg):
               subMsg.RemoveName("gc_cp") 
               for i in range(0, 3):
                  subMsg.RemoveName("gc_sr%i"%i)

class Beggar:
    def __init__(self):
        pass # self._config = self.config_parse()

    # Example usage:
    # if authenticate("username", "password", "your_ad_server_address", "your_domain"):
    #     print("Authentication successful!")
    # else:
    #     print("Authentication failed!")
    def _authenticate_ad(self, username, password, server_address="127.0.0.1", domain='sphereentertainmentco.com'):
        # Establish a connection to the AD server
        server = ldap3.Server(server_address, get_info=ldap3.ALL)
        
        # Concatenate domain and username
        user_dn = f"{username}@{domain}"

        # Try to bind (authenticate) to the server with the provided username and password
        try:
            connection = ldap3.Connection(server, user=user_dn, password=password)
            if connection.bind():
                return True  # Authentication succeeded
        except ldap3.core.exceptions.LDAPBindError as e:
            pass  # This exception is raised for bad username/password combos.
        
        return False  # Authentication failed

    def _authenticate_hack(self, username, password):
        if username not in self.users:
            return False
        udict = self.users[username]
        if 'pwd' not in udict:
            return False                # Login disallowed;
        if password != udict['pwd']:
            return False
        self._role = udict.get('role', 'loser')
        return True

    def authenticate(self, username, password):
        return self._authenticate_hack(username, password)

    def config_parse(self):
        with open('/usr/local/etc/beggar.json', 'r') as ifd:
            json_ = json.loads(ifd.read())
        return json_

    def error_json(self, error_text, code = 400):
        return jsonify(error=error_text), code

    def path_and_exists(self, json_, must_exist=True):
        if 'path' not in json_:
            return error_json("No path in json")
        fp = json_['path']
        if not fp.startswith("/"):
            return error_json(f"Path must be rooted, {fp} isn't")
        if must_exist:
            if not os.path.exists(fp):
                return error_json(f"No such file {fp}")
        return True

    def filedata(self, fp):
        statbuf = os.stat(fp)
        data = dict(path=fp, size=statbuf[6], uid=statbuf[4], gid=statbuf[5])
        try:
            pwd_struct = pwd.getpwuid(data['uid'])
            data['uname'] = pwd_struct[0]
        except Exception as e:
            pass
        try:
            grp_struct = grp.getgrgid(data['gid'])
            data['gname'] = grp_struct[0]
        except Exception as e:
            pass
        return data

    @property    
    def users(self):
        return self._config['users']

    @property
    def paths(self):
        return self._config['paths']

    @property
    def readable(self):
        return self.paths['readable']

    @property
    def writable(self):
        return self.paths['writable']

logging.basicConfig(filename='beg_server.log', level=logging.DEBUG)

beggar = Beggar()

app = Flask(__name__)

@app.route('/dmitri/', methods = [ 'POST' ])
def dmitri_item():
    data = request.json
    rc = beggar.path_and_exists(data)
    if rc != True:
        return beggar.error_json("path_and_exists({data}) failed, rc={rc}")
    fp = data['path']
    jimmy = Jimmy()
    jimmy.ConnectedToServer(fp)
    return jsonify(dict(result=f"{fp} installed, I guess..."))

@app.route('/ls/', methods=['POST'])
def ls_item():
    try:
        # Parse the JSON from the request
        data = request.json
        rc = beggar.path_and_exists(data)
        if rc != True:
            return beggar.error_json(f"rc={rc} when verifying path exists") # It's the error_json result;
        fp = data['path']
        if os.path.isfile(fp):
            # statbuf = os.stat(fp)
            # data = dict(path=fp, size=statbuf[6], uid=statbuf[4], gid=statbuf[5])
            data = beggar.filedata(fp)
        elif os.path.isdir(fp):
            flist = [fn for fn in os.listdir(fp) if not fn.startswith('.')] # don't do hidden files;
            flist.sort()
            data = [ ]
            for fn in flist:
                data.append(beggar.filedata(f"{fp}/{fn}"))
        else:
            return beggar.error_json("{fp} is neither a directory nor a file")
        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/move/', methods = [ 'POST' ])
def move_file():
    data = request.json
    if 'source' not in data:
        return beggar.error_json("No source path in json")
    src = data['source']
    if 'dest' not in data:
        return beggar.error_json("No dest path in json")
    dest = data['dest']
    try:
        shutil.move(src, dest)
        return jsonify(dict(result=f"Move complete {src} --> {dest}"))
    except Exception as e:
        return beggar.error_json(f"Move failed -- {str(e)}")

@app.route('/rm/', methods = [ 'POST' ])
def rm_item():
    def can_be_deleted(fp):
        if not fp.startswith("/tmp/"):
            return False
        return True
    data = request.json
    rc = beggar.path_and_exists(data)
    if rc != True:
        return rc
    fp = data['path']
    if not beggar.can_be_deleted(fp):
        return error_json(f"Invalid path {fp} you destructive prick, fuck off!")
    try:
        os.unlink(fp)
        return jsonify({"result": f"{fp} is so gone..."})
    except Exception as e:
        return beggar.error_json(str(e))

@app.route('/touch/', methods=[ 'POST' ])
def touch_item():
    data = request.json
    rc = beggar.path_and_exists(data, must_exist=False)
    if rc != True:
        return rc
    fp = data['path']
    which_dir = fp.split('/')[0]
    if which_dir not in beggar.writables:
        return beggar.error_json("Can't write to {fp}, disallowed!")
    try:
        afd = open(fp, 'a')
        afd.close()
        return jsonify({"result": f"Touched {fp}"})
    except Exception as e:
        return beggar.error_json(str(e)), 400

if __name__ == "__main__":
    # app.config = config_parse()
    app.run(debug=True, host='0.0.0.0', port=6869) # use 0.0.0.0 to accept any;


