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
		
		self.boardRows = 9
		self.boardCols = 12
		self.board = [[Tile(r, c) for c in range(self.boardCols)] for r in range(self.boardRows)]
		self.tilesUndrawn = set([self.board[r][c] for c in range(self.boardCols) for r in range(self.boardRows)])
		self.tilesPlaced = set()
		while len(self.tilesPlaced) < len(self.players):
			randomDraw = random.choice(list(self.tilesUndrawn))
			if len(self.getAdjoiningLoners(randomDraw)) == 0:
				self.tilesPlaced.add(randomDraw)
				self.tilesUndrawn.remove(randomDraw)
				
		for player in self.players:
			for i in range(7):
				player.draw(self.tilesUndrawn)
		
		#according to the game rules...
		self.corporations = [Corporation("Tower", 0, '\x1b[43m'), Corporation("Luxor", 0, '\x1b[42m'), Corporation("American", 1, '\x1b[44m'), Corporation("Worldwide", 1, '\x1b[47m'), Corporation("Festival", 1, '\x1b[41m'), Corporation("Imperial", 2, '\x1b[46m'), Corporation("Continental", 2, '\x1b[45m')]
		#string accumulator for in-round actions, especially by AI players
		self.console = ""
		#in my tests, I found a one-in-one-thousand oversight/error in the game rules:
		#    situation is possible in which no players can place tiles,
		#    even if game shouldn't have ended
		#So I keep this variable to call the game on the rare occasion it gets stuck
		self.stuck = None
	
	#part of Game "interface"
	#PRIMARY, ABSTRACT METHOD FOR CALLING AT RUNTIME
	def doRound(self): #None
		#reset the console string accumulator for the new round
		self.stuck = None #indeterminate until round ends
		#Give each player a turn...
		for player in self.players:
			#... but if the game is over (note: self.stuck != True here), then exit immediately
			if not self.getCompletion() < 100.0: return
			#1a. Ask for a tile to place
			tile = self.promptPlacement(player)
			if tile != None:
				assert self.testPlaceability(tile)
				self.stuck = False
				self.console += player.agent.name + " plays " + str(tile) + "\n"
				#1b. Place the tile and get a set of the loner-tiles it adjoins
				tilesAdded = self.placeTile(player, tile)
				corporationExpanded = None
				corporationsExpanded = self.getCorporationsAdjoiningTile(tile)
				#2a. If we expanded corporations, merge them (passing a set of just one corporation gets the corporation back)
				if len(corporationsExpanded) > 0: corporationExpanded = self.promptMerger(player, corporationsExpanded)
				#2b. If we joined tiles together, make a new corporation
				elif len(tilesAdded) > 1:
					corporationExpanded = self.promptFound(player, tilesAdded)
					self.console += player.agent.name + " founds " + str(corporationExpanded) + "\n"
					certificatesAvailable = corporationExpanded.getStockAvailable()
					#Award the founder's bonus, if possible
					assert corporationExpanded.getStockPrice() == 0
					if len(certificatesAvailable) > 0: player.buy(certificatesAvailable.pop())
				
				#3. Add all the tiles to the relevant corporation, if any
				if corporationExpanded != None:
					for nextTile in tilesAdded: corporationExpanded.addTile(nextTile)

			#4. Let the player purchase stock in existing corporations
			self.promptBuys(player)
			#5a. Replenish the player's tiles
			self.replenishPlayer(player)
		
		if self.stuck != False: #no one placed anything...
			self.console += "Placement impossible; reshuffling...\n"
			assert len(self.tilesUndrawn) > 0 #otherwise we can't reshuffle
			#reshuffle the game tiles for next round
			for player in self.players:
				self.tilesUndrawn |= player.tiles
				player.tiles = set()
			for player in self.players:
				self.replenishPlayer(player)
				if len([tile for tile in player.tiles if self.testPlaceability(tile)]) > 0: self.stuck = False
		
		if self.stuck != False: self.stuck = True
	
	#get an Agent to place a tile
	def promptPlacement(self, player): #Tile
		#player : Player
		choices = [tile for tile in player.tiles if self.testPlaceability(tile)]
		if len(choices) == 0: return None
		decision = Decision.Enumeration(self.getDictForPlayer(player), "pmnt", "Place a tile:")
		for choiceTile in choices:
			corporationIsFounded = 1.0 if len(self.getAdjoiningLoners(choiceTile)) > 0 else 0.0
			
			corporationsMerged = sorted(list(self.getCorporationsAdjoiningTile(choiceTile)), \
			key = lambda corp: len(corp.tiles), reverse = True)
			
			playerVestedInterest = min( \
			sum([corp.getVestedInterestForPlayer(player) for corp in corporationsMerged]) / float(len(corporationsMerged)) \
			if len(corporationsMerged) > 0 \
			else 0.0, \
			1.0) #just make sure that float arithmetic doesn't go over 1.00
			
			centerR = float(self.boardRows-1.0)/2.0
			centerC = float(self.boardCols-1.0)/2.0
			
			decision.option( \
			\
			{"pstn":\
			{"cenr":((float(choiceTile.row)-centerR)/centerR) ** 2.0, "cenc":((float(choiceTile.col)-centerC)/centerC) ** 2.0}, "fnds":corporationIsFounded, "mrgs":1.0 if len(corporationsMerged) > 1 else 0.0, "bons":playerVestedInterest},\
			\
			"tile", \
			\
			choiceTile, \
			\
			str(choiceTile) + ("*" * len(self.getCorporationsAdjoiningTile(choiceTile)) if len(self.getCorporationsAdjoiningTile(choiceTile)) > 0 else ("+" if len(self.getAdjoiningLoners(choiceTile)) > 0 else "")) \
			)
		
		return player.agent.decide(self, decision).id #returns the Tile placed
	
	#make sure a tile isn't dead
	def testViability(self, tile): #Boolean
		#tile : Tile
		assert tile not in self.tilesPlaced and tile not in self.tilesUndrawn
		return not len([corp for corp in self.getCorporationsAdjoiningTile(tile) if corp.isSafe()]) > 1
	
	#make sure we can place a tile right now
	def testPlaceability(self, tile): #Boolean
		#tile : Tile
		assert tile not in self.tilesPlaced and tile not in self.tilesUndrawn
		if not self.testViability(tile): return False
		#If not all corporations are on the board, return True
		if len([corp for corp in self.corporations if len(corp.tiles) == 0]) > 0: return True
		#Otherwise, check whether we would add a ninth corporation, which is illegal
		return len(self.getAdjoiningLoners(tile)) == 0
	
	#do the placement
	def placeTile(self, player, tile): #Tile set
		#player : Player
		#tile : Tile
		assert tile not in self.tilesPlaced and tile not in self.tilesUndrawn
		assert tile in player.tiles
		assert self.testPlaceability(tile)
		player.tiles.remove(tile)
		self.tilesPlaced.add(tile)
		others = self.getAdjoiningLoners(tile)
		others.add(tile)
		return others
	
	#adjacent tiles not affiliated with any corporation
	def getAdjoiningLoners(self, tile):
		#tile : Tile
		return set([adjLoner for adjLoner in self.tilesPlaced if tile.adjoins(adjLoner) and adjLoner.corporation == None])
	
	#corporations with at least one tile adjoining the tile passed as argument
	def getCorporationsAdjoiningTile(self, tile): #Corporation set
		#tile : Tile
		return set([corp for corp in self.corporations if len([adjTile for adjTile in corp.tiles if adjTile.adjoins(tile)]) > 0])
	
	#corporations on the board
	def getCorporationsActive(self): return set([corp for corp in self.corporations if len(corp.tiles) > 0])
	
	def getCorporationsInactive(self): return set(self.corporations) - self.getCorporationsActive()
	
	#asks Agent how to proceed with merger
	def promptMerger(self, player, corporations): #None
		#player : Player
		#corporations : Corporation list
		if len(corporations) == 1: return corporations.pop()
		
		survivor = self.promptLargest(player, corporations, "surv", "Corporations merge; choose the survivor:")
		corporations.remove(survivor)
		
		self.console += player.agent.name + " initiates merger\n"
			
		while len(corporations) > 0:
			nextTarget = self.promptLargest(player, corporations, "fold", "Corporations merge; choose a folder:")
			self.console += "\t" + str(nextTarget) + " folds\n"
			self.console += "\t\t%(bonusMajor)i to %(ownersMajor)s\n" \
			% {"bonusMajor":nextTarget.getBonuses()[0], "ownersMajor":", ".join([ownerMajor.agent.name for ownerMajor in nextTarget.getOwnersMajor()])}
			self.console += "\t\t%(bonusMinor)i to %(ownersMinor)s\n" \
			% {"bonusMinor":nextTarget.getBonuses()[1], "ownersMinor":", ".join([ownerMinor.agent.name for ownerMinor in nextTarget.getOwnersMinor()])}
			corporations.remove(nextTarget)
			playerNamesOrdered = [self.players[(self.players.index(player)+i)%len(self.players)].agent.name for i in range(len(self.players))]
			self.mergeCorporations(survivor, nextTarget, playerNamesOrdered)
		
		self.console += "\t" + str(survivor) + " survives\n"
		
		return survivor
	
	#asks Agent to decide which Corporation is largest when two are tied
	def promptLargest(self, player, corporations, outputsType, description): #Corporation
		#player : Player
		#corporations : Corporation set
		#outputsType : string
		#description : string
		if len(corporations) == 0: return None
		corporationsSortedBySize = sorted(list(corporations), key = lambda corp: len(corp.tiles), reverse = True)
		choices = [corp for corp in corporationsSortedBySize if len(corp.tiles) == len(corporationsSortedBySize[0].tiles)]
		
		if len(choices) == 1: return choices[0]
		
		decision = Decision.Enumeration(self.getDictForPlayer(player), outputsType, description)
		for corp in choices: decision.option(corp.getDictForPlayer(player), "corp", corp, str(corp))
		
		return player.agent.decide(self, decision).id
	
	#complete the merger of two Corporation instances
	def mergeCorporations(self, survivor, folder, playerNamesOrdered): #None
		#survivor : Corporation
		#folder : Corporation
		#playerNamesOrdered : string list
		assert survivor != folder
		assert survivor.tiles.isdisjoint(folder.tiles)
		assert survivor.stock.isdisjoint(folder.stock)
		
		folder.payout()
		
		sharesByOwnerName = folder.getSharesByOwnerName()
		assert False not in [shareOwnerName in playerNamesOrdered for shareOwnerName in sharesByOwnerName]
		for shareOwnerName in sorted(sharesByOwnerName, key = lambda name: playerNamesOrdered.index(name)):
			share = sharesByOwnerName[shareOwnerName]
			sample = share.pop()
			owner = sample.owner
			share.add(sample)
			while len(share) > 0:
				#make sure the share is an accurate reflection of the owner's holdings
				assert False not in [cert.owner == owner for cert in share]
				decision = Decision.Enumeration(self.getDictForPlayer(owner), "tact", "Folding " + str(folder) + " into " + str(survivor) + "; you have " + str(len(share)) + " certificates in the defunct corporation:")
				decision.option({"gain":survivor.getDictForPlayer(owner), "lose":folder.getDictForPlayer(owner)}, "hold", None, "(No further transactions)")
				sold = share.pop()
				share.add(sold)
				decision.option({"gain":survivor.getDictForPlayer(owner), "lose":folder.getDictForPlayer(owner)}, "sell", sold, "Sell next one for $" + str(folder.getStockPrice()))
				survivorStockAvailable = survivor.getStockAvailable()
				if len(share) > 1 and len(survivorStockAvailable) > 0:
					traded = (share.pop(), share.pop())
					obtained = survivorStockAvailable.pop()
					share |= set(traded)
					decision.option({"gain":survivor.getDictForPlayer(owner), "lose":folder.getDictForPlayer(owner)}, "exch", (traded, obtained), "Trade next two for one " + survivor.name)
				
				result = owner.agent.decide(self, decision).id
				if result == None:
					#don't get to know when people retain shares...
					#self.console += "\t\t" + owner.agent.name + " retains shares\n"
					break
				elif result == sold:
					self.console += "\t\t" + owner.agent.name + " sells next share for $" + str(folder.getStockPrice()) + "\n"
					owner.sell(sold)
					share.remove(sold)
				else:
					assert result == (traded, obtained)
					assert traded[0].owner == owner and traded[0] in owner.stock
					assert traded[1].owner == owner and traded[1] in owner.stock
					assert obtained.owner == None
					self.console += "\t\t" + owner.agent.name + " trades next two shares for one\n"
					owner.stock.remove(traded[0])
					owner.stock.remove(traded[1])
					owner.stock.add(obtained)
					traded[0].owner = None
					traded[1].owner = None
					obtained.owner = owner
					share -= set(traded)
		
		for tile in folder.tiles:
			tile.corporation = None
			survivor.addTile(tile)
		folder.tiles = set()
	
	#ask Agent which Corporation to found when placing a tile next to a loner to create a chain
	def promptFound(self, player, tiles): #Corporation
		#player : Player
		#tiles : Tile set
		assert len(tiles) > 1
		choices = self.getCorporationsInactive()
		assert len(choices) > 0
		if len(choices) == 1: return choices.pop()
		decision = Decision.Enumeration(self.getDictForPlayer(player), "foun", "Found a " + str(len(tiles)) + "-tiles corporation:")
		for corp in choices: decision.option({"tier":float(corp.tier)/2.0, "held":float(len([cert for cert in corp.stock if cert.owner != None]))/float(len(corp.stock)), "plsh":float(len([cert for cert in corp.stock if cert.owner == player]))/float(len(corp.stock))}, "newc", corp, str(corp))
		
		return player.agent.decide(self, decision).id
	
	#ask Agent which stock certificates to buy
	def promptBuys(self, player): #None
		#player : Player
		for i in range(3):
			choices = set([stock.pop() for (corp, stock) in [(corp, corp.getStockAvailable()) for corp in self.getCorporationsActive() if not corp.getStockPrice() > player.wallet] if len(stock) > 0])
			if len(choices) == 0: return
			decision = Decision.Enumeration(self.getDictForPlayer(player), "prch", "You have " + str(player.wallet) + ":")
			decision.option({}, "save", None, "(No further purchases)")
			for cert in choices: decision.option(cert.corporation.getDictForPlayer(player), "corp", cert, str(cert.corporation) + " for $" + str(cert.corporation.getStockPrice()) + " (you own " + str(len(cert.corporation.getSharesByOwnerName()[player.agent.name]) if player.agent.name in cert.corporation.getSharesByOwnerName() else 0) + "/" + str(len(cert.corporation.stock)) + "; " + str(len(cert.corporation.getStockAvailable())) + "/" + str(len(cert.corporation.stock)) + " remain)")
			
			certificate = player.agent.decide(self, decision).id
			if certificate == None: break
			self.console += player.agent.name + " buys " + str(certificate.corporation) + "\n"
			player.buy(certificate)
	
	#make sure the player gets new tile(s) at end of turn
	def replenishPlayer(self, player):
		#player : Player
		while len(player.tiles) < 7 and not len(player.tiles) > len(self.tilesUndrawn)/len(self.players):
			if len(self.tilesUndrawn) == 0: break
			player.draw(self.tilesUndrawn)
			tilesDead = set([tile for tile in player.tiles if not self.testViability(tile)])
			self.tilesUndrawn -= tilesDead
			player.tiles -= tilesDead
	
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

#(again, unused at present)
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

class Tile:
	@classmethod
	def nameForRow(self, r): #string
		#r : int
		assert r < 26
		return chr(r+ord('A'))
	
	def __init__(self, row, col): #void / None
		#row : int
		#col : int
		self.row = row
		self.col = col
		self.corporation = None
	
	def __str__(self): return self.__class__.nameForRow(self.row) + str(self.col).zfill(2)
	
	def adjoins(self, other): #Boolean
		#other : Tile
		return True if abs(self.row - other.row) + abs(self.col - other.col) == 1 else False

class Certificate:
	def __init__(self, corporation): #void / None
		#corporation : Corporation
		self.corporation = corporation
		self.owner = None

class Corporation:
	def __init__(self, name, tier, consoleColor = None): #void / None
		#name : string
		#tier : int
		#color : optional ansi-escape-sequence color-code
		assert not tier < 0 and not tier > 2
		self.name = name
		self.tier = tier
		self.tiles = set()
		self.stock = set([Certificate(self) for i in range(25)])
		self.consoleColor = consoleColor
	
	def __str__(self):
		#string with name and star-rating
		return self.name + " (" + ("*"*(self.tier+1)) + ")"
	
	def addTile(self, tile):
		#tile : Tile
		assert tile.corporation == None
		self.tiles.add(tile)
		tile.corporation = self
	
	def getStockPrice(self): #float
		if len(self.tiles) < 2: return 0
		cutoffs = [3, 4, 5, 6, 11, 21, 31, 41, None]
		prices = [100 * p for p in range(2, 13)][self.tier:self.tier+len(cutoffs)]
		for cutoff, price in zip(cutoffs, prices):
			if cutoff == None or len(self.tiles) < cutoff:
				return price
		assert False
	
	def getVestedInterestForPlayer(self, player): #float
		#player : Player
		vestedInterest = 0.0
		ownersMajor = self.getOwnersMajor()
		ownersMinor = self.getOwnersMinor()
		if player in ownersMajor: vestedInterest += 2.0 / float(len(ownersMajor))
		if player in ownersMinor: vestedInterest += 1.0 / float(len(ownersMinor))
		vestedInterest /= 3.0
		assert not vestedInterest < 0.0 and not vestedInterest > 1.0
		return vestedInterest
	
	def getDictForPlayer(self, player): #dictionary
		#player : Player
		representation = {}
		representation["tier"] = float(self.tier) / 2.0
		representation["size"] = min(float(len(self.tiles)) / 41.0, 1.0)
		representation["pric"] = float(self.getStockPrice()) / 1200.0
		representation["avbl"] = float(len(self.getStockAvailable())) / float(len(self.stock))
		representation["sout"] = 1.0 if self.isSoldOut() else 0.0
		representation["safe"] = 1.0 if self.isSafe() else 0.0
		
		sharesByOwnerName = self.getSharesByOwnerName()
		representation["sprd"] = 1.0 - (1.0 / float(len(sharesByOwnerName)))
		representation["ownp"] = float(len(sharesByOwnerName[player.agent.name]))/float(len(self.stock)) if player.agent.name in sharesByOwnerName else 0.0
		
		#disadvantage, vis-a-vis the majority owner
		shareLargest = float(len(sharesByOwnerName[self.getOwnersMajor().pop().agent.name]))
		sharePlayer = float(len(sharesByOwnerName[player.agent.name])) if player.agent.name in sharesByOwnerName else 0.0
		representation["plda"] = min(max((shareLargest - sharePlayer) / float(len(self.stock)), 0.0), 1.0)
		representation["bons"] = self.getVestedInterestForPlayer(player)
		
		playerTilesAdjoin = [playerTile for playerTile in player.tiles if len([myTile for myTile in self.tiles if myTile.adjoins(playerTile)]) > 0]
		representation["adjt"] = float(len(playerTilesAdjoin)) / float(len(player.tiles)) if len(player.tiles) > 0 else 0.0
		
		return representation
	
	def isSoldOut(self): return len(self.getStockAvailable()) == 0
	
	def getStockAvailable(self): return set([cert for cert in self.stock if cert.owner == None])
	
	def getBonuses(self): #float tuple
		major = self.getStockPrice() * 10
		return (major, major / 2)
	
	def isSafe(self): return len(self.tiles) > 10
	
	def getSharesByOwnerName(self): #int dictionary
		shares = {}
		for certificate in self.stock - self.getStockAvailable():
			if certificate.owner.agent.name not in shares:
				shares[certificate.owner.agent.name] = set()
			shares[certificate.owner.agent.name].add(certificate)
		assert len(shares) > 0
		return shares
	
	def getOwnersMajor(self): #Player set
		shares = self.getSharesByOwnerName()
		shareMajor = max([len(shares[ownerName]) for ownerName in shares])
		return set([share.pop().owner for share in shares.values() if len(share) == shareMajor])
	
	def getOwnersMinor(self): #Player set
		ownersMajor = self.getOwnersMajor()
		shares = self.getSharesByOwnerName()
		if len(ownersMajor) > 1 or len(shares) == 1: return ownersMajor
		
		ownerNamesMajor = [owner.agent.name for owner in ownersMajor]
		
		shareMinor = max([len(shares[ownerName]) for ownerName in shares if ownerName not in ownerNamesMajor])
		return set([share.pop().owner for share in shares.values() if len(share) == shareMinor])
	
	#Buyouts and End-Of-Game
	def payout(self): #None
		ownersMajor = self.getOwnersMajor()
		ownersMinor = self.getOwnersMinor()
		bonuses = self.getBonuses()
		
		for ownerMajor in ownersMajor: ownerMajor.wallet += int(math.ceil((float(bonuses[0])/float(len(ownersMajor)))/100.0)*100)
		for ownerMinor in ownersMinor: ownerMinor.wallet += int(math.ceil((float(bonuses[1])/float(len(ownersMinor)))/100.0)*100)