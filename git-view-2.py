#!/usr/bin/python

import subprocess
import os
import sys
import time
import cgi
import datetime

gitPath = '/bin/git'

if len(sys.argv) < 2:
	print("Syntax: py git-view-2.py <path-to-git-repo> <maximum-number-commits-on-each-branch>")
	exit(0)

path = sys.argv[1]
if path[-1] != "/":
	path = path + "/"

def callGit (args):
	pr = subprocess.Popen([gitPath] + args.split(' '), cwd=path, shell = False, stdout = subprocess.PIPE, stderr = subprocess.PIPE )
	(out, error) = pr.communicate()
	if len(error) != 0:
#		print("Error running git " + args + ":\n" + error.decode('UTF-8'))
		return None
	else:
		return out.decode('UTF-8').split('\n')

def newCommit (name):
	commit = {}
	commit['name'] = name
	commit['date'] = 0
	commit['author'] = ''
	commit['desc'] = ''
	return commit

def newBranch (name):
	branch = {}
	branch['name'] = name
	branch['commits'] = set()
	return branch

# get branches
branchLines = callGit('branch -a')
branches = {}
for branchLine in branchLines:
	if len(branchLine) == 0:
		continue
	branchName = branchLine[2:]
	if branchName.startswith('remotes/origin/HEAD'):
		continue
	if branchName.startswith('remotes/'):
		branches[branchName[8:]] = newBranch(branchName[8:])
	else:
		branches[branchName] = newBranch(branchName)

# get commits
commits = {}

for branchName in branches:
	branch = branches[branchName]
	count = 0
	lastCommit = None
	logLines = callGit('log --date=raw --no-merges ' + (('-n ' + sys.argv[2] + ' ') if len(sys.argv) == 3 else '') + branch['name'])
	skipCommit = False
	if logLines is None:
		continue # not a valid branch, so ignore it
	for logLine in logLines:
		logLine = logLine.strip(' \t')
		if logLine is '':
			continue
		if logLine.startswith('commit '):
			name = logLine[7:]
			if name not in commits:
				lastCommit = newCommit(name)
				commits[name] = lastCommit
				skipCommit = False
			else:
				lastCommit = commits[name]
				skipCommit = True
			branch['commits'].add(name)
		elif logLine.startswith('Date'):
			if not skipCommit:
				try:
					lastCommit['date'] = int(logLine[8:-6])
				except ValueError:
					continue
		elif logLine.startswith('Author'):
			if not skipCommit:
				lastCommit['author'] = logLine[8:]
		else:
			if not skipCommit:
				if len(lastCommit['desc']) > 0:
					lastCommit['desc'] += '<br />'
				lastCommit['desc'] += logLine.replace("&", r"&amp;").replace("<", r"&lt;").replace(">", r"&gt;").replace("\"", r"&quot;").replace("\'", r"\'")

# get sorted by dates
commitsByDate = {}
for commitName in commits:
	commitsByDate[commits[commitName]['date']] = commitName

# print html
f = open('html/git-view-2.html', 'w')
print('<html><body><div id="info" style="position:fixed; left: 0; top: 0; min-height: 6em;"></div>', file = f )

# print graph
print('<table border=1 style="border: 2px solid black; margin-top: 6em;" cellpadding=2 cellspacing=0><tr><td></td>', file = f)

for date in sorted(commitsByDate.keys(), reverse=True):
	commit = commits[commitsByDate[date]]
	print('''<td onmouseout="document.getElementById('info').innerHTML='';" onmouseover="document.getElementById('info').innerHTML=\'''' + commit['name'] + '<br />' + datetime.datetime.fromtimestamp(commit['date']).strftime('%Y-%m-%d %H:%M:%S') + '<br />' + commit['author'] + '<br />' + commit['desc'] + '''\';">''' + commit['name'][:4] + '</td>', file = f)
print('</tr>', file = f)

def printBranch(branch):
	even = True
	print('<tr><td>' + branch['name'] + '</td>', file = f)
	for date in sorted(commitsByDate.keys(), reverse=True):
		commit = commits[commitsByDate[date]]
		print('<td style="align: center; background-color: ' + ('#000000' if (commit['name'] in branch['commits']) else ('#ffa577' if even else 'skyblue')) + ';"></td>', file = f)
		even = not even
	print('</tr>', file = f)

printBranch(branches['origin/production'])
printBranch(branches['production'])
printBranch(branches['origin/staging'])
printBranch(branches['staging'])
printBranch(branches['origin/master'])
printBranch(branches['master'])
for branchName in branches:
	branch = branches[branchName]
	if branch['name'] in ['origin/production', 'production', 'origin/staging', 'staging', 'origin/master', 'master']:
		continue;
	printBranch(branch)

print('</table></body></html>', file = f)

