#Copyright (c) Hans Andersson 2011
#All rights reserved.

import os

import NeuralNetwork, Decision

####################################
### NN-DECISION AGENCY FRAMEWORK ###
####################################

#"Agent" instances decide "Decision" instances; an "Agent" can be either "AI" or "IO"
#"AI(Agent)" instances pass "Decision" instances through a "Brain"
#"IO(Agent)" instances ask the console user to decide

#"AI" instances encapsulate a "Brain" instance,
#               pass "Decision" instances through the "Brain",
#           and remember all past decision stimuli-outputs for later learning

class Agent: #"abstract" superclass / "interface"
	def __init__(self): self.decisions = []

	def decide(self, game, decision):
		self.decisions.append(decision)
		#pass
		return decision.selection()

class IO(Agent):
	def __init__(self, name):
		#name : string
		self.name = name
		self.decisions = []
	
	def decide(self, game, decision): #Option | Boolean | (float list)
		#decision : Decision
		self.decisions.append(decision)
		os.system("clear")
		os.system("printf '%s\n'" % str(game))
		input = None
		while input == None:
			try: input = decision.fromConsole()
			except ValueError: input = None
		return input
	
	def consult(self, other):
		#other : Agent
		assert isinstance(other, AI)
		review = ""
		for decision in self.decisions:
			secondOpinion = decision.copyFresh()
			secondOpinion.through(other.brain)
			review += str(decision) + "\n" + \
			self.name + " : " + str(decision.clarified().selection()) + "\n" + \
			other.name + " : " + str(secondOpinion.clarified().selection()) + "\n\n"
		return review

class AI(Agent):
	def __init__(self, brain):
		#brain : Brain
		self.brain = brain
		self.name = brain.path.split("/")[-1]
		self.decisions = []
	
	def decide(self, game, decision): #Option | Boolean | (float list) --- depends on Decision subclass
		#decision : Evaluation
		self.decisions.append(decision)
		return decision.through(self.brain)
	
	def learn(self, decisionTarget): #perspective, outputsType, targets): #void --- updates Brain
		#decisionClarified : Evaluation
		decisionActual = decisionTarget.copyFresh()
		decisionActual.through(self.brain)
		for difference in \
		decisionTarget.differences(decisionActual):
			self.brain.feedBackward( \
			difference.deltas, \
			difference.outputsType, \
			NeuralNetwork.Stimulus.fromDict(difference.context) \
			)