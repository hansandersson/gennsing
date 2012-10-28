#Copyright (c) Hans Andersson 2011
#All rights reserved.

import os, sys, random
import NeuralNetwork, Interface

########################################
### GENETICS / SELECTIVITY FRAMEWORK ###
########################################

#SANDBOX --- takes care of running a game when only AIs are playing
def autoplay(game):
	#game : Game
	os.system("printf '\tCompete... 000'")
	while game.getCompletion() < 100.0:
		game.doRound()
		os.system("printf '\b\b\b%s'" % str(min(int(game.getCompletion()), 100)).zfill(3))
	game.finalize()
	os.system("printf '\n'")

#Stores & loads Brain instances from the pool; implements genetic algorithm / adversarial selection
#Additionally, supports NN by computing dynamic learning rate, based on past competitive performance
class Manager:
	
	#internal class to maintain records of individual AIs (wins & losses)
	class Recordkeeper:
		def __init__(self, gameName):
			self.gameName = gameName
		
		def getRecordPathForAgent(self, agent): #string (file path)
			#agent : Agent
			assert isinstance(agent, Interface.Agent)
			return "./" + self.gameName + "/records/" + agent.name
		
		def loadRecordForAgent(self, agent): #float dictionary, with sum === 1.0
			#agent : Agent
			assert isinstance(agent, Interface.Agent)
			record = {}
			if os.path.isfile(self.getRecordPathForAgent(agent)):
				with open(self.getRecordPathForAgent(agent), 'r') as store:
					for line in store:
						pieces = line.strip().split("\t")
						assert len(pieces) == 3
						record[pieces[0]] = {"wins":float(pieces[1]), "losses":float(pieces[2])}
			return record
		
		def saveAgentRecord(self, agent, record):
			#agent : Agent
			#record : (float dictionary) dictionary
			assert isinstance(agent, Interface.Agent) and type(record) == type(dict())
			with open(self.getRecordPathForAgent(agent), 'w') as store:
				store.write( \
				"\n".join( \
				[adversary + "\t" + str(record[adversary]["wins"]) + "\t" + str(record[adversary]["losses"]) \
				for adversary in record] \
				) \
				)
		
		def computeLearningRate(self, teacher, student): #float, based on competitive record; naturally decays
			#teacher : Agent
			#student : Agent
			assert isinstance(teacher, Interface.Agent)
			assert isinstance(student, Interface.Agent)
			rate = 0.1
			studentRecord = self.loadRecordForAgent(student)
			if teacher.name in studentRecord:
				studentLossesVsTeacher, studentWinsVsTeacher = \
				studentRecord[teacher.name]["losses"], studentRecord[teacher.name]["wins"]
				
				rate *= studentLossesVsTeacher / (studentLossesVsTeacher + studentWinsVsTeacher)
			return rate

	def __init__(self, gameName, minimumBrainsCount = 10):
		#minimumBrainsCount : optional int
		self.gameName = gameName
		self.pathPool = "./" + self.gameName + "/brains/"
		self.minimumBrainsCount = minimumBrainsCount
		self.fill()
		self.recordkeeper = self.Recordkeeper(self.gameName)

	### RETRIEVAL OF USABLE BRAINS / AGENTS ###
	def getNamesUsed(self): #string list --- all the brains in the genepool
		namesUsed = set()
		for root, dirs, files in os.walk(self.pathPool): namesUsed |= set(files)
		namesPool = set(open("./names", "r").read().strip().split(","))
		namesExtraneous = namesUsed - namesPool
		return namesUsed - namesExtraneous

	def getNamesUnused(self): #string list --- the complement of getNamesUsed within the namespace
		namesUnused = set(open("./names", "r").read().strip().split(","))
		return namesUnused - self.getNamesUsed()
	
	def getBrainForName(self, name): #Brain ||| Brain.path.endsWith(brainName)
		#brainName : string
		return NeuralNetwork.Brain(self.pathPool + name)

	def getAIs(self, count, namesPreferred = set(), namesExcluded = set()): #Agent list
		#count : int
		assert namesPreferred.isdisjoint(namesExcluded)
		#First, ensure that we have enough brains!!!
		while len(self.getNamesUsed() - set([name for name in namesExcluded])) < count:
			self.getBrainForName(random.choice(list(self.getNamesUnused())))
		#then, return a random sample thereof
		
		namesSelected = set()
		if len(namesPreferred) > 0:
			namesSelected |= set(random.sample(namesPreferred, count)) if not count > len(namesPreferred) else namesPreferred 
		
		if len(namesSelected) < count:
			namesSelected |= set(random.sample(self.getNamesUsed() - (namesPreferred | namesExcluded), count - len(namesSelected)))
		
		return set([Interface.AI(self.getBrainForName(name)) for name in namesSelected])

	### MANAGEMENT OF PERSISTENT STORE ###
	def fill(self, example = None): #void --- makes sure the genepool is full
		#count : int
		#example : optional Agent
		if example == None: self.getAIs(self.minimumBrainsCount)
		else:
			assert isinstance(example, Interface.Agent)
			while len(self.getNamesUsed()) < self.minimumBrainsCount:
				clone = NeuralNetwork.Brain.clone(example.brain)
				clone.saveToPath(self.pathPool + random.choice(list(self.getNamesUnused())))

	def kill(self, target): #void --- adversarial selection
		#target : Agent
		assert isinstance(target, Interface.Agent)
		os.remove(target.brain.path)
		os.remove(self.recordkeeper.getRecordPathForAgent(target))
	
	### UPDATING PERSISTENT ENTITIES ###
	def teachStudents(self, teacher, students = None): #void --- updates Brain instances based on learning rate (supra)
		#teacher : Agent
		#students : Agent set
		
		#default to all existing Brain stores
		if students == None: students = [Interface.AI(brain) for brain in [self.getBrainForName(name) for name in self.getNamesUsed()]]
		
		os.system("printf '\tReflect... 000'")
		done = 0.0
		for decision in teacher.decisions:
			decisionClarified = decision.clarified()
			for student in students: student.learn(decisionClarified)
			done += 1.0
			os.system("printf '\b\b\b%s'" % str(int(100.0 * done/float(len(teacher.decisions)))).zfill(3))
		os.system("printf '\n'")
		
		os.system("printf '\tImprint... 000'")
		done = 0.0
		for student in students:
			student.brain.update(self.recordkeeper.computeLearningRate(teacher, student))
			student.brain.save()
			done += 1.0
			os.system("printf '\b\b\b%s'" % str(int(100.0 * done/float(len(students)))).zfill(3))
		os.system("printf '\n'")
	
	def updateWinnersLosers(self, winners, losers, agentsCount = None): #void --- update the competitive records
		#winners : Agent set
		#losers : Agent set
		assert winners.isdisjoint(losers)
		if agentsCount == None: agentsCount = len(winners) + len(losers)
		
		for winner in winners:
			record = self.recordkeeper.loadRecordForAgent(winner)
			for loser in losers:
				if loser.name not in record: record[loser.name] = {"wins":0.0, "losses":0.0}
				record[loser.name]["wins"] += 1.0
			self.recordkeeper.saveAgentRecord(winner, record)
		
		for loser in losers:
			record = self.recordkeeper.loadRecordForAgent(loser)
			for winner in winners:
				if winner.name not in record: record[winner.name] = {"wins":0.0, "losses":0.0}
				#adjust for count of competitors (so that wins awarded - losses awarded === 0.0)
				record[winner.name]["losses"] += 1.0 / float(agentsCount)
			self.recordkeeper.saveAgentRecord(loser, record)