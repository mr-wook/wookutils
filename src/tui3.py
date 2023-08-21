#!/bin/env python3
"""
tui3.py -- A simple Text UI support library;
"""

# Copyright (c) 2019, 2020 Wook

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

__license__ = "MIT"
__author__  = "mr.wook@gmail.com"

if True:
    import os
    import re
    import readline
    import shlex
    import stat
    import sys
    import types
    import subprocess

class Curry(object):
    def __init__(self, fn, *args, **kwa):
        self._args = args
        self._kwa = kwa
        self._fn = fn

    def __call__(self, *args, **kwa):
        if kwa:
            xkwa = self._kwa.copy()
            xkwa.update(kwa)
            kwa = xkwa
        else:
            kwa = self._kwa
        if not args:
            args = self._args
        return self._fn(*args, **kwa)

class Tui3(object):
    """This is a modal text user interface.
    Its only virtue is in its fast deployability.
    ui = TUI(prompt=string)
    ui.callback({'commandname':callback_method, ... })
    ui.add('commandname', callback_method)
    ui.mainloop()
    The callback methods can modify the callback dict via direct replacement,
    push, and pop
    """
    CLASSNAME = "Tui3"

    def __init__(self, **kwa):
        self._prompt     = kwa.get('prompt', "tui% ")
        self._arg        = kwa.get('arg', None)
        self._at_paths   = kwa.get('at_paths', [ ".", "~" ])
        self._pre_prompt_cb = kwa.get('pre_prompt_cb', None)
        self._cb         = { }
        self._file_flags = { }
        self._cbstack    = [ ]
        self._cmdvec     = [ ]
        self._aliases    = dict() # alias_name = { cmd: "name", args: [ ]} # append ui.args to args before invoking;
        self._cmd = self._arg = self._value = None
        self._cmdline = ""
        self._prefix_chars = ""
        self._prefaces = kwa.get('prefaces')
        if self._prefaces:
            self._prefix_chars = self._prefaces.keys().join("")

    def __getitem__(self, x):
        if type(x) == types.IntType: return self._cmdvec[x + 1]
        if type(x) == types.StringType: return self._calls[x]
        raise TypeError("Can't index type by %s" % type(x))

    def __setitem__(self, x, v):
        if type(x) == types.IntType:
            self._cmdvec[x + 1] = v
            return
        if type(x) == types.StringType:
            self._calls[x] = v
            return
        raise TypeError("Can't index type by %s" % type(x))

    def callback(self, cbdict, arg = None):
        "Replace the current callback dictionary"
        if not type(cbdict) == types.DictType:
            raise TypeError("%s::callback(cbdict) arg is not a dictionary" % Tui3.CLASSNAME)
        self._cb = cbdict
        self._arg = arg

    def add(self, cmd, meth, *args, **kwa):
        self._cb[cmd] = Curry(meth, *args, **kwa)

    def commands(self):
        rl = list(self._cb.keys())
        rl = [s for s in rl if not s.startswith('__')]
        rl.sort()
        return rl

    def push(self):
        "Push an additional callback on the stack to preserve state;"
        self._cbstack.append([ self._cb, self._arg, self._prompt ])

    def pop(self):
        "Pop a callback, and setup it's parameters as current;"
        trip = self._cbstack.pop()
        self._cb = trip[0]
        self._arg = trip[1]
        self._prompt = trip[2]

    def prompt(self, str = None):
        "Modify the current prompt"
        if str == None: return self._prompt
        self._prompt = str

    def mainloop(self):
        "Main loop, for synchronous command processing;"
        while True:
            try:
                ln = self._cmdline = input(self._prompt)
            except EOFError as e:
                # if cmds['__eof__']: return value from dispatch to __eof__
                print("Exiting...")
                sys.exit(0)     # Test for ignoreeof after adding support for .set;
            self.doCommand(ln)

    def args(self): return self._cmdvec[1:]

    def arg(self, i=0): return self._cmdvec[i + 1]

    def value(self):
        'Return value returned by last user method'
        return self._value

    def __len__(self):
        "Return number of parameters (including command) of current command"
        return len(self._cmdvec)

    def doCommand(self, ln, **kwa):
        # print("doCommand: '%s'" % ln)
        if ln.startswith('@'):          # Support command file processing;
            ifile = ln[1:]
            self._sourceFile(ifile.strip())
            return
        if ln.startswith('!'):          # Execute command as subprocess invocation;
            subcmd = ln[1:]
            try:
                (obuf, ebuf) = self.subCommand(subcmd)
                # print("ebuf %d bytes" % len(ebuf))
                # print("obuf %d bytes" % len(obuf))
                if len(ebuf) > 1:
                    print("Errors:", "\n".join(ebuf))
                if len(obuf) > 1:
                    print("\n".join(obuf))
            except Exception as e:
                print(f"subCommand failed -- {str(e)}")
            return
        # Regular in-line commands;
        try:
            self._cmdvec = shlex.split(ln)
        except ValueError as e:
            print(f"Bad Parse: {str(e)}")
            return False
        if not self._cmdvec:
            # Use __nullcmd__ here somehow... return self.doCommand("__nullcmd__", **kwa) ?
            return True
        else:
            cmd = self._cmdvec[0]
        self._argtext = ln[len(cmd):].strip()

        if cmd in self._aliases:
            alias = self._aliases[cmd]
            orig_cmd = alias['cmd']
            args = alias['args'] + self.args[1:]
            # self._cmdvec = [ cmd ] + args + self.args[1:]
            # self._arg = self._cmdvec[1]
            self._value = orig_cmd(self, self._arg)
            return self._value

        if self._cmdline == "":         # Handle null command as special case;
            if '__nullcmd__' in self._cb:
                self._cb['__nullcmd__'](self, self._arg)
            return

        self._cmd = self._cmdvec[0]
        prefix = ln[0]
        if prefix in self._prefix_chars:        # Handle special prefaces (., /, etc);
            dispatch = self._prefaces[prefix]
            self._value = dispatch(self, self._args)
            return self._value
        if len(self._cmdvec) > 1:
            self._arg = self._cmdvec[1]
        else:
            self._arg = None

        if not self._cmd in self._cb:
            if '__cmderr__'in self._cb:
                self._cb['__cmderr__'](self, self._arg)
            else:
                print("Unknown command", self._cmd)
            return
        # Actually execute command, and preserve returned value;
        self._value = self._cb[self._cmd](self, self._arg, **kwa) 
        return self._value

    def parse_inline_option(self, switch, args, **kwa):
        "Parse args prefaced by keyword, return ( keyword|False, ( items ), remaining_args )"
        count = kwa.get('count', 1)
        args = args[:]
        rl = []
        if switch not in args:
            return tuple([False, ( ), args])

        where = args.index(switch)
        rl = [ args.pop(where) ]
        count -= 1
        while count:
            rl.append(args.pop(where))
            count -= 1
        rl.append(args)
        return rl

    def parse_inline_options(self, optlist, args, **kwa):
        rd = dict()
        for opt in optlist:
            count = opt[-1]
            switch = opt[0]
            if switch not in args:
                continue
            where = args.index(switch)
            args.pop(where)
            count -= 1
            rl = [ ]
            while count > 0:
                rl.append(args.pop(0))
                count -= 1
            rd[switch] = rl
        return rd, args

    def set_alias(self, name, *args):
        """alias <name> args -- setup alias using first word in args to determine dispatch;"""
        # tui.add_alias(<name>, self._cb[args[0]], args[1:]])
        cmd = args[0]
        if cmd not in self._cb:
            print("Cannot alias to non-existent command %s" % cmd)
            return False
        if cmd in self._aliases:
            print("Cannot alias to an alias (%s)" % cmd)
            return False
        self._aliases[name] = dict(cmd=self._cb[args[0]], args=args[1:])
        pass

    def _sourceFile(self, fn):
        "Execute commands from source file if found accessible;"
        if self._at_paths and ('/' not in fn):
            for prefix in self._at_paths:
                fp = f"{prefix}/{fn}"
                if os.path.isfile(fp):
                    fn = fp
                    break
        try:
            ifd = open(fn, 'r')
        except IOError as e:
            print("Couldn't open %s: %s" % ( fn, e ))
            return
        ibuf = [x[:-1] for x in ifd.readlines()]
        ifd.close
        flags = dict()
        if ibuf[0].startswith(":"):
            flags = ibuf.pop(0)
            flags = flags[1:]
            flags = re.split(r'\s+', flags)
            flags = dict([(flag.split('=', 1)[0], flag.split('=')[1]) for flag in flags])
            self._file_flags[fn] = flags
        for ln in ibuf:
            if not ln:
                continue
            if ln.strip().startswith('#'):
                continue
            if flags.get('quiet', 0) == 0:
                print(">> %s" % ln)
            self.doCommand(ln, **flags)
        return

    def subCommand(self, subcmd):
        "Execute command as a (hopefully) valid subprocess command"
        subcmd = re.split(r'\s+', str(subcmd))
        pipe = subprocess.Popen(subcmd,
                                 stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                                 shell=False)
        (so, se) = pipe.communicate()
        so = str(so)[2:-1]
        se = str(se)[2:-1]
        obuf = re.split(r'\\n', so)
        ebuf = re.split(r'\\n', se)
        self._subprocess_exit = pipe.wait()
        return (obuf, ebuf)
        
    @property
    def argline(self):
        return " ".join(self.args)

    @property
    def args(self):
        return self._cmdvec[1:]
    
    @property
    def argtext(self):
        return self._argtext
    
    @property
    def cmdline(self):
        return self._cmdline

    @property
    def cmdnames(self):
        return self._cb.keys()

# Test App;
if __name__ == "__main__":

    def quitmethod(ui, arg):
        sys.exit(0)

    def lsmethod(ui, arg):
        # print type(arg), repr(arg)
        if arg == None:
            lst = os.listdir('.')
            lst.sort()
            olst = [ ]
            for f in lst:
                if f.startswith('.'): continue
                if f.endswith('~'): continue
                if f.endswith('#'): continue
                olst.append(f)
            for f in olst:
                print(f)
        else:
            import stat
            str = os.stat(arg)
            print(arg, str[stat.ST_SIZE])

    def echomethod(ui, arg):
        print(repr(arg))

    def ls_show_method(ui, arg):
        if arg == None: return
        str = os.stat(arg)
        print("%s (%d)" % ( arg, str[stat.ST_SIZE] ))
        ifd = open(arg, "r")
        ln = ifd.readline()
        ifd.close()
        print(ln)

    def echo_line(ui, arg):
        print(ui.cmdline())

    def main_mode(ui, arg):
        ui.pop()
        ui.prompt("main% ")

    showmode = { 'qq':quitmethod, 'ls':ls_show_method, 'echo':echo_line,
                 'q':main_mode }

    def show_mode(ui, arg):
        ui.push()
        ui.callback(showmode)
        ui.prompt("show% ")

    # Real App Start
    tui = Tui3(prompt="main% ")
    tui.add('ls', lsmethod)
    tui.add('q', quitmethod)
    tui.add('quit', quitmethod)
    tui.add('echo', echomethod)
    tui.add('show', show_mode)
    tui.mainloop()
    print("Unexpected exit")
    sys.exit(1)
