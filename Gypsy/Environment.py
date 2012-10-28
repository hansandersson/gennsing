#Copyright (c) Hans Andersson 2012
#All rights reserved.

import os, random, sys, math
cwd = os.getcwd()
sys.path.append("../")
import Decision
os.chdir(cwd)


  ###################################
  ### IMPLEMENTATION OF <<GYSPY>> ###
  ###################################

def getPlayersCountRange(): return (4, 4)

class Game:
	def __init__(self, agents):
		#agents : Agent list
		assert type(agents) in (type(list()), type(set())) and \
		(len(agents) == 3 or len(agents) == 4)
		agents = list(agents)
		random.shuffle(agents)
		self.players = [Player(agent) for agent in agents]
		
	
	#part of Game "interface"
	#PRIMARY, ABSTRACT METHOD FOR CALLING AT RUNTIME
	def doRound(self): #None
		#lead
		#follow
		#
	
	
	
	#represents the game as a dictionary, for use in the neural network, relative to a player's perspective
	def getDictForPlayer(self, player): #float dictionary
		#player : Player
		return {"game":{"safe":min(float(len([corp for corp in self.corporations if corp.isSafe()])) / float(len(self.corporations)), 1.0), "size":min(float(max([len(corp.tiles) for corp in self.corporations])) / 41.0, 1.0), "full":float(len(self.tilesPlaced))/float(self.boardCols*self.boardRows), "oths":1.0 - (1.0/(float(len(self.players))-1.0))}, "agnt":player.getDict()}
	
	#part of Game "interface"
	#how far gone is the game (used in GeneticArena.autorun() to break the loop when the game is done)
	def getCompletion(self): #boolean
		percentSafe = 100.0 * float(len([corp for corp in self.corporations if corp.isSafe()])) / float(len(self.getCorporationsActive())) if len(self.getCorporationsActive()) > 0 else 0.0
		largestSizeOver41 = 100.0 * float(max([len(corp.tiles) for corp in self.corporations])) / 41.0
		#self.stuck starts each round as None
		#whenever some agent places a tile, self.stuck = False
		#if, at end of player turns, self.stuck still None, then reshuffle tiles;
		#if anybody now has a tile they can place next round, then self.stuck = False
		#finally, at very end of round, if self.stuck still None, then set it True
		#have to use three values because checks getCompletion in middle of round...
		#    we want to declare game stuck only at end of round
		return min(max(percentSafe, largestSizeOver41, 100.0 if self.stuck == True else 0.0), 100.0)
	
	def getPerformance(self): return sum([player.wallet for player in self.players])
	
	#part of Game "interface"
	#completes any endgame cleanup and returns the list of players in descending order of score
	def finalize(self): #Agent list
		for corp in self.getCorporationsActive(): corp.payout()
		for player in self.players: player.sellout()
	
	#part of Game "interface"
	#returns a dictionary that says how well everybody did
	def getRanking(self):
		return [(player.agent, player.wallet) for player in sorted(self.players, key = lambda player: player.wallet, reverse = True)]
	
	#enables console play (returns a console representation of the game)
	def __str__(self): #string
		console = "  " + "".join([str(c).center(3) for c in range(self.boardCols)])
		for r in range(self.boardRows):
			console += "\n" + Tile.nameForRow(r) + " "
			for c in range(self.boardCols):
				console += (self.board[r][c].corporation.consoleColor if (self.board[r][c].corporation != None and self.board[r][c].corporation.consoleColor != None) else "") + " " + ((self.board[r][c].corporation.name[0]) if self.board[r][c].corporation != None else ("*" if self.board[r][c] in self.tilesPlaced else " ")) + " \x1b[0m"
		return self.console + console

class Suit:
	@classmethod
	def symbols(self):
		return ("S", "H", "D", "C")
	
	@classmethod
	def names(self):
		return ("Spades", "Hearts", "Diamonds", "Clubs")
	
	def __init__(self, symbol):
		assert symbol in self.__class__.symbols()
		self.symbol = symbol
		self.cards = set()
	
	def __str__(self):
		return self.symbol
	
	def __gt__(self, otherSuit):
		assert self.__class__ == otherSuit.__class__
		return self.__class__.symbols().index(self.symbol) < self.__class__.symbols().index(otherSuit.symbol)
	
	def __lt__(self, otherSuit):
		assert self.__class__ == otherSuit.__class__
		return self.__class__.symbols().index(self.symbol) > self.__class__.symbols().index(otherSuit.symbol)
	
	def __eq__(self, otherSuit):
		assert self.__class__ == otherSuit.__class__
		return not self > otherSuit and not self < otherSuit
	
	def __ne__(self, otherSuit):
		return not self == otherSuit

class Card:
	def __init__(self, suit, rank):
		assert not rank < 1 and not rank > 13
		assert suit.__class__ == Suit
		self.rank = rank
		self.suit = suit
		suit.cards |= self
	
	def isGypsy(self):
		return self.suit.symbol == "C" and self.rank == 8
	
	def __str__(self):
		if self.isGypsy(): return "GY"
		return (str(self.suit) + (["A"].append(map(str, range(2, 9))).append(["J", "Q", "K"]))[self.rank]
	
	def __gt__(self, otherCard):
		if self.isGypsy(): return True
		if self.suit == otherCard.suit: return self.rank > otherCard.rank
		return self.suit > otherCard.suit
	
	def __eq__(self, otherCard):
		return self.suit == otherCard.suit and self.rank == otherCard.rank
	
	def __lt__(self, otherCard):
		return not self > otherCard and not self == otherCard
	
	def __ne__(self, otherCard):
		return self > otherCard or self < otherCard


class Player:
	def __init__(self, agent, wallet = 6000): #void / None
		#agent : Agent
		#wallet : int
		self.agent = agent
		self.tiles = set()
		self.stock = set()
		self.wallet = wallet
	
	def buy(self, certificate): #void / None
		#certificate : Certificate
		assert certificate.owner == None
		assert not self.wallet < certificate.corporation.getStockPrice()
		self.stock.add(certificate)
		certificate.owner = self
		
		self.wallet -= certificate.corporation.getStockPrice()
	
	def sell(self, certificate): #void / None
		#certificate : Certificate
		assert certificate in self.stock
		assert certificate.owner == self
		self.stock.remove(certificate)
		certificate.owner = None
		
		self.wallet += certificate.corporation.getStockPrice()
	
	def draw(self, tiles): #Tile
		#tiles : Tile set
		assert len(tiles) > 0
		draw = random.choice(list(tiles))
		tiles.remove(draw)
		self.tiles.add(draw)
		assert not len(self.tiles) > 7
		return draw
	
	def getDict(self): #dictionary
		assert not self.wallet < 0
		return {"lqdt":self.wallet / (6000.0 + self.wallet)}
	
	#End-Of-Game
	def sellout(self): #None
		for certificate in self.stock.copy(): self.sell(certificate)