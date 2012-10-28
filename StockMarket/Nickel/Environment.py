#Copyright (c) Hans Andersson 2011
#All rights reserved.

import os, random, sys, math
cwd = os.getcwd()
sys.path.append("../")
import Decision
os.chdir(cwd)


  #########################################
  ### IMPLEMENTATION OF <<ACQUIRE (R)>> ###
  #########################################

############################################
###         Check it out here:           ###
### http://en.wikipedia.org/wiki/Acquire ###
############################################


#ideas for other features (i.e. potentially-significant inputs to the neural network):
#whether player can found a corporation
#whether one tile is adjacent to others the player holds
#Turn class that can describe the entire turn a player took
#  purchases history (at least for one round)
#  comparison to another turn (especially the last turn a player took)

def getPlayersCountRange(): return (2, 6)

class Game:
	def __init__(self, agents):
		#agents : Agent list
		assert type(agents) in (type(list()), type(set()))
		agents = list(agents)
		random.shuffle(agents)
		self.players = [Player(agent) for agent in agents]
		assert len(self.players) > 1
		
	
	def doRound(self): #None
		pass
			
	#represents the game as a dictionary, for use in the neural network, relative to a player's perspective
	def getDictForPlayer(self, player): #float dictionary
		#player : Player
		return {}
	
	#part of Game "interface"
	#how far gone is the game (used in GeneticArena.autorun() to break the loop when the game is done)
	def getCompletion(self): #boolean
		return 100.0
	
	def getPerformance(self): return sum([player.wallet for player in self.players])
	
	#part of Game "interface"
	#completes any endgame cleanup and returns the list of players in descending order of score
	def finalize(self): #Agent list
		pass
	
	#part of Game "interface"
	#returns a dictionary that says how well everybody did
	def getRanking(self):
		return [(player.agent, player.wallet) for player in sorted(self.players, key = lambda player: player.wallet, reverse = True)]
	
	#enables console play (returns a console representation of the game)
	def __str__(self): #string
		return ""

#I haven't implemented use of this class, yet...
#(unused at present)
class Turn:
	def __init__(self, player):
		self.player = player
		self.wallet = player.wallet
		
		#whichever corporation expanded as a result of the turn
		self.corporation = None
		self.tile = None
		self.purchases = set()
		self.transactions = set()
		
	def getDictForPlayer(self):
		return {}

class Player:
	def __init__(self, agent): #void / None
		#agent : Agent
		#wallet : int
		self.agent = agent
		self.hand = set()
		self.points = 0
		self.wallet = 0
	
	def getDict(self): #dictionary
		return {}