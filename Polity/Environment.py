#Copyright (c) Hans Andersson 2011
#All rights reserved.

import os, random, sys, math
cwd = os.getcwd()
sys.path.append("../")
import Decision
os.chdir(cwd)

try: from functools import reduce
except ImportError: reduce = reduce

##########################################
### MADE-UP GAME --- FOR EARLY TESTING ###
##########################################

playersCountRange = (2, 8)

class Game:
	def __init__(self, agents, goal = 100.0):
		#agents : Agent list
		#goal : float
		self.agents = agents
		self.empires = [Empire() for e in range(len(self.agents))]
		assert goal > 0.0 and not goal > 1000.0
		self.goal = goal
		self.rounds = 0
		self.status = ""
	
	def doRound(self):
		self.rounds += 1
		
		scores = [empire.score() for empire in self.empires]
		scoresMax = max(scores)
		scoresMin = min(scores)
		scoresRange = scoresMax - scoresMin
		
		def bounded(v):
			return max(min(v, 1.0), 0.0)
		
		contexts = [{"position":empire.dictRepr(), "standing":{"absolute":empire.score()/self.goal, "relative":((empire.score() - scoresMin)/scoresRange) if scoresRange > 0.0 else (1.0)}, "order":float(e)/float(len(self.empires)-1), "share":1.0/float(len(self.empires)), "time":100.0/(100.0+float(self.rounds))} for empire, e in zip(self.empires, range(len(self.empires)))]
		
		decisions = []
		for agent, empire, context in zip(self.agents, self.empires, contexts):
			empire.growth, empire.development, empire.production = agent.decide(self, Decision.Evaluation(context, "allocations", 3, "Your empire allocates resources to produce population, infrastructure, and material"))
			
			consumptions = (0.1, 0.1, 0.1)#agent.decide(Decision.Evaluation(context, "consumptions", 3, "Your empire consumes population => military, infrastructure => culture, material => technology:"))
			empire.draft(empire.population * min(consumptions[0], 1.0))
			empire.cultivate(empire.infrastructure * min(consumptions[1], 1.0))
			empire.invest(empire.material * min(consumptions[2], 1.0))
			
			action = Decision.Enumeration(context, "action", "You take one action:")
			action.option([empire.willingness/100.0, empire.preparedness/100.0], "bide", 1, "Bide your time; recuperate willingness and preparedness")
			action.option([100.0/(100.0+empire.progress), empire.willingness/100.0], "research", 1, "Research progress at the expense of willingness")
			action.options.extend([Decision.Enumeration.Option(otherContext, "attack", other, "Attack " + otherAgent.name + " at the expense of preparedness and willingness") for other, otherAgent, otherContext in zip(self.empires, self.agents, contexts) if other != empire])
			decisions.append(action)
		
		actions = [agent.decide(self, decision) for agent, decision in zip(self.agents, decisions)]
		self.status = ""
		for empire, agent, action in zip(self.empires, self.agents, actions):
			if action.outputsType == "bide":
				empire.bide()
				self.status += agent.name + " bode.\n"
			elif action.outputsType == "research":
				empire.research()
				self.status += agent.name + " researched.\n"
			else:
				assert action.id in self.empires and action.id != empire
				empire.attack(action.id)
				self.status += agent.name + " attacked " + self.agents[self.empires.index(action.id)].name + ".\n"
		
		for empire in self.empires:
			empire.turn()
	
	def getCompletion(self):
		return 100.0 * max(float(self.rounds)/100.0, max([empire.score() for empire in self.empires])/self.goal)
	
	def finalize(self): #Agent list
		#from winner to loser
		return [agent for agent, empire in sorted(zip(self.agents, self.empires), key = lambda agent, empire: empire.score(), reverse = True)]
	
	def getPerformances(self):
		performances = {}
		for agent, empire in zip(self.agents, self.empires):
			performances[agent.name] = empire.score()
		return performances
	
	def __str__(self):
		features = ["population", "growth", "military", "preparedness", "infrastructure", "development", "culture", "willingness", "material", "production", "technology", "progress"]
		colors = {"population":'\x1b[34m', "growth":'\x1b[34m', "military":'\x1b[31m', "preparedness":'\x1b[31m', "infrastructure":'\x1b[33m', "development":'\x1b[33m', "culture":'\x1b[35m', "willingness":'\x1b[35m', "material":'\x1b[32m', "production":'\x1b[32m', "technology":'\x1b[36m', "progress":'\x1b[36m'}
		colWidth = 10
		
		console = self.status + "\n\x1b[1m"+("".rjust(colWidth)+" ") + (" ".join([(colors[feature] if feature in colors else "") + feature[0:min(5, colWidth, len(feature))].upper().rjust(colWidth) for feature in features])+"\n")
		console += "\n".join(["\x1b[0m\x1b[1m"+agent.name[0:min(colWidth, len(agent.name))].upper().rjust(colWidth)+"\x1b[0m " + " ".join([(colors[feature] if feature in colors else "") + str(int(empire.__dict__[feature])).rjust(colWidth) for feature in features]) + "\x1b[0m\x1b[1m" + str(int(empire.score())).rjust(colWidth) for empire, agent in zip(self.empires, self.agents)])
		return console+"\x1b[0m"

class Empire:
	def __init__(self):
		self.population = 100.0 #tangible
		self.growth = 100.0 #allocation
		self.military = 0.0 #intangible
		self.preparedness = 100.0
		
		self.infrastructure = 100.0 #tangible
		self.development = 100.0 #allocation
		self.culture = 0.0 #intangible
		self.willingness = 100.0
		
		self.material = 100.0 #tangible
		self.production = 100.0 #allocation
		self.technology = 0.0 #intangible
		self.progress = 0.0
	
	def turn(self):
		unitCosts = [[1.0, 3.0, 6.0],
					 [6.0, 1.0, 3.0],
					 [3.0, 6.0, 1.0]]
		focuses = [self.growth, self.development, self.production]
		totalFocus = sum(focuses)
		self.growth, self.development, self.production = [100.0*(focusNext/totalFocus) if totalFocus > 0.0 else (100.0/3.0) for focusNext in focuses]
		totalCosts = reduce(lambda c1, c2: map(lambda a, b: a+b, zip(c1, c2)), [map(lambda c, f: c*f, zip(focuses, costs)) for costs in unitCosts])
		capacities = [(self.willingness / 100.0) * self.population, self.infrastructure, self.material]
		minMultiplier = min(map(lambda cap, cost: cap / cost if cost > 0 else 1e10, zip(capacities, totalCosts)))
		progress = [focus * minMultiplier for focus in focuses]
		self.population += 1.0 + progress[0] # no multiplier
		self.infrastructure += 1.0 + progress[1] * math.log(1.0 + self.progress)
		self.material += 1.0 + progress[2] * math.log(1.0 + self.progress)
	
	def dictRepr(self):
		attributes = {}
		attributes["_popln"] = 100.0/(100.0+self.population)
		attributes["_infrs"] = 100.0/(100.0+self.infrastructure)
		attributes["_matrl"] = 100.0/(100.0+self.material)
		attributes["growth"] = self.growth/100.0
		attributes["dvlpmt"] = self.development/100.0
		attributes["prdctn"] = self.production/100.0
		attributes["_milty"] = 100.0/(100.0+self.military)
		attributes["_cultr"] = 100.0/(100.0+self.culture)
		attributes["_techy"] = 100.0/(100.0+self.technology)
		attributes["prepar"] = self.preparedness/100.0
		attributes["willin"] = self.willingness/100.0
		attributes["_progr"] = 100.0/(100.0+self.progress)
		return attributes
	
	#Consumption
	def draft(self, q):
		#q : float
		assert not q > self.population
		self.population -= q
		self.military += q
	
	def cultivate(self, q):
		#q : float
		assert not q > self.infrastructure
		self.infrastructure -= q
		self.culture += q
	
	def invest(self, q):
		#q : float
		assert not q > self.material
		self.material -= q
		self.technology += q
	
	#Action
	def attack(self, other):
		#other : Empire
		#costs willingness, preparedness
		#gains assets from other players
		forcesA = self.preparedness * self.military
		forcesB = other.preparedness * min(other.military, other.military ** 0.5)
		battle = forcesA + forcesB
		capture = (forcesA / battle) ** 2.0
		for asset in ["population", "infrastructure", "material"]:
			change = capture * other.__dict__[asset]
			self.__dict__[asset] += change / 1.1
			other.__dict__[asset] -= change
		self.military *= (forcesA / battle) ** 0.25
		other.military = (other.military - min(other.military, other.military ** 0.5)) + (min(other.military, other.military ** 0.5) * (forcesB / battle) ** 0.25)
		other.culture *= (1.0 - capture) ** 0.5
		other.progress *= (1.0 - capture) ** 0.5
		self.preparedness *= random.uniform(0.7, 0.9)
		
	def bide(self):
		recover = lambda value: 100.0 - ((100.0 - value) / random.uniform(9.0, 11.0))
		self.willingness = recover(self.willingness)
		self.preparedness = recover(self.preparedness)
	
	def research(self):
		#costs willingness, preparedness
		#gains progress (productivity from primaries to intangibles)
		self.progress += self.technology
		self.willingness *= random.uniform(0.7, 0.9)
	
	#Information
	def score(self):
		return ((self.population ** 2.0) * self.military * self.infrastructure * (self.culture ** 2.0) * (self.material * self.technology * self.progress)) ** (1.0/9.0) / 1.5