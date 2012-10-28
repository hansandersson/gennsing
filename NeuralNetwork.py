#Copyright (c) Hans Andersson 2011
#All rights reserved.

import random, math, os

try: from functools import reduce
except ImportError: reduce = reduce

#####################################
### NEURAL NETWORK IMPLEMENTATION ###
#####################################

#This module provides the abstract, low-level framework for a neural network

#Nonlinear activation function (over a linear combination of inputs)
def sigmoid(value, multiplier = 1.0): #float on [0.0, 1.0]
	#value : float
	e = 1/(1 + math.exp(-value * multiplier))
	return max(min(e, 1.0), 0.0)

#A signature for messages passed through the neural network
class Signature:
	def __init__(self, kind, dimensions):
		#kind : string
		#dimensions : int
		self.kind = kind
		self.dimensions = dimensions
	
	def __str__(self): return self.kind + "^" + str(self.dimensions)

#Like a dictionary, although ordered and with the intention of immutability
class Stimulus:
	@classmethod
	def fromDict(self, dictionary): #Stimulus
		#dictionary : recursive float dictionary
		keys = []
		sources = []
		for key, value in zip(dictionary.keys(), dictionary.values()):
			keys.append(key)
			if type(value) == type(float()):
				sources.append([value])
			elif type(value) == type(list()):
				for component in value:
					if type(component) != type(float()):
						raise TypeError("Value for key '%s' contains non-float component" % key)
				sources.append(value)
			else:
				if type(value) != type(dict()):
					raise TypeError("Type of value for key '%s' unhandled" % key)
				sources.append(self.fromDict(value))
		return self(keys, sources)

	def __init__(self, keys, sources):
		#keys : string list
		#sources : (float list | Stimulus) list
		self.keys = keys
		self.values = []
		for source in sources:
			if type(source) == type(list()):
				for component in source: assert type(component) == type(float())
				self.values.append(source)
			else:
				assert type(source) == type(self)
				assert source.__class__ == self.__class__
				#Evaluate only later when passing through the neural network
				self.values.append(None)
		self.sources = sources

class Neuron:
	def __init__(self, weights): #remember to start with the constant intercept!!
		#weights : float list
		self.weights = [w for w in weights]
		#self.backs caches backpropagated values for batch updates
		self.backs = []
	
	#Activate based on inputs
	def feed(self, stimuli): #float on [0.0, 1.0]
		#stimuli : float list
		if type(stimuli) != type(list()):
			raise TypeError("Stimuli of type other than list")
		elif len(stimuli) + 1 != len(self.weights):
			raise ValueError("Count of stimuli not equal to count of weights")
		
		stimSum = self.weights[0]
		for stimulus, weight in zip(stimuli, self.weights[1:]):
			if type(stimulus) != type(float()):
				raise TypeError("Stimulus of type other than float")
			elif stimulus > 1.0 or stimulus < 0.0:
				raise ValueError("Stimulus outside range")
			stimSum += stimulus * weight
		return sigmoid(stimSum)
	
	#Cache the updates...
	#Since we're reusing neurons in multiple locations,
	#   wait to commit the changes until we're told (see 'update()' below)
	def back(self, inputs, delta): #void
		#inputs : float list
		#delta : float
		assert type(delta) == type(float())
		assert type(inputs) == type(list())
		assert len(inputs) + 1 == len(self.weights)
		
		backs = [delta * 1.0] #start with the zero-index constant term
		backs.extend([delta * input for input in inputs])
		self.backs.append(backs)
	
	#Commit what we've backed
	def update(self, rate): #void
		#rate : float
		def sums(list1, list2):
			assert type(list1) == type(list())
			assert type(list2) == type(list())
			assert len(list(list1)) == len(list(list2))
			return [l1 + l2 for l1, l2 in zip(list1, list2)]
		
		#Take the mean of all the requested updates...
		#Nota bene: combining backed vectors might lead to nonconvergence
		#           we should be able to learn repeatedly from a single decision
		#           and then we'll have to check for convergence
		updates = reduce(lambda acc, inc: [sum/float(len(self.backs)) for sum in sums(acc, inc)], \
		self.backs, [0.0 for weight in self.weights])
		
		assert len(self.weights) == len(updates)
		
		self.backs = []
		self.weights = [weight + (rate * update) for weight, update in zip(self.weights, updates)]
	
	def __str__(self): return "|".join([str(weight) for weight in self.weights])

class Cortex:
	def __init__(self, inputSignatures, dendrons, axons, outputSignature):
		#inputSignatures : Signature list
		#dendrons : Neuron list
		#axons : Neuron list
		#outputSignature : Signature
		self.inputSignatures = inputSignatures
		self.inputDimensions = sum(signature.dimensions for signature in inputSignatures)
		
		#hidden layer
		for dendron in dendrons: assert len(dendron.weights) == self.inputDimensions + 1
		self.dendrons = dendrons
		
		#output layer
		for axon in axons: assert len(axon.weights) == len(dendrons) + 1
		self.axons = axons
		
		assert len(axons) == outputSignature.dimensions
		self.outputSignature = outputSignature
	
	#Classification
	def feed(self, stimuli): #float list
		#stimuli : float list
		assert type(stimuli) == type(list())
		assert self.inputDimensions == len(stimuli)
		throughputs = [dendron.feed(stimuli) for dendron in self.dendrons]
		return [axon.feed(throughputs) for axon in self.axons]
	
	#Backpropagation
	def back(self, inputs, faults): #float list (faults for next level upstream)
		#inputs : float list
		#outputs : float list
		#faults : float list
		
		#inputs is the activations getting fed into all the dendrons
		#outputs is what we 
		#faults is | topmost outputs: (label - activation)
		#          | internal layers: (how much error it contributes to next higher layer = delta_higher * weight_of_my_outputs_in_higher)
		assert type(inputs) == type(list())
		assert type(faults) == type(list())
		assert len(inputs) == self.inputDimensions
		assert len(faults) == len(self.axons)
		
		def propagate(inputs, neurons, outputs, faults):
			assert type(inputs) == type(list())
			assert type(neurons) == type(list())
			assert type(outputs) == type(list())
			assert type(faults) == type(list())
			assert len(neurons) == len(outputs) and len(outputs) == len(faults)
			
			delta = lambda activation, fault: activation * (1.0 - activation) * fault
			faultsUpstream = [0.0 for input in inputs]
			for neuron, output, fault in zip(neurons, outputs, faults):
				neuronDelta = delta(output, fault)
				neuron.back(inputs, neuronDelta)
				
				faultsUpstream = \
				[accumulation + (nextWeight * neuronDelta) \
				for accumulation, nextWeight \
				in zip(faultsUpstream, neuron.weights[1:])]
			
			return faultsUpstream
		
		throughputs = [dendron.feed(inputs) for dendron in self.dendrons]
		outputs = [axon.feed(throughputs) for axon in self.axons]
		
		return propagate( \
		inputs, \
		self.dendrons, \
		throughputs, \
		propagate(throughputs, self.axons, outputs, faults) \
		)
			

class Brain:
	@classmethod
	def clone(self, parent, perturb = 0.1, mutate = 0.05):
		#brains : Brain list
		#perturb : float
		#mutate : float
		assert parent.__class__ == self
		assert type(perturb) == type(float())
		assert type(mutate) == type(float())
		
		child = self()
		
		for summary in parent.neurons:
			child.neurons[summary] = \
			Neuron([w * random.uniform(1.0 - perturb, 1.0 + perturb) \
			for w in parent.neurons[summary].weights])
		
		child.mutate(mutate)
		return child
				
	def __init__(self, path = None):
		#path : string
		self.cortices = {}
		self.neurons = {} #:(Neuron list) dictionary, keyed by signature
		self.typeDimensions = {} #:int dictionary, keyed by keys that will appear in stimuli
		self.randomWeightsRange = 0.1
		if path != None: self.loadFromPath(path)
	
	def load(self):
		assert self.path != None
		return self.loadFromPath(self.path)
	
	def loadFromPath(self, path):
		#path : string
		assert type(path) == type(str())
		self.path = path
		if not os.path.isfile(path): self.save()
		with open(path, 'r') as store:
			for line in store:
				pieces = line.strip().split("\t")
				assert len(pieces) == 2
				self.neurons[pieces[0]] = \
				Neuron([float(w) for w in pieces[1].split("|")]) #cf Neuron.__str__()
		return self
	
	def save(self):
		assert self.path != None
		return self.saveToPath(self.path)
	
	def saveToPath(self, path):
		#path : string
		assert type(path) == type(str())
		self.path = path
		with open(path, 'w') as store:
			store.write("\n".join([summary + "\t" + str(neuron) \
		for summary, neuron in zip(self.neurons.keys(), self.neurons.values())]))
		return self
	
	def update(self, rate): #void --- updates weights in all neurons
		#rate : float
		assert type(rate) == type(float())
		for neuron in self.neurons.values(): neuron.update(rate)
	
	#Useful to break free of local optima
	def mutate(self, rate):
		#rate : float
		for neuron in self.neurons.values():
			for w in range(len(neuron.weights)):
				if random.uniform(0.0, 1.0) < rate:
					neuron.weights[w] = \
					random.uniform(-self.randomWeightsRange, self.randomWeightsRange)
	
	#CLASSIFICATION
	def feedForward(self, stimulus, outputsType, outputsCount = None):
		#stimulus : Stimulus
		#outputsType : string
		#outputsCount : (int)
		
		assert stimulus.__class__ == Stimulus
		
		#First, we have to make sure (recursively)
		#       that we have evaluated all downstream stimuli
		#       on which our current classification depends
		inputs = []
		for v in range(len(stimulus.values)):
			if stimulus.values[v] == None:
				stimulus.values[v] = self.feedForward(stimulus.sources[v], stimulus.keys[v])
			elif stimulus.keys[v] not in self.typeDimensions:
				self.typeDimensions[stimulus.keys[v]] = len(stimulus.values[v])
			assert len(stimulus.values[v]) == self.typeDimensions[stimulus.keys[v]]
				
			inputs.extend(stimulus.values[v])
		
		#Now we know that inputs is a simple float list
		
		#Check outputsCount; if necessary, infer it from stimulus
		if outputsType not in self.typeDimensions:
			if outputsCount == None:
				outputsCount = int(0.5 + float(len(inputs))/2.0)
			self.typeDimensions[outputsType] = outputsCount
		elif outputsCount == None:
			outputsCount = self.typeDimensions[outputsType]
		assert self.typeDimensions[outputsType] == outputsCount
		
		inputSignatures = [Signature(kind, self.typeDimensions[kind]) for kind in stimulus.keys]
		outputSignature = Signature(outputsType, self.typeDimensions[outputsType])
		
		#return : float list
		return self.cortexForInputsOutput(inputSignatures, outputSignature).feed(inputs)
	
	#ERROR BACKPROPAGATION
	def feedBackward(self, faults, outputsType, stimulus):
		#outputs : float list
		#outputsType : string
		#stimulus : Stimulus
		
		assert stimulus.__class__ == Stimulus
		assert outputsType in self.typeDimensions
		faultsCount = len(faults)
		assert self.typeDimensions[outputsType] == faultsCount
		
		#First, we have to find out what we would have output
		outputs = self.feedForward(stimulus, outputsType)
		inputs = []
		for moreInputs in stimulus.values: inputs.extend(moreInputs)
		
		inputSignatures = [Signature(kind, self.typeDimensions[kind]) for kind in stimulus.keys]
		outputSignature = Signature(outputsType, self.typeDimensions[outputsType])
		assert len(inputs) == sum([inputSignature.dimensions for inputSignature in inputSignatures])
		faultsUpstream = self.cortexForInputsOutput(inputSignatures, outputSignature).back(inputs, faults)
		for key, source, values in zip(stimulus.keys, stimulus.sources, stimulus.values):
			if type(source) == type(stimulus):
				self.feedBackward(faultsUpstream[:len(values)], key, source)
			faultsUpstream = faultsUpstream[len(values):]
			
	#Finds the cortex (hidden + output layers) that can process given inputs to get a desired output
	def cortexForInputsOutput(self, inputSignatures, outputSignature):
		#inputSignatures : Signature list
		#outputSignature : Signature
		
		assert outputSignature.__class__ == Signature
		
		inputsSummary = " * ".join([str(inputSignature) for inputSignature in inputSignatures])
		outputsSummary = str(outputSignature)
		
		inputsCount = sum([inputSignature.dimensions for inputSignature in inputSignatures])
		
		cortexSignature = inputsSummary + " -> " + outputsSummary
		
		#Returns the appropriate Cortex instance; if necessary, creates anew
		if cortexSignature not in self.cortices:
			dendronsCount = int((inputsCount * outputSignature.dimensions)**(0.5)) + 1
			dendrons = self.neuronsForSignatures( \
			[inputsSummary + " -> " + str(d) + "/" + str(dendronsCount) for d in map(lambda d: d+1, range(dendronsCount))], \
			inputsCount \
			)
			
			axonsCount = outputSignature.dimensions
			axons = self.neuronsForSignatures( \
			[str(dendronsCount) + " -> (" + str(a) + "/" + str(axonsCount) + ") " + outputsSummary for a in map(lambda a: a+1, range(axonsCount))], \
			dendronsCount \
			)
			
			self.cortices[cortexSignature] = \
			Cortex(inputSignatures, dendrons, axons, outputSignature)
		
		return self.cortices[cortexSignature]
	
	#Finds neurons that will process what we're trying to process
	def neuronsForSignatures(self, signatures, inputsCount):
		#signatures : Signature list
		#inputsCount : int
		neurons = []
		for signature in signatures:
			if signature not in self.neurons:
				self.neurons[signature] = \
				Neuron( \
				[random.uniform(-self.randomWeightsRange, self.randomWeightsRange) for i in range(inputsCount+1)] \
				) #remember the constant term!
			neurons.append(self.neurons[signature])
		return neurons