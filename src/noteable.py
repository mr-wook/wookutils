#!/usr/bin/env python3
"notable.py -- pre-cursor to knowledge?"

if True:
	import datetime
	import json
	import os
	import re
	import sys
	import time


class NoteDB:
	def __init__(self, fn, backing_store='json'):
		self._fn = fn
		self._bs = backing_store
		self._data = self.load(self._fn, self._bs)

	def __len__(self):
		return len(self._data)

	def __getitem__(self, i):
		return self._data[k]

	def backup(self):
		if self._bs == 'json':
			bakfile = f"{self._fn}.bak"
			shutil(self._fn, bakfile)
		else:
			raise RuntimeError(f"Unknown Backing Store type {self._bs}")
		return

	def load(self, fn, backing_store = None):
		if not backing_store:
			backing_store = 'json'
		if backing_store == 'json':
			if not os.path.isfile(fn):
				raise [ ] # NULL DB not legal?: RuntimeError(f"NoteDB: File not found {fn}")
			sz = os.stat(fn)[6]
			if sz:
				return [ ]
			with open(fn, 'r') as ifd:
				ibuf = ifd.read(1024 * 1024 * 64) # Thassalottanotes!
			json_ = json.loads(ibuf)
			olist = [ ]
			for dict_ in json_:
				if 'name' not in dict_:
					note = Note(f"unnamed_{len(olist)+1}", **dict_)
				else:
					note = Note(**dict_)
				olist.append(note)
		else:
			raise RuntimeError(f"Unknown Backing Store type {backing_store}")
		return olist
 
	def save(self):
		writable = [note._params for note in self._notes]
		for params in writable:
			params['when'] = str(params['when'])
			# print(params)
		# print(f"Writing {len(writable)} records")
		with open(self._fn, 'w') as ofd:
			ofd.write(json.dumps(writable) + "\n")
		self._updated = False
		return


class Note:
	"An individual Note"
	UPDATEABLE = [ 'name', 'when', 'priority' ]
	def __init__(self, name = None, **kwa):
		if name:
			self._params = dict(name=name)
		self._params.update(kwa)
		if 'priority' not in self:
			self['priority'] = 9
		if 'when' not in self:
			self['when'] = self.now
		else:
			when_ = self['when']
			if type(when_) == type(""):
				when_ = datetime.datetime.fromisoformat(when_)
			self['when'] = when_


	def __getitem__(self, k):
		return self._params[k]

	def __contains__(self, k):
		return k in self._params

	def __setitem__(self, k, v):
		if k not in [ 'name', 'description', 'who', 'when', 'priority' ]:
			raise IndexError(f"Illegal param {k}")
		self._params[k] = v

	def __lt__(self, other):
		s_name, o_name = self['name'], other['name']
		if s_name != o_name:
			return s_name < o_name
		s_pri, o_pri = self['priority'], other['priority']
		if s_pri != o_pri:
			return s_pri < o_pri
		s_when, o_when = self['when'], other['when']
		if s_when != o_when:
			return s_when < o_when
		return False

	def __str__(self):
		olist = [ f"topic: {self['name']}", f"priority: {self['priority']}", str(self['when']), self['description']]
		ostr = "\n".join(olist)
		return ostr

	def display(self):
		print(str(self))

	def one_liner(self):
		print(self.one_line)

	@property
	def json(self):
		return json.dumps(self._params)

	@property
	def now(self):
		return datetime.datetime.utcnow()

	@property
	def ordinal(self):
		dt = self['when']
		if not isinstance(dt, datetime.datetime):
			if type(dt) == type(""):
				dt = datetime.datetime.fromisoformat(dt)
			elif type(dt) == type(1):
				return dt
		return dt.toordinal()

	@property
	def one_line(self):
		name_pri = f"{self['name']}({self['priority']})"
		return f"{name_pri:14s} {self.quick_when}: {self['description']}"

	@property
	def quick_when(self):
		when_ = self['when']
		# This probably induces reprehensible ambiguity;
		if type(when_) == type(""):
			when_ = datetime.datetime.fromisoformat(when_)
		return f"{when_.hour}:{when_.minute:02d} {when_.month}/{when_.day}/{when_.year}"


class Notes:
	"A note aggregator"
	def __init__(self, fn = None, *notes):
		self._updated = False
		if fn == None:
			fn = os.path.expanduser("~/.notes.json")
		self._fn = fn
		if notes:
			self._notes = list(notes)
			return
		if os.path.isfile(self._fn):
			self._notes = self.load(self._fn)
		else:
			self._notes = [ ]

	def __getitem__(self, k):
		if type(k) == type(1):
			return self._notes[k]
		elif type(k) == type(""):	# single (first) item filter
			return self._convert_to_filter(k)[0]

	def __len__(self):
		return len(self._notes)

	def append(self, note):
		self._notes.append(note)
		self.save()

	def after(self, when):
		today, yesterday = self._temporal_prelude()
		if when == "yesterday":
			remaining = [note for note in self._filter('after', yesterday)]
		if when.endswith("d"):
			when = int(when[:-1])
			remaining = [note for note in self._filter('after', when)]
		return remaining

	def before(self, when):
		today, yesterday = self._temporal_prelude()
		if when == 'today':
			remaining = [note for note in self._filter('before', today)]
		if when == "yesterday":
			remaining = [note for note in self._filter('before', yesterday)]
		if when.endswith("d"):
			when = int(when[:-1])
			remaining = [note for note in self._filter('before', when)]
		return remaining

	def during(self, when):
		# today, yesterday = self._temporal_prelude()
		if when in [ 'today', 'yesterday' ]:
			when = getattr(self, when)
		remaining = [note for note in self._notes if note.ordinal == when]
		return remaining

	def _dt_or_str(self, when):
		if isinstance(when, datetime.datetime):
			return when
		if when == 'today':
			return datetime.datetime.utcnow().toordinal()
		if when == 'yesterday':
			return datetime.datetime.utcnow().toordinal() - 1
		if when == 'tomorrow':
			return datetime.datetime.utcnow().toordinal() + 1
		if type(when) == type(""):
			if when.endswith("d"):
				prefix = when[:-1]
				if not prefix.isdigit():
					raise TypeError(f"{when} is not a valid specifier")
				prefix = int(prefix)
				return datetime.datetime.utcnow() + prefix
			when = datetime.datetime.toordinal(when)
		if type(when) == type(1):
			return datetime.datetime.utcnow().toordinal() + when
		return when

	def _temporal_prelude(self):
		today = datetime.datetime.utcnow()
		today = datetime.datetime.toordinal(today)
		yesterday = today - 1
		return today, yesterday

	def _temporal_filter(self, verb, ordinal):
		# verb is 'before', 'after', 'during', 'today', 'yesterday';

		def within(verb, ordinal):
			if verb == 'before':
				return [note for note in self._notes if note.ordinal < ordinal]
			if verb == 'after':
				return [note for note in self._notes if note.ordinal > ordinal]
			if verb == 'during':
				return [note for note in self._notes if note.ordinal == ordinal]
			if verb == 'today':
				return [note for note in self._notes if note.ordinal == ordinal]
			if verb == 'yesterday':
				return [note for note in self._notes if note.ordinal == self.yesterday]
			return [ ]

		today, yesterday = self._temporal_prelude()
		# print(f"Notes._temporal_filter: verb={verb} ordinal={ordinal} today={today} yesterday={yesterday}")
		if verb in [ 'after', 'before' ]:
			found = within(verb, ordinal)
			return found
		if verb == 'today':
			found = self.during(self.today)
			return found
		if verb == "yesterday":
			found = self.during(self.yesterday)
			return found
		return [ ]

	def _filter(self, verb, *args, **kwa):
		if 'from' in kwa:
			src = kwa['from']
		else:
			src = self._notes
		ordinal = args[0]
		if ordinal < (365 * 5):
			ordinal = self.today + ordinal
		# print(f"Notes._filter: verb={verb} ordinal={ordinal}")
		if verb in [ 'before', 'after', 'during', 'today', 'yesterday' ]:
			return self._temporal_filter(verb, ordinal)
		return None

	def _enumerate(self, notes = None, **kwa):
		topic = kwa.get('topic', None)
		i = 1
		olist = [ ]
		if notes == None:
			notes = self._notes
		for note in notes:
			if topic:
				if topic == note['name']:
					olist.append(f"{i:3d} {note.one_line}")
					i += 1
					continue
			else:
				olist.append(f"{i:3d} {note.one_line}")
			i += 1
		return olist

	def enumerate(self, notes = None, topic=None):
		if notes == None:
			notes = self._notes
		return self._enumerate(notes, topic=topic)

	def load(self, fn):
		if not os.path.isfile(fn):
			return [ ]
		if not os.stat(fn)[6]:
			return [ ]
		with open(fn, 'r') as ifd:
			ibuf = ifd.read(1024 * 1024 * 64) # Thassalottanotes!
		json_ = json.loads(ibuf)
		olist = [ ]
		for dict_ in json_:
			if 'name' not in dict_:
				note = Note(f"unnamed_{len(olist)+1}", **dict_)
			else:
				note = Note(**dict_)
			olist.append(note)
		return olist

	def pop(self, i: int):
		self._notes.pop(i)
		self._updated = True
 
	def save(self):
		writable = [note._params for note in self._notes]
		for params in writable:
			params['when'] = str(params['when'])
			# print(params)
		# print(f"Writing {len(writable)} records")
		with open(self._fn, 'w') as ofd:
			ofd.write(json.dumps(writable) + "\n")
		self._updated = False
		return

	def sort(self):
		self._notes.sort()

	@property
	def today(self):
		return datetime.datetime.utcnow().toordinal()

	@property
	def topics(self):
		topics = {note['name'] for note in self._notes}
		return topics

	@property
	def updated(self):
		return self._updated

	@property
	def yesterday(self):
		return self.today - 1
	

if __name__ == "__main__":
	class App:
		# TODO?: Add support for .noteable.last to use for last note modified?
		#   or .notable { last: n, auto-enumerate: False, auto-confirm: True }?
		def __init__(self, fn = None):
			self._notes = Notes()
			self._pname = sys.argv[0]
			if fn:
				if os.path.isfile(fn):
					self._notes.load()
			self._help = dict(edit=f"{self._pname} edit <index> (p <n>)|(n <name>|(a <append_description)(i <prepend_description>)|(c <desc>))")
			self._ops = { '+' : self._add, '-' : self._delete,
					      'after' : self._after, 'before' : self._before, 'during': self._during, 'edit' : self._edit,
					      'ls' : self._ls, 'pri' : self._prioritize, 'prio' : self._prioritize, 'priority' : self._prioritize,
					      'today' : self._today, 'yesterday' : self._yesterday }

		def _screen_args(self, args):
			done = False
			i = 0
			screen = { }
			while not done:
				arg = args[i]
				if '=' in arg:
					k, v = arg.split('=', 1)
					if k not in Note.UPDATEABLE:
						i += 1
						continue
					if k == 'priority':
						v = int(v)
					screen[k] = v
					args.pop(i)
				else:
					i += 1
				if i >= len(args):
					done = True
				continue
			return args, screen

		def _add(self, *args):
			# add name text ## Add name=name:description=join(text);
			args = list(args)
			args, screen = self._screen_args(args)
			name = args.pop(0)
			text = " ".join(args)
			screen['description'] = text
			note = Note(name, **screen)
			self._notes.append(note)
			note.display()
			return

		def _after(self, *args):
			when = args[0]
			# print(f"_after: when={when}")
			notes = self._notes.after(when)
			if not notes:
				return None
			print(f"[{len(notes)} since {when}]")
			# _ = 
			return "\n".join([note.one_line for note in notes])

		def _before(self, *args):
			# Collapse this into _since which handles before and after cases;
			when = args[0]
			notes = self._notes.before(when)
			if not notes:
				return None
			print(f"[{len(notes)} before {when}]")
			return "\n".join([note.one_line for note in notes])

		def _checkrange(self, i):
			if i not in range(len(self._notes)):
				return False, f"Index {i} out of range 1:{len(self._notes)}"
			return True, ""

		def _delete(self, *args):
			self._notes.sort()
			args = list(args)
			if not args:
				print("No note selected")
				return
			confirmed = False
			for switch_ in [ '-y', '-Y' ]:
				if switch_ in args:
					confirmed = True
					args.remove(switch_)
			while args:
				index = args.pop(0)
				if not index.isdigit():
					print("Index {index} is like, totally, not legit")
					continue
				i = int(index) - 1
				valid, errstr = self._checkrange(i)
				if not valid:
					return errstr
				note = self._notes[i]
				print(f"Note {i + 1}")
				note.display()
				if not confirmed:
					confirmation = input(f"Confirm [y/N]: ")
					if confirmation.lower() != "y":
						print(f"Not confirmed")
						return None
				self._notes.pop(i)
				print("Removed")
				self._notes.save()
			return None

		def display(self, rv):
			if type(rv) == None:
				return
			if type(rv) == type([ ]):
				for e in rv:
					if isinstance(e, Note):
						print(str(e))
				return
			if isinstance(rv, Notes):
				_ = [print(str(note)) for note in rv]
				return
			if type(rv) == type(""):
				print(rv)
			return

		def _during(self, *args):
			when = args[0]
			notes = self._notes.during(when)
			if not notes:
				return None
			print(f"[{len(notes)}] during {when}")
			return "\n".join([note.one_line for note in notes])

		def _edit(self, *args):
			def update(i, k, v):
				note = self._notes[i]
				note[k] = v
				conf = input(f"Confirm update {note.one_line} [Y/n]: ")
				if not (conf or conf.lower() == 'y'):
					print("Confirmed")
					self._notes.save()
				else:
					print("Update declined")
					sys.exit(0)
				return note.one_line

			args = list(args)
			if 'help' in args:
				return self._help['edit']
			i = int(args.pop(0)) - 1
			edit_cmd = args.pop(0)
			valid, errstr = self._checkrange(i)
			if not valid:
				return errstr
			# a: append, i: insert, c: change, p: priority, n: name
			if edit_cmd.lower() not in [ 'a', 'c', 'i', 'n', 'p']:
				return "Unrecognized edit command {edit_cmd}"
			edit_cmd = edit_cmd.lower()
			# self._notes.sort()
			if edit_cmd == 'p':
				return update(i, 'priority', int(args[0]))
			if edit_cmd == 'n':
				return update(i, 'name', args[0])
			if edit_cmd == "c":
				return update(i, 'description', " ".join(args))
			if edit_cmd == "a":
				return update(i, 'description', self._notes[i]['description'] + "; " + " ".join(args))
			if edit_cmd == "i":
				return update(i, 'description', " ".join(args) + "; " + self._notes[i]['description'])
			print(f"Don't understand edit command {edit_cmd}")
			sys.exit(1)

		def _ls(self, *args):
			# Ignore args (for now)
			# TODO: support ./noteable.py ls [<topic> ...] [-N]
			enumerate = False
			args = list(args)
			if '-N' in args:
				enumerate = True
				args.remove('-N')
			# self._notes.sort()
			if args:
				topics = [ ]
				for topic in args:
					if enumerate:
						topics += self._notes.enumerate(None, topic)
				return "\n".join(topics)
			if enumerate:
				return "\n".join(self._notes.enumerate())
			_ = [note.one_liner() for note in self._notes]
			return None

		def _prioritize(self, *args):
			args = list(args)
			if len(args) < 2:
				return f"Need index and new priority in that order"
			self._notes.sort()
			i, prio = int(args.pop(0)) - 1, int(args.pop(0))
			self._notes[i]['priority'] = prio
			self._notes.save()
			return self._notes[i].one_line

		def run(self, *args):
			args = list(args)
			if not args:
				print(f"[{len(self._notes)} loaded]")
				return
			op = args.pop(0)
			if op in self.topics:
				notes = [print(note.one_line) for note in self._notes if note['name'] == op]
				sys.exit(0)
			if op not in self._ops:
				print(f"Unknown operation {op}")
				sys.exit(1)
			func = self._ops[op]
			rv = func(*args)
			self.display(rv)
			sys.exit(0)

		def _today(self, *args):
			notes = [note.one_line for note in self._notes.after('yesterday')]
			return "\n".join(notes)

		def _yesterday(self, *args):
			notes = [note.one_line for note in self._notes.during('yesterday')]
			return "\n".join(notes)

		@property
		def topics(self):
			return self._notes.topics

		@property
		def updated(self):
			return self._notes.updated
		

	NOTESFILE = os.path.expanduser("~/notes.notes")
	app = App(NOTESFILE)
	pname, *args = sys.argv
	app.run(*args)
	if app.updated:
		app.save()
	sys.exit(0)

	# cli: ./noteable.py - <#> ## delete note #
	# cli: ./noteable before yesterday|<n>d
	# cli: ./noteable after yesteray|<n>d
	# cli: noteable edit <n> field=value . . .
