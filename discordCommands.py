import re
import math
import secrets
from datetime import datetime

UPDATE_FLAG_MIN_DELTA = 60
AUTH_TIMEOUT = 190

class InscriptionCmd:
	
	# two ordered lists of tuples (name, type)
	MANDATORY_ARGS = []
	OPTIONAL_ARGS = [('x', int), ('y', int)]
	# TODO support for *args ? possible but more work to do and not needed for now
	
	def __init__(self, author, accepted_args):
		# add remaining preconditions
		if len(accepted_args) != 0 and len(accepted_args) != 2:
			raise AttributeError(f"Both x and y or neither should be given.") # TODO player send
		self.author = author
		self.user_pos = None
		if accepted_args:
			self.user_pos = (accepted_args[0], accepted_args[1])
		else:
			self.user_pos = self.parse_name(str(self.author.display_name))

	async def run(self, client):
		#self.client = client
		# it's a coroutine, the whole thing is here :)
		if self.author.id not in client.seen_ppl:
			await self.author.send("Salutations!")
			client.seen_ppl.add(self.author.id)

		#TODO: prevent concurrent requests... (done with bot_vote.py:152 ?)

		if not self.user_pos:
			await self.author.send("""Pour vous authentifier il me faut vos coordonnées!
- soit par argument: /inscription X Y
- soit dans votre pseudo sous la forme [018:006]
""") # TODO move to init
			return

		# TODO: make this a function that checks if we can expect an update or not
		# TODO change something as we should access _falg vars outside of class
		if client._flag_update_task or not client._flag:
			await self.author.send("Merci de patienter quelques instants..")

		flag = await client.get_flag()
		if not flag:
			await self.author.send("Ouch! J'ai du mal à accéder au site du drapeau, merci de revenir plus tard.")
			return

		idx_in_flag = self.flag_coords_to_index()
		if idx_in_flag > len(flag):
			await self.author.send("Duh! Ces coordonnées ne semblent pas appartenir au drapeau. Bye!")
			return
		pixel_data = flag[idx_in_flag]
		# no need for the flag anymore, release it
		flag = None

		hex_col = pixel_data['hexColor'].upper() # TODO: check present ?

		# generate auth_color, must be different than hex_col
		auth_color = hex_col
		while auth_color == hex_col:
			auth_color = f"#{secrets.token_hex(3).upper()}"

		author_name = await client.get_author_name(pixel_data['author'])
		if not author_name:
			author_name = "(invalid)"

		await self.author.send(f"""Pour me prouver ton unicité dirty-biologico-pixelique en tant que "{author_name}", change la couleur de ton pixel avec ce code:
```{auth_color}```Au cas où voilà le lien du drapeau: <https://fouloscopie.com/experiment/7>.
Je reviens dès j'aurai jeté un oeil au drapeau (toutes les {UPDATE_FLAG_MIN_DELTA}s) et que ton pixel aura changé !
""")

		start = datetime.now()
		while (datetime.now() - start).total_seconds() < AUTH_TIMEOUT:
			flag = await client.wait_next_flag_update()
			new_hex_col = flag[idx_in_flag]['hexColor'].upper()
			if new_hex_col == hex_col:
				continue # TODO: display "alive" message if delta was already long enough for the user to change his pixel ?
			elif new_hex_col != auth_color:
				await self.author.send("La couleur de ton pixel a changé mais pas de la bonne couleur :/ Demande annulée.")
				return
			else:
				break
		else:
			await self.author.send("Ton pixel n'a pas pu être vérifié dans le temps imparti. Demande annulée.")
			return

		# better be sure, in case above logic changes
		assert new_hex_col == auth_color

		token = secrets.token_hex(16)

		await self.author.send(f"""Apparemment c'est bien toi. Voici ton token, ne le partage pas:
```{token} // prototype, ce token ne sera pas utilisable```Si tu le perds, refais la procédure et l'ancien deviendra invalide.
Pour l'utiliser il suffira de me le donner (ou à un autre système peut-être..) en privé lors des sessions de vote.
Tu peux maintenant recoloriser ton pixel comme bon te semble.""") # TODO warn after 5 min when guy can change is color back (and tell him what color it was)

		# TODO: gen token + maintain json database

	def parse_name(self, name):
		m = re.findall("(\d+)[,:;/-](\d+)", name)
		if len(m) < 1:
			return False
		X, Y = m[0]
		pos = max(0, int(X)), max(0, int(Y))
		return pos

	# un peu de maths ne font pas de mal
	def flag_index_to_coords(self, index):
		# pattern:
		#  0  1  4  6 12 15
		#  2  3  5  7 13 16
		#  8  9 10 11 14 17
		# 18 ..
		# pattern repeats at each rank X:
		# fill bottom line of size 2 * X L2R
		# fill 2 vertical lines on the right of size (X + 1) L2R T2B
		# this is +4X+2 pixels per rank.
		# computing the starting count of pixels at each rank (== first pixel index)
		# is equivalent to summing an arithmetic sequence
		# this sum equals 2X², so rank 1 starts with 2 pixels rank 2 starts with 8 pixels
		# inversing the equation we can find the rank of a pixel index:
		rank = math.floor(math.sqrt(index / 2)) # 7 gives 1, 8 gives 2 
		# then get the first pixel index
		base = 2 * rank * rank
		# now let's find our index in the inner pattern
		d = index - base
		bline_size = 2 * rank
		if d < bline_size: # pixel in bottom line
			return (d + 1, rank + 1)
		d -= bline_size
		vline_size = rank + 1
		if d < vline_size: # pixel in first vertical line
			return (bline_size + 1, d + 1)
		# pixel in second vertical line
		d -= vline_size
		return (bline_size + 1 + 1, d + 1)


	# see flag_index_to_coords for details
	def flag_coords_to_index(self):
		x, y = self.user_pos
		# shift coords so that (0, 0) is the origin
		x -= 1
		y -= 1
		# check if pixel is in a bottom line of the pattern
		bline_size = 2 * y # y == rank if bottom line
		if x < bline_size:
			base = 2 * y * y
			return base + x
		# otherwise pixel is in vertical lines
		rank = math.floor(x / 2)
		base = 2 * rank * rank
		idx = base + 2 * rank + y# base + bline_size + y
		if x & 1:
			idx += rank + 1 # vline_size
		return idx



COMMAND_CHAR = '/'
defined_commands = {'inscription' : InscriptionCmd}
	
def parse_message(author, message):
	if not message[0] == COMMAND_CHAR:
		print(f'"{message}" is not a command.')
		return

	words = re.split(r"\s+", message)
	name = words[0][1:]
	if name in defined_commands:
		command = defined_commands[name]
		nb_args = len(words) - 1
		if nb_args < len(command.MANDATORY_ARGS):
			raise AttributeError(f"Missing {len(command.MANDATORY_ARGS) - nb_args} arguments for command '{name}'.") # TODO player send
		elif nb_args >  len(command.MANDATORY_ARGS) + len(command.OPTIONAL_ARGS):
			raise AttributeError(f"Too much arguments for command '{name}'. Expecting beetwen {len(command.MANDATORY_ARGS)} and {len(command.MANDATORY_ARGS) + len(command.OPTIONAL_ARGS)} got {nb_args}") # TODO player send

		accepted_args = []
		for i, word in enumerate(words[1:]):
			# mandatory args should always be before optional ones
			if i < len(command.MANDATORY_ARGS):
				try:
					parsed = command.MANDATORY_ARGS[i][1](word) # we try to parse to the wanted type
					accepted_args.append(parsed)
				except TypeError:
					raise AttributeError(f"Argument '{word}' is expected to be of type {command.MANDATORY_ARGS[i][1]}.") # TODO player send
			elif i < len(command.OPTIONAL_ARGS) + len(command.MANDATORY_ARGS):
				j = i - len(command.MANDATORY_ARGS)
				try:
					parsed = command.OPTIONAL_ARGS[j][1](word)
					accepted_args.append(parsed)
				except TypeError:
					raise AttributeError(f"Argument '{word}' is expected to be of type {command.OPTIONAL_ARGS[j][1]}.") # TODO player send
			else:
				# This is a real error as it should already be handeld by check above
				AttributeError(f"Too much arguments for command '{name}'. Expecting beetwen {len(command.MANDATORY_ARGS)} and {len(command.MANDATORY_ARGS) + len(command.OPTIONAL_ARGS)} got {nb_args}")
		return command(author, accepted_args)
	else:
		print(f"Unhandeld command : {message} (known commands are {defined_commands})")


#if words[0] == "/inscription":
#	await self.on_cmd_inscription(message, words[1:])
#elif words[0] == "/echo":
#	await message.reply(" ".join(words[1:]))
