#!/usr/local/bin/python3
# -*- Python -*-

"""Wooks Generic Library, a bunch of useful stuff for RAD"""

if True:
    import boto3
    from   collections import OrderedDict
    from   configparser import ConfigParser
    import os
    import re
    import string
    import subprocess
    import sys
    import types


STRING_TYPE = type("")
INT_TYPE    = type(0)
FLOAT_TYPE  = type(1.0)
TUPLE_TYPE  = type(())
LIST_TYPE   = type([])
DICT_TYPE   = type({})

class Processor:
    """Generic text processing tools;"""
    def __init__(self):
        self.data = [ ]
        self.errors = [ ]
        self.rc = 0

    def __len__(self):
        return len(self.data)

    def grep(self, s, **kwa):
        squeeze = kwa.get('squeeze')
        index = kwa.get('index', False)
        invert = kwa.get('invert', False)
        if not invert:
            rl = [ln for ln in self.data if s in ln]
        else:
            rl = [ln for ln in self.data if s not in ln]

        if squeeze:
            rl = map(self.squeeze, rl)
        if kwa.get('unsemi'):
            rl = map(lambda s: s.replace(';', ''), rl)
        if kwa.get('lastword') == True:
            rl = map(lambda s: re.split(r'\s+', s)[-1], rl)
        if index != False:
            return rl[index]
        return rl

    def squeeze(self, s):
        "Remove concatenated separators -- replace w/ regex?;"
        while "  " in s:
            s = s.replace("  ", " ")
        return s

    def startswith(self, target):
        if not self.data:
            return False
        return self.fulltext.startswith(target)

    def line_count(self, s):
        "Count number of lines in which s appears;"
        return len([ln for ln in self.data if s in ln]) 

    @property
    def fulltext(self):
        if self._fulltext:
            return self._fulltext
        if not self.data:
            return ""
        self._fulltext = "\n".join(filter(None, self.data))
        return self._fulltext

    @property
    def listify(self):
        list_ = [ ]
        for ln in self.data:
            line_list = re.split(r'\s+', ln)
            list_.apend(line_list)

class SubApp(Processor):
    """Generic Subprocessing;"""
    def __init__(self, *args):
        super(SubApp, self).__init__()
        # would with work here, since close isn't available?
        pipe = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        so, se = pipe.communicate()
        so, se = so.decode('utf-8'), se.decode('utf-8')
        self.rc = pipe.wait()
        # print("SubApp: type(so)=%s so=%s" % ( type(so), so ))
        self.data = so.split('\n')
        self.errors = se.split('\n')
        # pipe.close()
    
class RandomFile(Processor):
    """Apply Processor methods to arbitrary source file;"""
    def __init__(self, fn):
        super(RandomFile, self).__init__()
        ifd = open(fn, 'r')
        self.data = [ln[:-1] for ln in ifd.readlines()]
        ifd.close()

class MapFile(Processor):
    """Create a map out of file containing 'key: value' strings;"""
    def __init__(self, fn):
        super(MapFile, self).__init__()
        ifd = open(fn, 'r')
        self.data = [ln[:-1] for ln in ifd.readlines()]
        ifd.close()
        self._map = {}
        for ln in self.data:
            if not ln:
                continue
            k, v = re.split(r'\s*:\s*', ln, 1)
            k, v = k.strip(), v.strip()
            self._map[k] = v

    def __getitem__(self, k): return self._map[k]
    def __contains__(self, k): return k in self._map
    def __len__(self): return len(self._map)
    def keys(self): return self._map.keys()

class Config(object):
    "Extensions to SafeConfigParser -- cannot inherit without auto-instantiating?, so I made a composite class;"
    def __init__(self, fn, *args, **kwa):
        self._version = sys.version_info[0]
        if self._version > 2:
            self._scp = ConfigParser()
            self._sections = self._scp.sections()
        else:
            self._scp = SCP(*args, **kwa)
        base_fn = fn
        if not fn.startswith("/"):
            found = False
            for pos in [ ".", "..", os.path.expanduser("~") ]:
                fn = "%s/%s" % ( pos, base_fn )
                if os.path.isfile(fn):
                    found = True
                    break
            if not found:
                raise RuntimeError("Cannot find config file %s" % base_fn)
        self._scp.read(fn)
        secs = self._scp.sections()
        self._sections = OrderedDict()
        for sec in secs:
            self._sections[sec] = OrderedDict(self._scp.items(sec))

    def __getitem__(self, sec):
        return self._sections[sec]

    def __contains__(self, sec):
        return sec in self._sections

    def __call__(self, sec, item, dflt = None):
        if not sec in self._sections:
            raise RuntimeError("Missing Section %s" % sec)
        if self._version < 3:
            items = self._sections[sec]
            if not item in items:
                return dflt
            return items[item]
        else:
            if not item in self._scp[sec].keys():
                return dflt
            return self._scp[sec][item]

    def sections(self):
        return self._sections.keys()

# ________________________________________________________________
# Utility Classes
#

class App(object):
    "Standard App support stuff, should replace swproc w/ argpase, etc."
    _name = None
    _app_fp = None
    _args = None
    def __init__(self, pname = None, *args, **kwa):
        """App() constructor, requires pname (app name),
        command line args in args to follow as a list (if available),
        and kwa allows the setup of default initial switches and values"""
        if len(args) > 0:
            self._args = list(args[:])
        else:
            self._args = [ ]
        self._switches = { }
        if pname == None:
            pname = sys.argv[0]
        self._app_fp = pname
        sls = pname.rfind('/')
        self._name = pname[sls + 1:]
        self._notify = False
        self._dict = { }
        self._fmatch = re.compile(r"^([+|-]\d+\.\d*)$") # Match for floating point number
        self._imatch = re.compile(r"^([+|-]\d+)$") # Match for signed int
        for k in kwa:
            self._switches[k] = kwa[k]

    def __contains__(self, k): return k in self._switches

    def __getitem__(self, k):
        """Referring to App[item] gets the switch value of item,
        which is True if no arg, arg if sw=arg, or False if not seen"""
        if type(k) == type(0):
            if k >= len(self._args): raise StopIteration
            return self._args[k]
        if not k in self._switches: return None
        return self._switches[k]

    def __setitem__(self, k, v):
        """The normal use of this is to set initial defaults before swproc is called,
        then you never have to worry about the app[foo] == False case"""
        self._switches[k] = v

    def __delitem__(self, k): del self._switches[k]

    def get(self, k, dflt):
        if k in self._switches: return self._switches[k]
        return dflt

    def __str__(self):
        "Return application name without leading path"
        return self._name

    def __repr__(self):
        "Return application name and switch dict"
        return repr(self._name) + " " + repr(self._dict)

    def __len__(self): return len(self._args)

    def pop(self, i=-1): return self._args.pop(i)

    def load_text(self, fn):
        ifd = open(fn, 'r')
        ibuf = [ln[:-1].strip() for ln in ifd.readlines()]
        ifd.close()
        return ibuf
    
    def name(self):
        "Return application name without leading path"
        return os.path.splitext(self._name)[0]

    def path(self):
        "Return full path to app"
        return self._app_fp

    def switches(self):
        "Return list of known switch names"
        self.switch_list = self._switches.keys()
        return self.switch_list

    def swproc(self):
        """Simple switch processing,
        absorbs -sw and -sw=val from args supplied in constructor"""
        i = 0
        # print "self._args", self._args ; sys.exit(0)
        while i < len(self._args):
            arg = self._args[i]
            if arg and arg.startswith('-'):
                self._args.pop(i)
                sw = arg
                swname = arg[1:]
                if len(swname) == 0: return False
                if swname[0] == '-': swname = swname[1:] # Absorb --swname stuff
                if swname.find('=') > -1:
                    (swname, swval) = swname.split('=', 2)
                    if swval.isdigit():
                        swval = int(swval) # Yep, only positive int support
                    elif self._fmatch.match(swval):
                        swval = float(swval)
                else:
                    swval = True
                self._switches[swname] = swval
                continue
            else: # Positional arg, skip
                i += 1
        return self._args

    def exit(self, n):
        if self._notify:
            self._notify.close()
        sys.exit(n)

    def Usage(self, txt):
        """Usage(pnmfull, txt) -- Usage error message that peels path prefix from progname
        """
        print("Usage: %s %s" % ( self._name, txt ))

    def Die(self, s, ecode = 1):
        """Die(str) -- Print message, die cleanly"""
        print("FATAL(%s): %s" % ( self._name, s ))
        sys.exit(ecode)

    def Warn(self, s):
        "Print WARNING: %\n"
        print("WARNING: " + s)

    def Info(self, s):
        "Print [%s]\n"
        print("[%s]" % s)

    # n = notify2.Notification('foo', 'bar'); n.show()
    def Notify(self, s):
        import notify2
        # if not hasattr(self, '_notify'): self._notify = None
        if not self._notify:
            # if not hasattr(self, '_name'): self._name = __file__
            notify2.init(self._name)
            self._notify = notify2.Notification(s)
        else:
            self._notify.update(s)
        self._notify.show()

class OrderedSet():
    def __init__(self):
        self._set = []
        self.push = self.append

    def __contains__(self, item):
        return item in self._set

    def __getitem__(self, i):
        return self._set[i]

    def __iter__(self):
        for item in self._set:
            yield item

    def __len__(self):
        return len(self._set)

    def add(self, other):
        curr = set(self._set)
        src = set(other._set)
        new_items = src - curr
        self._set += [item for item in other._set if item in new_items]
        return

    def append(self, item):
        if item in self:
            return
        self._set.append(item)

    def copy(self):
        ros = OrderedSet()
        ros._set = self._set[:]

    def pop(self, index = -1):
        self._set.pop(index)

    def remove(self, item):
        if item not in self._set:
            return ValueError(f"{item} not in set")
        self._set.remove(item)

    def starts_at(self, item):
        i = self._set.index(item)
        subl = self._set[i:]
        for item in subl:
            yield item

class SmartDict(dict):
    def __init__(self, **kwa):
        super(SmartDict, self).__init__()
        self.update(kwa)

    def keys(self):
        keys = super(SmartDict, self).keys()
        keys.sort()

    def __iter__(self):
        keys = self.keys()
        for k in keys:
            yield self[k]

    def deep(self, *indices):
        indices = list(indices)
        table = indices.pop(0)
        while indices:
            table = indices.pop(0)
        return table

    def query(self, sentence):
        indices = re.split(r'\s+', sentence)
        return self.deep(indices)

class Curry(object):
    def __init__(self, fnc, *lst, **kwa):
        self._func = fnc
        self._lst = lst[:]
        self._kwa = kwa.copy()

    def __call__(self, *lst, **kwa):
        nlst = lst + self._lst
        kwa.update(self._kwa)
        return self._func(*nlst, **kwa)

class JobSysParse(object):
    def __init__(self, s):
        t1 = os.sep + 'job' + os.sep
        t2 = os.sep + 'dd' + os.sep + 'shows' + os.sep
        self._j2 = self._lemon = False
        if s.startswith(t1):
            self._j2 = True
            self._offset = 5
        elif s.startswith(t2):
            self._lemon = True
            self._offset = 10
        if (not self._lemon) and (not self._j2):
            raise RuntimeError("Not a valid jobsystem path -- %s" % s)
        s = s[self._offset:]
        self._list = s.split(os.sep)
        self._dict = dict(show=None, seq=None, shot=None, suffix=None)
        sfx = 0
        if len(self._list) > 0:
            self._dict['show'] = self._list[0]
            sfx = 1
        if len(self._list) > 1:
            self._dict['seq'] = self._list[1]
            sfx = 2
        if len(self._list) > 2:
            self._dict['shot'] = self._list[2]
            sfx = 3
        if len(self._list) >= sfx: self._dict['suffix'] = os.sep.join(self._list[sfx:])

    def __getitem__(self, k):
        if type(k) == type(0):
            return self._list[k]
        if type(k) == type(""):
            if k == 'sequence': k = seq
            return self._dict[k]
        raise IndexError("Unknown index type for JSParse")

    def __contains__(self, k):
        if type(k) == type(0): return k <= len(self._list)
        if type(k) == type(""): return k in self._dict
        raise IndexError("Unknown index type for JSParse")
        
    def __len__(self): return len(self._list)

    def __str__(self): return os.sep.join(["job"] + self._list)

    def list(self): return self._list[:]

    def top(self):
        s = os.sep + "job"
        if self['show']: s += os.sep + self['show']
        if self['seq']:  s += os.sep + self['seq']
        if self['shot']: s += os.sep + self['shot']
        return s

class PS:
    """Process status, get all, filter for nm if supplied,
    currently uses output of ps command"""
    #               F       S      uname    pid     ppid     C       PRI
    __pat0 = r"^\s*(\d+)\s+(\w+)\s+(\w+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\-\d]+)"
    #              Nice       Addr        Size    wchan   stime    tty
    __pat1 = r"\s+([\-\d]+)\s+([\-\w]+)\s+(\d+)\s+(\w+)\s+(.*)" # (\w+)\s+([\w\?]+)\s+(.*)"
    #              time                 cmd
    __pat2 = r"\s+(\d{2}:\d{2}:\d{2})\s+(.*)"
    __xlate = { 'f':0, 's':1, 'uname':2, 'pid':3, 'ppid':4, 'c':5, 'pri':6,
                'nice':7, 'addr':8, 'size':9, 'wchan':10, 'stime':11, 'tty':12,
                'time':13, 'cmd':14 }

    def __init__(self, nm = None, **kwa):
        """PS() Constructor, invoke ps -efl, slurp up all output,
        use nm as filter, create a list of all fields post regexp"""
        self._groups = [ ]
        self._ilines = [ ]
        ibuf = Capture('/bin/ps', [ '-efl' ])
        chop(ibuf)                      # Chomp all lines
        pat = self.__pat0 + self.__pat1 # + self.__pat2	# This is a bugaround **TEMP**
        rex = re.compile(pat)
        for ln in ibuf:
            ln = ln.rstrip()
            self._ilines.append(ln)
            if nm != None:
                if ln.find(nm) < 0:     # This should be field constrained
                    continue
            mtch = rex.match(ln)
            if mtch:
                self._groups.append(mtch.groups()[:])
            else:
                grps = re.split(r'\s+', ln)
                self._groups.append(grps)

    def __len__(self):
        """Return number of lines that matched filter,
        or all if no filter on instancing"""
        return len(self._groups)

    def __str__(self):
        "Simple reconstruction of inputs"
        ostr = ""
        for grp in self._groups:
            ostr += "%s %s %s %s %s %s %s %s %s %s %s %s %s %s %s\n" % tuple(grp)
        return ostr

    def __repr__(self):
        "Reconstruction of input that can be eval'd back into a data structure"
        ostr = ""
        for grp in self._groups:
            ostr += repr(grp) + ","
        return "[" + ostr[:-1] + "]"

    def __call__(self, i, k):
        return self._groups[i][self.__xlate[k]]

    def __getitem__(self, k):
        """Get all the fields for supplied index,
        or get ith line, kth field if ps[(i, k)] supplied"""
        if type(k) == type(0):
            return self._groups[k]
        if type(k) in [type(()), type([])]:
            i = k[0]
            k = k[1]
            return self._groups[i][self.__xlate[k]]
        raise TypeError("Couldn't understand index in PS.__getitem__", repr(k))

    def column(self, k): return self.__xlate[k]

class Currency(float):
    def __init__(self, amount):
        self.amount = amount

    def __str__(self):
        temp = "%.2f" % self.amount
        profile = re.compile(r"(\d)(\d\d\d[.,])")
        while 1:
            temp, count = re.subn(profile,r"\1,\2",temp)
            if not count: break
        return temp

class Finder(object):
    "A simple in python directory-walking find"
    def __init__(self, top, pat_or_tgt, **kwa):
        "starting at top, save pat_or_tgt to be used by actual find method"
        self._top = top
        self._tgt = pat_or_tgt
        self._rex = None
        self._opts = {}
        self._opts.update(kwa)
        self._found = [ ]
        self._scanned = 0

    def _traverseP(self, path):
        return os.path.islink(path) and os.path.isdir(path)

    def _reveal(self, dir):
        print("[%s]" % dir)

    def __len__(self):
        return len(self._found)

    def debug(self, v = None):
        if v != None:
            self._opts['debug'] = v
            return
        if not 'debug' in self._opts: return 0
        return self._opts['debug']

    def found(self):
        return self._found

    def find(self):
        "find everything, returned as a list"
        os.path.walk(self._top, self._flinks, self._found)
        return self._found

    def _flinks(self, arg, dir, fnames):
        for f in fnames:
            fp = dir + os.sep + f
            if self._traverseP(fp):
                os.path.walk(fp, self._flinks, arg)
            else:
                arg.append(fp)
        if self.debug() > 0: self._reveal(dir)

    def filter(self):
        "Only return those items with the target found in the filename"
        os.path.walk(self._top, self._ffilter, self._found)
        return self._found

    def _ffilter(self, arg, dir, fnames):
        for f in fnames:
            fp = dir + os.sep + f
            if self._traverseP(fp):
                os.path.walk(fp, self._ffilter, arg)
            else:
                if f.find(self._tgt) > -1:
                    arg.append(fp)
        if self.debug() > 0: self._reveal(dir)

    def re_follow(self):
        "Use the regex to limit to only matches, but allows the directory path to be included"
        self._rex = re.compile(self._tgt)
        os.path.walk(self._top, self._ref, self._found)
        return self._found

    def _ref(self, arg, dir, fnames):
        for f in fnames:
            fp = dir + os.sep + f
            if self._traverseP(fp):
                os.path.walk(fp, self._ref, arg)
            else:
                m = self._rex.match(fp) # This is the only case that matches pathwise
                if m != None:
                    arg.append(fp)
        if self.debug() > 0: self._reveal(dir)

class Histo(object):
    "Histogram a dictionary, graphically or textually"
    def __init__(self, dct = None, **kwa):
        if dct != None: self._udict = dct # Just keep a reference so we can keep updating things
        else: self._udict = { }
        self._width = 50
        if 'width' in kwa: self._width = kwa['width']
        self._sformat = "%12s:\t%d\n"
        if 'format' in kwa: self._sformat = kwa['format']
        self._tlist = [ ]
        self._reverse = False
        self.update()

    def __str__(self):
        self.update()
        ostr = ""
        for k in keys:
            ostr += self._sformat % (k, self._udict[k])
        return ostr

    def __len__(self): return len(self._udict)

    def __getitem__(self, i):
        if type(i) == type(0): return self._tlist[i]
        return self._udict[i]

    def __setitem__(self, k, v):
        if type(k) != type(""): raise TypeError("Index must be string")
        if type(v) not in [ type(0), type(1.0) ]:
            raise TypeError("Value must be int or float")
        self._udict[k] = v
    
    def update(self):
        self._tlist = [ ]
        for k in self._udict:
            self._tlist.append((self._udict[k], k))
        if len(self._tlist) == 0: return
        self._tlist.sort()
        if self._reverse: self._tlist.reverse
        self._min = min(self._tlist)[0]
        self._max = max(self._tlist)[0]

    def keys(self): return map(lambda t: t[1], self._tlist)

    def values(self): return map(lambda t: t[0], self._tlist)

    def textGraph(self):
        self.update()
        keys = self.keys()
        csize = float(self._max) / float(self._width)
        ostr = ""
        for k in keys:
            lbl = k
            sz = self._udict[k]
            stars = "*" * int(float(sz) / csize)
            ostr += lbl + ": " + stars + '\n'
        return ostr

    def distance(self, h2):
        "Compute the (euclidean) distance between two histograms"
        raise RuntimeError("Not Yet Implemented")

class SimpleMimeMail(object):
    boundary = """________________________________f00dd00d"""
    def __init__(self, **kwa):
        self._segments = [ ]            # List of tuples (mimetype, content)
        self._dict = dict(seglist=[], To=None, From=None, subject="[no subject]",
                          smtphost='localhost')
        self._dict.update(kwa)
        self._segments += self['seglist']

    def __contains__(self, k): return k in self._dict

    def __getitem__(self, k):
        if type(k) == type(""): return self._dict[k]
        if type(k) == type(0): return self._segments[k]

    def __setitem__(self, k, v):
        if type(k) == type(""): self._dict[k] = v
        if type(k) == type(0): self._segments[k] = v

    def __len__(self): return len(self._segments)

    def append(self, mtype, mdata):
        self._segments.append((mtype, mdata))
        return (mtype, mdata)

    def send(self):
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.image import MIMEImage
        from email.mime.base import MIMEBase
        from smtplib import SMTP
        import socket
        msg = MIMEMultipart()
        msg['From'] = self['From']
        msg['To'] = self['To']
        if 'subject' in self:
            msg['Subject'] = self['subject']
        for seg in self._segments:
            (mtype, mdata) = seg
            if '/' in mtype:
                (mtype, subtype) = mtype.split('/', 2)
            else:
                subtype = False
            # print "Assembling %s %s" % (mtype, mdata)
            if mtype == 'text':
                submsg = MIMEText(mdata, _subtype=subtype)
            elif mtype == 'image':
                submsg = MIMEImage(mdata, _subtype=subtype)
            else:
                submsg = MIMEBase(mtype, subtype)
            msg.attach(submsg)
        smtp = SMTP()
        smtp.connect(self['smtphost'])
        smtp.help(socket.getfqdn())
        ss = smtp.sendmail(self['From'].split()[-1],
                           [addr.strip() for addr in self['To'].split(',')],
                           msg.as_string())
        es = smtp.quit()
        return (ss, es)

# SendMail here is retained for backwards compatibility
def SendMail(**kwa):
    """Easy way to Send Mail, all args supplied as kwa (ie: to='address'),
    n.b.: from address must be From='address' (Capital F)
    because of reserved word restrictions on 'from'"""
    from email.MIMEText import MIMEText
    from smtplib import SMTP
    import socket
    smtp = SMTP()
    if 'debug' in kwa:
        smtp.set_debuglevel(kwa['debug'])
    smtphost = 'localhost'
    if 'smtphost' in kwa: smtphost = kwa['smtphost']
    smtp.connect(smtphost)           # This is the normal case at DD
    smtp.helo(socket.getfqdn())
    msg = MIMEText(kwa['body'])
    msg['To'] = kwa['to']
    if 'from' in kwa:
        msg['From'] = kwa['From']
    else:
        msg['From'] = os.getlogin() + "@" + socket.getfqdn()
    if 'subject' in kwa: msg['Subject'] = kwa['subject']
    if 'cc' in kwa: msg['Cc'] = kwa['cc']
    if kwa['to'].find(",") > -1:
        to2 = kwa['to'].split(',')
        to2 = [x.strip() for x in to2]
    else:
        to2 = kwa['to'].split()[-1]
    frm2 = kwa['From'].split()[-1]
    # print "To: %s to2: %s cc: %s" % ( msg['To'], to2, msg['Cc'] )
    ss = smtp.sendmail(frm2, to2, msg.as_string())
    es = smtp.quit()
    return (ss, es)

# ________________________________________________________________
# Just some routines found left in this namespace

def meta_import(libname, libvar, **kwa):
    env = os.environ
    if libvar in env:
        importable = env[libvar]
    else:
        importable = libname
    if 'k_from' in kwa:
        ilist = [ 'from', importable ]
        if 'k_import' in kwa:
            ilist += [ 'import', kwa['k_import'] ]
        if 'as' in kwa:
            ilist += [ 'as', kwa['as'] ]
    else:
        ilist = [ 'import', importable ]
        if 'as' in kwa:
            ilist += [ 'as', kwa['as'] ]
    cmd = ' '.join(ilist)
    print("cmd: %s" % cmd)
    x = compile(cmd, '_wookutil_meta_import.py', 'exec')
    return x

def chop(s):
    "Remove extraneous EOLs from line or all lines in list of lines"
    if type(s) == LIST_TYPE:
        for i in xrange(0, len(s)):
            s[i] = chop(s[i])
        return s
    while len(s) > 0 and (s[-1] == '\n' or s[-1] == '\r'): s = s[:-1]
    return s

def clean(s):
    "Remove EOLs, and trailing and leading whitespace from arg"
    s = chop(s)                         # Remove EOL(s)
    if type(s) == LIST_TYPE:
        return [ln.strip() for ln in s]
    return s.strip()

def uniq(lst):
    if len(lst) < 2:
        return lst
    isTuple = False
    if type(lst) == TUPLE_TYPE:
        isTuple = True
    rlst = set(lst)
    if isTuple:
        return tuple(rlst)
    return list(rlst)

def UnTupleTuple(t1):
    """UnTupleTuple(tup) -- If a tuple of a tuple,
    return as a list of the interior tuple"""
    r = [ ]
    for e in t1:
        for e1 in e:
            r.append(e1)
    return r

def OverArg(fmt, tup):
    """OverArg(fmt, tup) -- format string that doesn't consume everything in the tuple"""
    done = 0
    while not done:
        try:
            ostr = fmt % tup
        except TypeError:
            tup = tup[:-1]
            if len(tup) < 1: return ""
            continue
        return ostr

def Collapse(istr, excl):
    """Collapse(str, excl) -- Remove the elements from excl from the string"""
    ostr = istr
    for r in excl:
        ostr = ostr.replace(r, '')
    return ostr

def Arr_Subtract(a1, a2):
    """Arr_Subtract(a1, a2) -- Remove everything that occurs in a1 from a2, preserves order"""
    for e in a1:
        try:
            a2.remove(e)
        except ValueError:
            pass
    return a2

def KFind(tgt, Hsh):
    """KFind(tgt, hash) -- find key from a hash ignoring case,
    returning correctly cased Key"""
    tl = tgt.lower()
    for k in Hsh:
        if k.lower() == tl: return k
    return None

def Found(tgt, strarr):
    """Found(tgt, strarr) -- Search for an occurrence of one of the strings
    in strarr in tgt, returning true or false (1 or 0)"""
    for s in strarr:
        if tgt.find(s) != -1: return 1
    return 0

def FoundI(tgt, strarr):
    """Search for an occurrence of one of the strings in strarr in tgt,
    returning true or false (1 or 0) - case insensitive"""
    tgtl = tgt.lower()
    for s in strarr:
        sl = s.lower()
        if tgtl.find(sl) != -1: return 1
    return 0

def FoundEnd(tgt, strarr):
    """Search for an occurrence of one of the strings in
    strarr as terminating tgt, returning the ext or None"""
    for s in strarr:
        if tgt.endswith(s): return s
    return None

def Capture(prog, *params, **kwa):
    """Run a prog through popen3 and capture it's errors (first) and output stream
    as an array of lines, keyword arg input provides an input stream"""
    cmd = [ prog ]
    if params:
        cmd += params
    subkwa = dict(stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    for k in [ 'env', 'cwd', 'shell', 'shell' ]:
        if k in kwa:
            subkwa[k] = kwa[k]
    si = kwa.get('input', None)
    if si:
        subkwa['stdin'] = si
    subp = subprocess.Popen(cmd, **subkwa)
    obuf, ebuf = subp.communicate()
    subp.wait()
    if 'debug' in kwa:
        print("Reading Error Messages")
    if 'debug' in kwa:
        if not obuf:
            print("Capture: null output")
            return obuf + ebuf
        print(obuf)
    if ('split_output' in kwa) and kwa.get('split_output'):
        return obuf.decode(), ebuf.decode
    rbuf = obuf + ebuf
    return rbuf.decode()

def RunOnHost(host, cmd, input = None):
    if input:
        raise RuntimeError("Not yet implemented")
    else:
        return DoCapture("rsh", [ host, cmd ])

def Tail(cnt, llbuf):
    "Read the last n lines of a line buffer (array of strings)"
    buflen = len(llbuf)
    if cnt > buflen: cnt = buflen
    for ln in llbuf[-cnt:]:
        if ln.endswith('\n'):
            print(ln[:-1])
        else:
            print(ln)

def Detach(prog, uargs = [ ], env = None):
    """Detach(prog, uargs) -- run prog as a child, passing it args, forget it exists"""
    pid = os.fork()
    if pid != 0:
        return
    else:
        uargs.insert(0, prog)
        if env == None:
            os.execv(prog, uargs)                # Never returns
        else:
            os.execve(prog, uargs, env)
 
def DateOnly(dttm):
    """Try and return a date MySQL can consume"""
    import MySQLdb
    _datetimet = MySQLdb.Date(2005)
    if dttm == None: return ""
    if type(dttm) == type(_datetimet):
        return dttm.Format("%D")
    if not isinstance(dttm, type("")): return dttm
    if len(dttm) > 10:
        return dttm[:10]
    return dttm

def explode_dict(d, *tups):
    "explode_dict(dict_, ('branch_1', 'branch_2', 'branch_3'), ( 'a', 'b', 'c' ), ( '1', '2', '3', '4' ))"
    if not tups:
        return
    for k in tups[0]:
        d[k] = dict()
        explode_dict(d[k], *tups[1:])

# ________________
# Find Variants
#

def FindFollow(path):
    "Find all files at/below path and return a list of them, crossing links"
    flist = [ ]
    os.path.walk(path, FollowLinks, flist)
    return flist

def FollowLinks(arg, dir, fnames):
    "Subsidiary pump for FindFollow"
    for f in fnames:
        fp = dir + "/" + f
        if os.path.islink(fp) and os.path.isdir(fp):
            os.path.walk(fp, FollowLinks, arg)
        else:
            arg.append(fp)

def FindFollowFilter(path, filter):
    "Like FindFollow, but only where filter matches"
    flist = [ ]
    os.path.walk(path, FollowFilter, (flist, filter))
    return flist

def FollowFilter(arg, dir, fnames):
    "Only append if arg[1] appears in file name (not path)"
    lst = arg[0]
    filter = arg[1]
    for f in fnames:
        fp = dir + "/" + f
        if os.path.islink(fp) and os.path.isdir(fp):
            os.path.walk(fp, FollowFilter, arg)
        else:
            if f.find(filter) > -1:
                lst.append(fp)

def FindFollowFilterRegExp(path, filter):
    """Like FindFollow, but only where file matches supplied regexp"""
    flist = [ ]
    rex = re.compile(filter)
    os.path.walk(path, FollowFilterRegExp, (flist, rex))
    return flist

def FollowFilterRegExp(arg, dir, fnames):
    "For people who love RegExp's, like FollowFilter"
    lst = arg[0]
    rex = arg[1]
    for f in fnames:
        fp = dir + "/" + f
        if os.path.islink(fp) and os.path.isdir(fp):
            os.path.walk(fp, FollowFilterRegExp, arg)
        else:
            if rex.match(f):
                lst.append(fp)

def GetMTime(fn):
        status = os.stat(fn)
        return status.st_mtime

def Human_Size(n):
    """Convert integer to rounded human-readable magnitude"""
    def stringify(n):
        k = 1024; m = k * k; g = m * k; t = g * k; p = t * k; x = p * k; y = x * k; z = y * k
        ranges = [ k, m, g, t, p, x, y, z ]
        suffixes = { k:"K", m:"M", g:"G", t:"T", p:"P", x:"X", y:"y", z:"Z" }
        sign = None
        if n < 0:
            sign = "-"
            n = -n
        for upper in ranges:
            where = ranges.index(upper)
            if (where == 0) and n < upper:
                ns = "%d" % n
                if sign:
                    ns = "-" % ns
                return ns
            low_bound = ranges[where - 1]
            hi_bound = ranges[where]
            if n >= low_bound and n < hi_bound:
                fmt = "%%d%s" % suffixes[low_bound]
                if sign:
                    fmt = "-" + fmt
                # v = n / (float(low_bound) + min(1, n % low_bound))
                v = round(n / float(low_bound))
                return fmt % v
        print("WTF: %d not in known range" % n)
        return(str(n))
    if False:
        if n >= 0 and n < k:
            ns = "%d" % n
        elif n >= k and n < m:
            ns = "%dK" % ( n / float(k) + min(1, n % k) )
        elif n >= m and n < g:
            ns = "%dM" % ( n / float(m) + min(1, n % m) )
        elif n >= g and n < t:
            ns = "%dG" % ( n / float(g) + min(1, n % g) )
        elif n >= t:
            ns = "%dT" % ( n / float(t) + min(1, n % t) )
        elif n >= p:
            ns = "%dP" % ( n / float(p) + min(1, n % p) )
        return ns
    else:
        return stringify(n)

def wc(ibuf):
    "Wordcount -- as in unix wc"
    if type(ibuf) == type(""):
        ifd  = open(ibuf, 'r')
        ibuf = ifd.readlines()
        ifd.close()
    cc = [ sum([len(ln.split()) for ln in ibuf]) ]
    wc = [ len(ibuf), cc, sum([len(ln) for ln in ibuf]) ] # Standard format of wc -l output
    return wc

# AWS Support objects

class S3(object):
    CLIENT = None
    def __init__(self, bucket, **kwa):
        if not S3.CLIENT:
            S3.CLIENT = boto3.client('s3')
        self._bucket = bucket

    def __str__(self):
        return self._bucket

    def list(self, prefix='', **kwa):
        verbose = kwa.get('verbose')
        if verbose:
            del kwa['verbose']
        params = dict(Bucket=self._bucket, MaxKeys=kwa.get('MaxKeys', 123))
        if prefix:
            params['Prefix'] = prefix
        params.update(kwa)
        resp = S3.CLIENT.list_objects_v2(**params)
        contents = resp['Contents']
        if not verbose:
            return [c['Key'] for c in contents]
        return contents

    def upload(self, fp, obj_nm = None):
        if obj_nm == None:
            obj_nm = os.path.split(fp)[-1]
        resp = S3.CLIENT.upload_file(fp, self._bucket, obj_nm)
        return resp

    @property
    def bucket(self):
        return self._bucket

    @bucket.setter
    def bucket(self, v):
        self._bucket = v    
    
    @property
    def buckets(self):
        bux = self.CLIENT.list_buckets()
        bux = bux['Buckets']
        return [e['Name'] for e in bux]

# ________________________________________________________________
# Test Code

if __name__ == "__main__":
    import shlex
    buf = Capture("/bin/cat", "/etc/issue")
    print(f"Capture buf: {buf}")

if __name__ == "__main__":
    vl = [ 1999, 1999999, 1999999999, 1999999999999 ]
    for v in vl:
        print(f"{v}\t{Human_Size(v)}")
    # sys.exit(0)

if __name__ == "__main__":
    class TestApp:
        def __init__(self):
            self._subapps = dict()
            self['ps'] = SubApp("/bin/ps", "-efl")
            self['netstat'] = SubApp("/bin/ss", "-tonp")
            self['sysctl_net'] = SubApp("/sbin/sysctl", "net.ipv4")
            self['meminfo'] = RandomFile("/proc/meminfo")
        def __getitem__(self, k): return self._subapps[k]
        def __contains__(self, k): return k in self._subapps
        def __setitem__(self, k, v): self._subapps[k] = v

    app = TestApp()
    print("Syns:", app['netstat'].line_count('SYN_RECV'))
    print("Fins:", app['netstat'].line_count('FIN_WAIT'))
    print("Closes:", app['netstat'].line_count('CLOSE_WAIT'))
    print("Estab:", app['netstat'].line_count('ESTAB'))
    print("TimeWaits:", app['netstat'].line_count('TIME_WAIT'))

    # print("KeepAliveRequests:", app['nginx'].grep("keepalive_requests", lastword=True, unsemi=True)[0])
    print(app['meminfo'].grep('MemFree')[0])
    print("Web Forks:", app['ps'].line_count('nginx'))
    print(app['sysctl_net'].grep("net.ipv4.tcp_tw_reuse", index=-1), app['sysctl_net'].grep('net.ipv4.tcp_syn_retries')[-1], app['sysctl_net'].grep('net.ipv4.tcp_synack_retries')[-1])

if __name__ == "__main__":
    app = App(sys.argv[0], sys.argv[1:], foo=0, bar=1)
    histo = Histo()
    histo['a'] = 1000
    histo['b'] = 100
    histo['c'] = 5000
    histo['d'] = 2
    print(histo.textGraph())
    ts = "/job/TDDEVL/AR/00010/user/work.wook"
    ls = "/dd/shows/tddevl/ts/0001/"
    js = JobSysParse(ts)
    lp = JobSysParse(ls)
    print("%s: %s/%s/%s -- %s (%s)" % (ts, js['show'], js['seq'], js['shot'], js['suffix'], js.top()))
    print("%s: %s/%s/%s -- %s (%s)" % (lp, lp['show'], lp['seq'], lp['shot'], lp['suffix'], lp.top()))
    SendMail(subject='%s test' % sys.argv[0], to='mr.wook@gmail.com,mrwook@gmail.com,m.r.w.ook@gmail.com', body='Unit test of SendMail function', cc='wook@d2.com', smtphost='smtphost', From='wook@d2.com')
    sys.exit(0)
