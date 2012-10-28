#!/usr/bin/env python

import urllib, re, os, sys

def clean(data): return '\n'.join(data.strip().split('\n')[1:])

etfsList = urllib.urlopen("http://www.masterdata.com/HelpFiles/ETF_List_Downloads/AllETFs.csv").read().strip().split('\n')
symbolsColumnIndex = etfsList[0].split(',').index("Symbol")
symbols = [etf.split(',')[symbolsColumnIndex] for etf in etfsList[1:]]

for symbol in symbols:
	baseURL = "http://ichart.finance.yahoo.com/table.csv?s=%s" % symbol
	with open("./charts/%s" % symbol, 'w') as store:
		store.write(clean(urllib.urlopen(baseURL).read()))
	with open("./dividends/%s" % symbol, 'w') as store:
		store.write(clean(urllib.urlopen("%s&g=v" % baseURL).read()))