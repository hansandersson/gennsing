#Copyright (c) Hans Andersson 2011
#All rights reserved.

#################################################
### UNIMPLEMENTED CANDIDATE FOR EARLY TESTING ###
#################################################

class Game:
	def __init__(self, playersCount = 5, size = 100.0, sparsity = 200000.0):
		self.map = Map(size, sparsity)
		
		
class Map:
	def __init__(self, size, sparsity):
		self.size = size
		self.systems = [System(random.uniform(-self.size, self.size), random.uniform(-self.size, self.size), random.uniform(-self.size, self.size)) for p in int(range(((2.0 * size) ** 3.0) / sparsity))]

class System:
	def __init__(self, x, y, z):
		self.coordinates = (x, y, z)

class Unit: