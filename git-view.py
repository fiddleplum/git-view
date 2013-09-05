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
				commit['HEAD'] = []
				commit['level'] = 0
				commits[name] = commit
			if lastCommit is not None:
				commits[lastCommit]['children'].append(name)
			else:
				commits[name]['HEAD'].append(branchName)
			lastCommit = name
		elif logLine.startswith('Date'):
			date = logLine[8:-6]
			commits[lastCommit]['date'] = date
			commitsByDate[date] = lastCommit
		elif logLine.startswith('    Merge branch'):
			

# get parents of each commit
for commitName in commits:
	commits[commitName]['parents'] = (callGit('rev-list --parents -n 1 ' + commitName)[0].split(' '))[1:]

# get commit levels
maxLevel = 0
for date in sorted(commitsByDate.keys(), reverse=True):
	commitName = commitsByDate[date]
	for parentCommitName in commits[commitName]['parents']:
		commits[parentCommitName]['level'] = max(commits[parentCommitName]['level'], commits[commitName]['level'] + 1)
	maxLevel = max(maxLevel, commits[commitName]['level'])

# get node text for each commit
for commitName in commits:
	commits[commitName]['nodetext'] = commits[commitName]['name'][:8]

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
var height = ''' + str(400) + ''';
var width = ''' + str(maxLevel * 100) + ''';

var render = function(r, n) {
	/* the Raphael set is obligatory, containing all you want to display */
	var set = r.set().push(
		/* custom objects go here */
		r.rect(n.point[0]-30, n.point[1]-13, 62, 86)
			.attr({"fill": "#fa8", "stroke-width": 2, r : "9px"}))
			.push(r.text(n.point[0], n.point[1] + 30, n.label)
				.attr({"font-size":"20px"}));
	/* custom tooltip attached to the set */
	set.items.forEach(
		function(el) {
			el.tooltip(r.set().push(r.rect(0, 0, 30, 30)
				.attr({"fill": "#fec", "stroke-width": 1, r : "9px"})))});
	return set;
};

/* only do all this when document has finished loading (needed for RaphaelJS */
window.onload = function()
{
	var g = new Graph();
	var levels = {};

''', file = f)

#### TODO: Add new layout that takes levels of nodes. Then at each node, it sets it a h * hlevel for the x position, and for the vertical, keeps a counter of how many are already at that level, doing v * vlevel for the y position.

for commitName in commits:
	print('''
		node = g.addNode("''' + commits[commitName]['nodetext'] + '''");
		node.innerid = "''' + ','.join(commits[commitName]['HEAD']) + '''";
		''', file = f)
	print(','.join(commits[commitName]['HEAD']))

for commitName in commits:
	for parentCommitName in commits[commitName]['parents']:
		print('g.addEdge("' + commits[parentCommitName]['nodetext'] + '", "' + commits[commitName]['nodetext'] + '", { directed : true } );', file = f)

for commitName in commits:
	print('levels["' + commits[commitName]['nodetext'] + '"] = ' + str(commits[commitName]['level']) + ';', file = f)

print('''
	/* layout the graph using the Spring layout implementation */
	var layouter = new Graph.Layout.Leveled(g, levels);
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
<div id='console'></div>
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
	print('<tr><td>' + commits[commitName]['nodetext'] + '</td>', file = f)
	for branchName in branchNames:
		if branchName in commits[commitName]['branches']:
			print('<td>X</td>', file = f)
		else:
			print('<td></td>', file = f)
	print('</tr>', file = f)
print('</table></body></html>', file = f)

