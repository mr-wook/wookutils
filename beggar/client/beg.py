#!/usr/bin/env python3

if True:
    import argparse
    import os
    import pprint
    import requests
    import sys

class App:
    def __init__(self):
        # add file:<name>, pull:<url> send:<file>, get:<file>
        self._operations = dict(ls=self._ls, mv=self._move, move=self._move, touch=self._touch, rm=self._rm, delete=self._rm)
        self._operations['del'] = self._rm # fracking reserved words...
        # Add support for --across=hostname,hostname,hostname,...

    def die(self, text, code=1):
        print(f"FATAL: {text}")
        sys.exit(code)

    def help(self, which="main", hostname="<hostname>"):
        def details():
            print("All file paths should be rooted;")
            print("The server needs to be accessible, and running the beggar server;")
            print("Not all file paths are permissible and there are no remote re-configure options;")
            print("set BEGGAR_NAME as a known user name in the environment;")
            print("set BEGGAR_KEY as a valid key in the environment;")
            return True
        pname = os.path.split(sys.argv[0])[-1]
        which = which.lower()
        # Please, let us have Python 3.10 so we can do match;
        if which == "main":
            print(f"{pname} <hostname> <operation> <operation specific args>")
            return details()
        if which == "post_hostname_args":
            print(f"{pname} {hostname} still needs arguments after the hostname, like the operation, ie:")
            return self.help("main")
        if which == "ls":
            print(f"{pname} {hostname} ls <rooted directory path>")
            return True
        if which in [ 'rm', 'del', 'delete' ]:
            print(f"{pname} {hostname} {which} <permissible rooted directory path>")
            return True
        if which in [ 'mv', 'move' ]:
            print("{pname} {hostname} {which} <rooted source filename path> <rooted destination filename path>")
            return True
        if which == "touch":
            print("{pname} {hostname} {which} <rooted filename path>")
            return True

    def post(self, endpoint, **kwa):
        url = f"http://{self._hostname}:6869/{endpoint}/"
        headers = dict(Authorization=f"Bearer {os.getenv('BEGGAR_KEY', '.....')}")
        kwa = { **kwa, **dict(user=os.getenv('BEGGAR_USER', 'anon')) }
        resp = requests.post(url=url, json=kwa, headers=headers)
        # resp = requests.post(url=url, json=kwa)
        if resp.status_code != 200:
            self.die(f"failed: {resp.json()['error']}")
        # print(pprint.pprint(resp.json(), indent=2))
        return resp

    def _ls(self, *args):
        def show_file(dict_):
            fp, sz, gid, uid = dict_['path'], dict_['size'], dict_['gid'], dict_['uid']
            if 'uname' in dict_:
                uid = dict_['uname']
            if 'gname' in dict_:
                gid = dict_['gname']
            print(f"{fp:<20s} {uid}:{gid} {sz}")

        resp = self.post("ls", path=args[0])
        json_ = resp.json()
        tj = type(json_)
        if tj == type([ ]):
            for dict_ in json_:
                show_file(dict_)
        elif tj == type({ }):
            show_file(json_)
        else:
            print("Busted ass json")
            return 1
        return 0

    def _move(self, *args):
        resp = self.post("move", source=args[0], dest=args[1])
        json_ = resp.json()
        print(json_['result'])
        return 0

    def _rm(self, *args):
        resp = self.post("rm", path=args[0])
        json_ = resp.json()
        print(json_['result'])
        return 0

    def _touch(self, *args):
        resp = self.post("touch", path=args[0])
        json_ = resp.json()
        print(json_['result'])
        return 0

    def run(self, *args):
        args = list(args)
        if not args:
            self.help()
            sys.exit(0)
        # if not args.across:
        #     across = [ args.pop(0).lower()]
        # else:
        #     across = re.split('\s*,\s*', args.across)
        # for host in args.across:
        #     self._hostname = host
        #     self._operations[op](*args, host)
        self._hostname = hostname = args.pop(0).lower()
        if not args:
            self.help("post_hostname_args", hostname)
            sys.exit(0)
        self._op = op = args.pop(0).lower()
        if op not in self._operations:
            print(f"Unknown operation {op}", hostname)
            sys.exit(1)
        rc = self._operations[op](*args)
        return rc

if __name__ == "__main__":
    args = sys.argv[:]
    pname = args.pop(0)
    app = App()
    rc = app.run(*args)
    sys.exit(rc)
