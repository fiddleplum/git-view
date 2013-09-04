#!/usr/bin/python

import subprocess
import os
import sys
import time

gitPath = '/bin/git'

if len(sys.argv) != 2:
	print("Syntax: py git-view.py <path-to-git-repo>")
	exit(0)

path = " ".join(sys.argv[1:])
if path[-1] != "/":
	path = path + "/"

def callGit (args):
	pr = subprocess.Popen([gitPath] + args.split(' '), cwd=path, shell = False, stdout = subprocess.PIPE, stderr = subprocess.PIPE )
	(out, error) = pr.communicate()
	if len(error) != 0:
		print("Error running git " + args + ":\n" + error.decode('UTF-8'))
		exit(0)
	return out.decode('UTF-8').split('\n')

# get branches
branchLines = callGit('branch -a')
branchNames = []
for branchLine in branchLines:
	if len(branchLine) == 0:
		continue
	branchName = branchLine[2:]
	if branchName.startswith('remotes/origin/HEAD'):
		continue
	if branchName.startswith('remotes/'):
		branchName = branchName[8:]
	branchNames.append(branchName)

# get commits
headCommits = []
commits = {}
commitsByDate = {}
for branchName in branchNames:
	count = 0
	lastCommit = None
	logLines = callGit('log --date=raw ' + branchName)
	for logLine in logLines:
		if logLine.startswith('commit '):
			name = logLine[7:]
			if name in commits:
				commits[name]['branches'].append(branchName)
			else:
				commit = {}
				commit['name'] = name
				commit['branches'] = [branchName]
				commit['children'] = []
				commit['parents'] = []
				commit['count'] = 0
				commits[name] = commit
			if lastCommit is not None:
				commits[lastCommit]['children'].append(name)
			else:
				headCommits.append(name)
			lastCommit = name
		elif logLine.startswith('Date'):
			date = logLine[8:-6]
			commits[lastCommit]['date'] = date
			commitsByDate[date] = lastCommit
for date in sorted(commitsByDate.keys(), reverse=True):
	commitName = commitsByDate[date]
	for childCommitName in commits[commitName]['children']:
		commits[childCommitName]['count'] = max(commits[childCommitName]['count'], commits[commitName]['count'] + 1)

# get parents of each commit
for commitName in commits:
	commits[commitName]['parents'] = (callGit('rev-list --parents -n 1 ' + commitName)[0].split(' '))[1:]

# print html
f = open('html/git-view.html', 'w')
print('<html><body>', file =f )

# print graph
print('''
<script type="text/javascript" src="js/jquery-1.4.2.min.js"></script>
<script type="text/javascript" src="js/raphael-min.js"></script>
<script type="text/javascript" src="js/dracula_graffle.js"></script>
<script type="text/javascript" src="js/dracula_graph.js"></script>
<script type="text/javascript">
<!--

var redraw;
var height = 3000;
var width = 4000;

/* only do all this when document has finished loading (needed for RaphaelJS */
window.onload = function()
{
	var g = new Graph();

''', file = f)

for commitName in commits:
	for parentCommitName in commits[commitName]['parents']:
		print('g.addEdge("' + commitName[:8] + '", "' + parentCommitName[:8] + '");', file = f)

print('''
	/* layout the graph using the Spring layout implementation */
	var layouter = new Graph.Layout.Spring(g);
	layouter.layout();

	/* draw the graph using the RaphaelJS draw implementation */
	var renderer = new Graph.Renderer.Raphael('canvas', g, width, height);
	renderer.draw();

	redraw = function()
	{
		layouter.layout();
		renderer.draw();
	};
};

-->
</script>
<div id="canvas"></div>
<button id="redraw" onclick="redraw();">redraw</button>
''', file = f)

# print top of table
print('<table><tr><td>Commit</td>', file = f)
for branchName in branchNames:
	print('<td>' + branchName + '</td>', file = f)
print('</tr>', file = f)

# print commit rows
for date in sorted(commitsByDate.keys(), reverse=True):
	commitName = commitsByDate[date]
	print('<tr><td>' + commitName[:8] + '</td>', file = f)
	for branchName in branchNames:
		if branchName in commits[commitName]['branches']:
			print('<td>X</td>', file = f)
		else:
			print('<td></td>', file = f)
	print('</tr>', file = f)
print('</table></body></html>', file = f)

