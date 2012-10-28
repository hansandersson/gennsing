#Copyright (c) Hans Andersson 2011
#All rights reserved.

import os

try: from functools import reduce
except ImportError: reduce = reduce

import NeuralNetwork

#############################
### NN DECISION FRAMEWORK ###
#############################

#This module concretizes (in-game) decisions as "Evaluation" instances

class Evaluation:
	#this class expresses the neural-network - backpropagate-able
	#difference between two Evaluation instances
	class Difference:
		def __init__(self, context, outputsType, targetActivations, otherActivations):
			assert type(targetActivations) == type(list())
			assert type(otherActivations) == type(list())
			assert len(targetActivations) == len(otherActivations)
			assert type(context) == type(dict())
			assert type(outputsType) == type(str())
			self.context = context
			self.outputsType = outputsType
			self.deltas = [t - o for t, o in zip(targetActivations, otherActivations)]
	
	def __init__(self, context, outputsType, outputsCount = 1, description = None):
		#context : recursive float dictionary
		#outputsType : string
		#outputsCount : (int)
		#description : (string)
		assert type(context) == type(dict())
		self.context = context
		self.outputsType = outputsType
		self.outputsCount = outputsCount
		self.activations = None
		self.description = description
	
	#passes the decision through a neural network to set activations
	def through(self, brain):
		#brain : Brain
		self.activations = brain.feedForward(NeuralNetwork.Stimulus.fromDict(self.context), self.outputsType, self.outputsCount)
		assert len(self.activations) == self.outputsCount
		return self.activations
	
	#gets the decision from the console user
	def fromConsole(self):
		os.system("printf '%s\n'" % str(self))
		os.system("printf '\tChannels : %i\n'" % self.outputsCount)
		while self.activations == None \
		or len(self.activations) != self.outputsCount \
		or max(self.activations) > 1.0 or min(self.activations) < 0.0:
			inputs = input("? ").split(" ")
			self.activations = [float(input) for input in inputs]
		return self.selection()
	
	#just returns the list of activations for a generic Evaluation instance (cf subclasses)
	def selection(self): return self.activations
	
	#needed so that we don't end up overwriting previous decisions
	def copyFresh(self):
		return self.__class__(self.context, self.outputsType, self.outputsCount, self.description)
	
	#useful for giving neural network clearer learning examples
	def clarified(self):
		selfClarified = Evaluation(self.context, self.outputsType, self.outputsCount, self.description)
		selfClarified.activations = self.activations
		return selfClarified
	
	#computes where two decisions differ --- for use with clarified(), supra
	def differences(self, other):
		#self : target Evaluation
		#other : deviating Evaluation
		assert self.__class__ == other.__class__
		assert self.outputsType == other.outputsType
		assert self.selection() != None
		assert other.selection() != None
		return [self.__class__.Difference(self.context, self.outputsType, self.activations, other.activations)]
	
	def __str__(self): return "Decision : " + (self.outputsType if self.description == None else self.description)

#I've found that the neural nets can learn discrete decisions much better than continuous ones
#Evaluation subclass for making a selection among enumerated options
class Enumeration(Evaluation):
	class Option:
		def __init__(self, context, outputsType, id = None, description = None):
			#context : recursive float dictionary
			#outputsType : string
			#id : (any) for external identification only (e.g. for in-game convenience)
			#           not for use in the NeuralNetwork neural network or genetic algorithm
			#description : (string)
			self.context = context
			self.outputsType = outputsType
			self.id = id
			self.activation = None
			self.description = description
		
		def copyFresh(self): return self.__class__(self.context, self.outputsType, self.id, self.description)
		
		def __str__(self): return (self.outputsType if self.description == None else self.description)
	
	def __init__(self, context, outputsType, description = None):
		#context : recursive float dictionary
		#outputsType : string
		#description : (string)
		assert type(context) == type(dict())
		self.context = context
		self.outputsType = outputsType
		self.outputsCount = 1
		self.activations = None
		self.options = []
		self.description = description
	
	#adds an option to the enumeration
	def option(self, context, outputsType, id = None, description = None): #new Option
		#context : recursive float dictionary
		#outputsType : string
		#id : (any) again, for external convenience only
		#description : (string)
		assert type(context) == type(dict())
		option = self.__class__.Option(context, outputsType, id, description)
		self.options.append(option)
		return option
	
	def selection(self): #returns Option with maximum activation, after having passed through Brain
		return reduce( \
		lambda selection, option: selection if selection.activation > option.activation else option, \
		self.options \
		)
	
	def through(self, brain): #Option with maximum activation
		#brain : Brain
		for option, representation in zip(self.options, self.toDicts()):
			option.activation = brain.feedForward(NeuralNetwork.Stimulus.fromDict(representation), self.outputsType, 1)[0]
		return self.selection()
	
	def fromConsole(self, certainty = 0.95):
		assert type(certainty) == type(float())
		assert certainty > 0.5 and not certainty > 1.0
		os.system("printf '%s\n'" % str(self))
		choice = None
		while choice not in range(len(self.options)): choice = int(input("? "))
		for o, option in zip(range(len(self.options)), self.options):
			option.activation = (certainty) if o == choice else (1.0 - certainty)
		return self.selection()
	
	def toDicts(self): #recursive float dictionary --- used only in Enumeration instances to contextualize each option
		return [{"context":self.context, option.outputsType:option.context} for option in self.options]
	
	def copyFresh(self):
		copy = self.__class__(self.context, self.outputsType, self.description)
		copy.options = [option.copyFresh() for option in self.options]
		return copy
	
	def clarified(self, certainty = 0.95): #enhances the machine-learnable difference between the selected option and the other options
		assert type(certainty) == type(float())
		assert certainty > 0.5 and not certainty > 1.0
		selfClarified = self.copyFresh()
		selectionIndex = self.options.index(self.selection())
		for o, option in zip(range(len(selfClarified.options)), selfClarified.options):
			option.activation = (certainty) if o == selectionIndex else (1.0 - certainty)
		return selfClarified
	
	def differences(self, other):
		#self : target Evaluation
		#other : deviating Evaluation
		assert self.selection() != None
		assert other.selection() != None
		assert self.__class__ == other.__class__
		assert self.outputsType == other.outputsType
		assert len(self.options) == len(other.options)
		return [self.__class__.Difference(selfOptionRepresentation, self.outputsType, [selfOption.activation], [otherOption.activation]) for selfOption, otherOption, selfOptionRepresentation in zip(self.options, other.options, self.toDicts())]
	
	def __str__(self):
		stringRepresentation = "Decision : " + (self.outputsType if self.description == None else self.description) + "\n"
		stringRepresentation += "\n".join(["\tOption " + str(o).zfill(len(str(len(self.options)))) + " : " + str(option) for o, option in zip(range(len(self.options)), self.options)])
		return stringRepresentation

#Evaluation subclass to yield True/False responses
class Verification(Evaluation):
	def __init__(self, context, outputsType, description = None):
		#context : recursive float dictionary
		#outputsType : string
		#description : optional, human-readable string
		assert type(context) == type(dict())
		self.context = context
		self.outputsType = outputsType
		self.outputsCount = 1
		self.activations = None
		self.description = description
	
	def fromConsole(self, certainty = 0.95):
		assert type(certainty) == type(dict())
		assert certainty > 0.5 and not certainty > 1.0
		os.system("printf '%s\n'" % str(self))
		choice = None
		while choice not in [0, 1]: choice = int(input("? "))
		self.activations = [certainty] if choice == 1 else [1.0 - certainty]
		return self.selection()
		
	def selection(self): #Boolean
		assert self.activations != None
		assert type(self.activations) == type(list())
		assert len(self.activations) == 1
		return self.activations[0] > 0.5
	
	def copyFresh(self):
		return self.__class__(self.context, self.outputsType, self.description)
	
	def clarified(self, certainty = 0.95):
		assert type(certainty) == type(dict())
		assert certainty > 0.5 and not certainty > 1.0
		selfClarified = self.copyFresh()
		selfClarified.activations = [certainty] if self.selection() else [1.0 - certainty]
		return selfClarified