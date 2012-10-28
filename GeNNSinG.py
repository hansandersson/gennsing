#!/usr/bin/env python

#Copyright (c) Hans Andersson 2011
#All rights reserved.

import os, sys, random, datetime
import Interface, GeneticArena

class OptionError(Exception): pass

### FIRST COMMAND-LINE ARGUMENT === GAME-ENVIRONMENT
if not len(sys.argv) > 1: raise OptionError("Environment missing")
environmentName = sys.argv[1]
cwd = os.getcwd()
os.chdir(os.path.dirname(sys.argv[0]) + "/")
Environment = __import__(environmentName, globals(), locals(), ["Environment"], -1).Environment
os.chdir(cwd)

#initialize the GeneticArena, which takes care of the genetic algorithm
arenaManager = GeneticArena.Manager(environmentName)
countMin, countMax = Environment.getPlayersCountRange()

### OPTION DEFAULTS
consoleNames, brainNames = set(), set()
automatic, compsCount = False, None
stall, target, iterationsSinceProgress = None, None, 0

### COMMAND-LINE OPTION/ARGUMENT PARSER
for a in range(len(sys.argv[2:])):
	option = sys.argv[2:][a]
	
	while option[0] == '-': option = option[1:]
	argument = None
	if ':' in option: option, argument = option.split(':')
	elif '=' in option: option, argument = option.split('=')
	
	if option in ('h', '?', "help"):
		raise SystemExit
	elif option in ('a', "automate", "auto", "automatic"):
		automatic = int(argument) if argument != None else True
	elif option in ('u', "users", "user"):
		if argument == None:
			a += 1
			argument = sys.argv[2:][a]
		consoleNames = set(argument.split(','))
		for name in consoleNames: assert name.isalpha()
	elif option in ('b', "brain", "brains"):
		if argument == None:
			a += 1
			argument = sys.argv[2:][a]
		brainNames = set(argument.split(','))
		for name in brainNames: assert name.isalpha()
	elif option in ('c', "count", "comps_count", "computers_count"):
		if argument == None:
			a += 1
			argument = sys.argv[2:][a]
		compsCount = int(argument)
		if compsCount < countMin or compsCount > countMax: compsCount = None
		else: countMin, countMax = compsCount, compsCount
	elif option in ('s', "stall"):
		if argument == None:
			a += 1
			argument = sys.argv[2:][a]
		stall = int(argument)
		assert stall > 0
	elif option in ('t', "test", "target", "threshold"):
		if argument == None:
			a += 1
			argument = sys.argv[2:][a]
		target = int(argument)
	else: raise OptionError("option '%s' unrecognized" % option)

os.system("clear")

if compsCount != None:
	arenaManager.minimumBrainsCount = max(arenaManager.minimumBrainsCount, compsCount)
	arenaManager.fill()

if automatic != False: #let the computer improve by playing itself
	winner = None
	performanceMax = None
	i = 1
	while (automatic == True or not i > automatic) \
	and (stall == None or stall > iterationsSinceProgress) \
	and (target == None or performanceMax == None or target > performanceMax):
		agents = set()
		if winner != None: agents.add(winner)
		
		agents |= arenaManager.getAIs( \
		count = random.randint(countMin, countMax) - len(agents), \
		namesPreferred = brainNames, \
		namesExcluded = (set([winner.name]) if winner != None else set()) \
		)
		
		os.system("printf 'Game %(i)i : %(names)s\n'" % {"i":i, "names":" vs ".join([agent.name for agent in agents])})
		
		#GeneticArena takes care of game.doRound() until game.getCompletion() == 100.0
		game = Environment.Game(agents)
		GeneticArena.autoplay(game)
		
		if performanceMax == None or game.getPerformance() > performanceMax:
			performanceMax = game.getPerformance()
			iterationsSinceProgress = 0
		else: iterationsSinceProgress += 1
		
		#any end-of-game stuff, then return the players, from winner to loser
		agentsRanked = game.getRanking()
		
		winner = agentsRanked[0][0]
		losers = [agent for agent, quantifier in agentsRanked[1:]]
		loser = losers[-1]
		#updates the win / loss record for each participant
		arenaManager.updateWinnersLosers(set([winner]), set(losers))
		
		#updates the neural network through error backpropagation
		arenaManager.teachStudents(winner)
		
		#natural selection
		arenaManager.kill(loser)
		arenaManager.fill(winner) #clones the winner, with minor mutation
		
		i += 1

else: #INTERACTIVE
	#sets up the console Agent and gets AIs
	agents = set([Interface.IO(consoleName) for consoleName in consoleNames]) | \
	arenaManager.getAIs( \
	count = random.randint(countMin, countMax), \
	namesPreferred = brainNames, \
	namesExcluded = consoleNames \
	)
	
	#run the game until completion
	game = Environment.Game(agents)
	while game.getCompletion() < 100.0:
		os.system("clear");
		os.system("printf '%(names)s\n%(game)s\n'" % {"names":" vs ".join([agent.name for agent in agents]), "game":str(game)})
		game.doRound()
	game.finalize()
	
	#again, finalize the game and rank the players by performance, from winner to loser
	agentsRanked = game.getRanking()
	
	#print the standings
	os.system("printf '%s\n'" % \
	"\n".join([str(rank) + ": " + agent.name + " (" + str(quantifier) + ")" \
	for rank, (agent, quantifier) in zip(range(1, len(agentsRanked)+1), agentsRanked)]) \
	)
		
	winner = agentsRanked[0][0]
	
	#write a human-readable review for the console player if the AI won
	if isinstance(winner, Interface.AI):
		for agent in filter(lambda agent: isinstance(agent, Interface.IO), agents):
			with open("./" + environmentName + "/reviews/" + str(datetime.datetime.now()) + " @ " + agent.name + ".txt", 'w') as annotation:
				annotation.write(agent.consult(winner))
	
	#update the neural networks, even if the console user won
	arenaManager.teachStudents(winner)