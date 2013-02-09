import pygame
from pygame.locals import *
import random
import numpy
import struct
import pyaudio
import math

board = ""
board_height = 0
board_width = 0
ghosts = []
volume = 0


INITIAL_TAP_THRESHOLD = 0.010
FORMAT = pyaudio.paInt16 
SHORT_NORMALIZE = (1.0/32768.0)
CHANNELS = 2
RATE = 44100  
INPUT_BLOCK_TIME = 0.05
INPUT_FRAMES_PER_BLOCK = int(RATE*INPUT_BLOCK_TIME)
# if we get this many noisy blocks in a row, increase the threshold
OVERSENSITIVE = 15.0/INPUT_BLOCK_TIME                    
# if we get this many quiet blocks in a row, decrease the threshold
UNDERSENSITIVE = 120.0/INPUT_BLOCK_TIME 
# if the noise was longer than this many blocks, it's not a 'tap'
MAX_TAP_BLOCKS = 0.15/INPUT_BLOCK_TIME

def get_rms( block ):
    # RMS amplitude is defined as the square root of the 
    # mean over time of the square of the amplitude.
    # so we need to convert this string of bytes into 
    # a string of 16-bit samples...

    # we will get one short out for each 
    # two chars in the string.
    count = len(block)/2
    format = "%dh"%(count)
    shorts = struct.unpack( format, block )

    # iterate over the block.
    sum_squares = 0.0
    for sample in shorts:
        # sample is a signed short in +/- 32768. 
        # normalize it to 1.0
        n = sample * SHORT_NORMALIZE
        sum_squares += n*n

    return math.sqrt( sum_squares / count )

class TapTester(object):
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.stream = self.open_mic_stream()
        self.tap_threshold = INITIAL_TAP_THRESHOLD
        self.noisycount = MAX_TAP_BLOCKS+1 
        self.quietcount = 0 
        self.errorcount = 0

    def stop(self):
        self.stream.close()

    def find_input_device(self):
        device_index = None            
        for i in range( self.pa.get_device_count() ):     
            devinfo = self.pa.get_device_info_by_index(i)   
            print( "Device %d: %s"%(i,devinfo["name"]) )

            for keyword in ["mic","input"]:
                if keyword in devinfo["name"].lower():
                    print( "Found an input: device %d - %s"%(i,devinfo["name"]) )
                    device_index = i
                    return device_index

        if device_index == None:
            print( "No preferred input found; using default input device." )

        return device_index

    def open_mic_stream( self ):
        device_index = self.find_input_device()

        stream = self.pa.open(   format = FORMAT,
                                 channels = CHANNELS,
                                 rate = RATE,
                                 input = True,
                                 input_device_index = device_index,
                                 frames_per_buffer = INPUT_FRAMES_PER_BLOCK)

        return stream

    def tapDetected(self):
        print "Tap!"

    def listen(self):
        try:
            block = self.stream.read(INPUT_FRAMES_PER_BLOCK)
        except IOError, e:
            # dammit. 
            self.errorcount += 1
            print( "(%d) Error recording: %s"%(self.errorcount,e) )
            self.noisycount = 1
            return

        return get_rms(block)

tt = TapTester()
pacman = None
score = 0

def getLoudness():
	global tt
	return tt.listen()



class pacman(object):
	def __init__(self):
		global pacman
		self.x = 9
		self.y = 9
		self.color = pygame.Color(255, 255, 0, 255)
		pacman = self


	def draw(self, screen):
		pygame.draw.circle( screen, self.color, ( self.x * 20 + 10, self.y * 20 + 10), 10 )

	def actually_move(self, x, y ):
		global board, board_width, score, ghosts

		pos = (x,y)
		for g in ghosts:
			gpos = g.getPos()
			if gpos[0] == pos[0] and gpos[1] == pos[1]:
				gameover()


		if get_cell(x, y) is ".":
			place = x + ( y * board_width )
			board = board[:place] + " " + board[place+1:]
			score += 1
		if get_cell(x, y) is "c":
			place = x + ( y * board_width )
			board = board[:place] + " " + board[place+1:]
			score += 5
		if is_filled( x, y ):
			return False
		else:
			self.x = x
			self.y = y

	# takes the position as a tuple.
	def try_move(self, pos ):
		global board
		if not is_filled( pos[0], pos[1] ):
			self.actually_move(pos[0], pos[1])
			return True
		else:
			return False

	def move(self):
		x = self.x
		y = self.y
		spaces = [ (x, y+1), (x, y-1), (x+1, y), (x-1, y) ]
		toRemove = []
		for space in spaces:
			if is_filled( space[0], space[1] ):
				toRemove.append(space)

		for f in toRemove:
			spaces.remove(f)

		self.try_move(spaces[random.randrange(0, len(spaces))])


class ghost(object):
	def __init__(self, x, y, color = pygame.Color(255, 0, 0, 255) ):
		global ghosts
		self.color = color
		self.x = x
		self.y = y
		ghosts.append(self)

	def draw(self, screen):
		global board_width, board_height
		#pygame.draw.rect( screen, self.color, pygame.Rect( (self.x * board_width), (self.y * board_height), 20, 20), 0 )
		draw_rect( screen, self.x * 20, self.y*20, self.color, 20)

	# takes the position as a tuple.
	def try_move(self, pos ):
		global board
		if not is_filled( pos[0], pos[1] ):
			self.x = pos[0]
			self.y = pos[1]
			return True
		else:
			return False

	def move(self):
		x = self.x
		y = self.y
		spaces = [ (x, y+1), (x, y-1), (x+1, y), (x-1, y) ]
		toRemove = []
		for space in spaces:
			if is_filled( space[0], space[1] ):
				toRemove.append(space)

		for f in toRemove:
			spaces.remove(f)

		self.try_move(spaces[random.randrange(0, len(spaces))])

	def getPos(self):
		return (self.x, self.y)

def draw_rect( screen, x, y, color, size ):
	pygame.draw.rect( screen, color, pygame.Rect(x, y, size, size), 0 )

# note: X and Y here refer to board coordinates.
def draw_dot( screen, x, y, color = pygame.Color(128, 255, 128, 255) ):
	pygame.draw.circle( screen, color, ( x * 20 + 10, y * 20 + 10), 5 )

def load_map(name):
	filename = name+".txt"
	f = open(filename)

	boardString = ""
	boardWidth = 0
	boardHeight = 0

	for line in f:
		l2 = line.strip("\n").replace(" ", ".")
		boardWidth = len(l2)
		boardHeight += 1
		boardString = boardString + l2

	return (boardString, (boardWidth, boardHeight) )


def is_filled( x, y ): # doesn't check for collisions with ghosts since that prevents the player from dying
	return get_cell(x,y) is "w"

def get_cell( x, y ):
	global board, board_width, board_height
	# detect edge cases
	if x < 0 or y < 0 or x > board_width or y > board_height:
		return False
	
	newpos = x + (y * board_width)
	return board[newpos]


def draw_board( screen ):
	global board, board_width, board_height

	white = pygame.Color(255, 255, 255, 255 )

	for x in range(0,board_width):
		for y in range(0,board_height):
			if is_filled( x, y ):
				draw_rect(screen, x*20, y*20, white, 20)
			if get_cell(x,y) is ".":
				draw_dot(screen, x, y )
			if get_cell(x,y) is "c":
				draw_dot(screen, x, y, pygame.Color(255, 0, 0, 255))
			if get_cell(x,y) is "p":
				draw_dot(screen, x, y, pygame.Color(0, 0, 255, 255))


def draw_grid(screen):
	white = pygame.Color(255, 255, 255, 50 )
	for i in range(0, 20):
		pygame.draw.line(screen, white, (20*i, 0), (20*i, 400) )

	for j in range(0, 20):
		pygame.draw.line(screen, white, (0, 20*j), (400, 20*j) )


def gameover():
	global score
	print "Your score was: " + str(score)
	#exit()

def main():
	global board, board_width, board_height, ghosts, pacman, volume
	
	## Load the board from the test map file.
	temp = load_map("map")
	board = temp[0]
	board_width = temp[1][0]
	board_height = temp[1][1]

	screen = pygame.display.set_mode((380,440), DOUBLEBUF | FULLSCREEN) # Make this fullscreen for presentation.

	clock = pygame.time.Clock()

	# Create some test ghosts.
	ghost(1, 1)
	ghost(18,1, pygame.Color(0, 255, 0, 255 ))

	pacman()

	last_tick = pygame.time.get_ticks()
	ticks_per_frame = 300

	while True:
		#gameloop

		
		# Logic step
		if (pygame.time.get_ticks() - last_tick ) > ticks_per_frame:
			last_tick = pygame.time.get_ticks()

			pacman.move()

			# draw all the ghosts
			for g in ghosts:
				g.move()

		# Do the drawing
		screen.fill( pygame.Color( 0, 0, 0, 255 ) )
		draw_board(screen)
		draw_grid(screen)




		# Draw the volume indicator
		c = None
		volume += getLoudness()
		volume -= 0.05
		volume = volume * volume
		
		if volume < 0:
			volume = 0.01
		
		if volume > 0.8:
			volume *= 0.8

		if volume > 1:
			volume = 0.99

		if ( volume ):
			c = pygame.Color(0, int(255*volume), 0, 150 )


		pygame.draw.rect( screen, c, pygame.Rect(200*(1-volume), 400, 380*volume, 40), 0 )
		

		# draw all the ghosts
		for g in ghosts:
			g.draw(screen)
		pacman.draw(screen)
		

		# Finish the drawing and place it on the screen.
		pygame.display.flip()


		for event in pygame.event.get():
			if event.type == QUIT: ## defined in pygame.locals
				pygame.quit()
				exit()




if __name__ == '__main__':
	main()