#Copyright (c) Hans Andersson 2011
#All rights reserved.

import os, random, sys, math
import re, urllib.request

cwd = os.getcwd()
sys.path.append("../")
import Decision
os.chdir(cwd)

def getPlayersCountRange(): return (5, 5)

"""
Even better: rate each security by how much I like it,

Do I want to reconstitute the portfolio entirely at each round?
	(Look at every security on the market?) Probably too expensive...
Or do I want to decide first whether to add a position?
	if so, go through the securities I don't have and pick one to add,
		then return to the top (add another position?)

1. Sell current positions?
	for each security, sell another or hold?
2. Buy  new     positions?
	add a position?
"""
	
class Game:
	def __init__(self, agents):
		#agents : Agent list
		assert type(agents) in (type(list()), type(set()))
		assert not len(agents) < getPlayersCountRange[0] and not len(agents) > getPlayersCountRange[1]
		self.players = [Player(agent) for agent in agents]
	
	def doRound(self):
		
	
	def getDictForPlayer(self, player): #float dictionary
		#player : Player
		return {"game":{"safe":min(float(len([corp for corp in self.corporations if corp.isSafe()])) / float(len(self.corporations)), 1.0), "size":min(float(max([len(corp.tiles) for corp in self.corporations])) / 41.0, 1.0), "full":float(len(self.tilesPlaced))/float(self.boardCols*self.boardRows), "oths":1.0 - (1.0/(float(len(self.players))-1.0))}, "agnt":player.getDict()}
	
	def getCompletion(self): #boolean
		

	def getPerformance(self): return max([player.wallet for player in self.players])
	
	def finalize(self): for player in self.players: player.sellout()
	
	def getRanking(self):
		return [(player.agent, player.wallet) for player in sorted(self.players, key = lambda player: player.wallet, reverse = True)]
	
	def __str__(self): return ""

class Transaction:
	def __init__(self, player, certificate, action, proceeds = 0.0):
		self.player = player
		self.certificate = certificate
		self.proceeds = proceeds
		
		actions = ["held", "sold", "excd"]
		if action in actions: action = actions.index(action)
		assert (type(action) == type(int()) and not action < 0 and action < len(actions))
		self.action = action
	
	def getDictForPlayer(self):
		return {}

class Player:
	def __init__(self, agent, wallet = 5000.0): #void / None
		#agent : Agent
		#wallet : int
		self.agent = agent
		self.positions = {}
		self.wallet = wallet
	
	def buy(self, security, quantity, price, fee): #void / None
		#security : Security
		assert isinstance(security, Security)
		assert type(quantity) == type(int()) and quantity > 0
		assert type(price) == type(double()) and price > 0.0
		transactionCost = fee + price * double(quantity)
		assert not self.wallet < transactionCost
		if security not in self.positions: self.positions[security] == 0
		self.wallet -= transactionCost
		self.positions[security] += quantity
	
	def sell(self, security, quantity, price, fee): #void / None
		#security : Security
		assert isinstance(security, Security)
		assert type(quantity) == type(int()) and quantity > 0
		assert security in self.positions and not self.positions[security] < quantity
		assert type(price) == type(double()) and price > 0.0
		transactionYield = -fee + price * double(quantity)
		assert not self.wallet < transactionYield
		self.positions[security] -= quantity
		self.wallet += transactionYield
		if self.positions[security] == 0: del self.positions[security]
	
	def getDict(self): #dictionary
		assert not self.wallet < 0
		return {"lqdt":self.wallet / (5000.0 + self.wallet)}
	
	#End-Of-Game
	def sellout(self): #None
		for certificate in self.stock.copy(): self.sell(certificate)

