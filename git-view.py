#!/usr/bin/python

import subprocess
import os
import sys
import time

gitPath = '/bin/git'

if len(sys.argv) < 2:
	print("Syntax: py git-view.py <path-to-git-repo> <maximum-number-commits-on-each-branch>")
	exit(0)

path = sys.argv[1]
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
activeBranchNames = []
for branchLine in branchLines:
	if len(branchLine) == 0:
		continue
	branchName = branchLine[2:]
	if branchName.startswith('remotes/origin/HEAD'):
		continue
	if branchName.startswith('remotes/'):
		continue
	activeBranchNames.append(branchName)
branchNames = set()
branchNames.update(activeBranchNames)

# get commits
headCommits = []
commits = {}
commitsByDate = {}
remotes = []

for branchName in activeBranchNames:
	count = 0
	lastCommit = None
	logLines = callGit('log --date=raw ' + (('-n ' + sys.argv[2] + ' ') if len(sys.argv) == 3 else '') + branchName)
	for logLine in logLines:
		if logLine.startswith('commit '):
			name = logLine[7:]
			if name not in commits:
				commit = {}
				commit['name'] = name
				commit['branch'] = '' # set of branches at this commit
				commit['merge'] = [] # list of branch names from a merge
				commit['parents'] = [] # list of parents commits (from merges or just previous commits)
				commit['children'] = [] # list of children commits
				commit['level'] = 0
				commits[name] = commit
			if lastCommit is None:	
				commits[name]['branch'] = branchName
			lastCommit = name
		elif logLine.startswith('Date'):
			date = logLine[8:-6]
			commits[lastCommit]['date'] = date
			commitsByDate[date] = lastCommit
		elif logLine.startswith('    Merge branch'):
			if len(commits[lastCommit]['merge']) == 0:
				firstBranchNameEndIndex = logLine.find('\'', 18)
				firstRemote = (logLine[firstBranchNameEndIndex + 2:firstBranchNameEndIndex + 4] == 'of')
### TODO: Make remotes unique.
				secondBranchNameStartIndex = logLine.find('into ')
				if secondBranchNameStartIndex != -1:
					branch1 = logLine[5 + secondBranchNameStartIndex:]
					commits[lastCommit]['merge'].append(branch1)
					branchNames.add(branch1)
				else:
					commits[lastCommit]['merge'].append('')
				branch2 = ('remote:' if firstRemote else '') + logLine[18:firstBranchNameEndIndex]
				commits[lastCommit]['merge'].append(branch2)
				branchNames.add(branch2)
		elif logLine.startswith('    Merge pull request'):
			if len(commits[lastCommit]['merge']) == 0:
				firstBranchNameEndIndex = logLine.find('\'', 18)
				firstRemote = (logLine[firstBranchNameEndIndex + 2:firstBranchNameEndIndex + 4] == 'of')
				secondBranchNameStartIndex = logLine.rfind(' ') + 1
				commits[lastCommit]['merge'].append('')
				branch2 = logLine[secondBranchNameStartIndex:]
				commits[lastCommit]['merge'].append(branch2)
				branchNames.add(branch2)
				print(str(commits[lastCommit]['merge']))

# get parents of each commit
for commitName in commits:
	commits[commitName]['parents'] = (callGit('rev-list --parents -n 1 ' + commitName)[0].split(' '))[1:]
	for parentCommitName in commits[commitName]['parents']:
		if parentCommitName in commits and commitName not in commits[parentCommitName]['children']:
			commits[parentCommitName]['children'].append(commitName)

# fill in rest of branch info
for date in sorted(commitsByDate.keys(), reverse=True):
	commitName = commitsByDate[date]
	if len(commits[commitName]['merge']) == 2:
		if commits[commitName]['merge'][0] != '' and commits[commitName]['parents'][0] in commits:
			commits[commits[commitName]['parents'][0]]['branch'] = commits[commitName]['merge'][0]
			commits[commitName]['branch'] = commits[commitName]['merge'][0]
		if commits[commitName]['merge'][1] != '' and commits[commitName]['parents'][1] in commits:
			commits[commits[commitName]['parents'][1]]['branch'] = commits[commitName]['merge'][1]
for date in sorted(commitsByDate.keys(), reverse=True):
	commitName = commitsByDate[date]
	branchName = commits[commitName]['branch']
	noBranchParentName = ''
	for parentName in commits[commitName]['parents']:
		if parentName in commits and branchName == commits[parentName]['branch']:
			noBranchParentName = ''
			break # the branch is already in a parent
		if parentName in commits and commits[parentName]['branch'] == '':
			if noBranchParentName is not '':
				noBranchParentName = ''
				break # more than one parent with no branch
			noBranchParentName = parentName
	if noBranchParentName is not '':
		commits[noBranchParentName]['branch'] = branchName
# for date in sorted(commitsByDate.keys(), reverse=False):
	# commitName = commitsByDate[date]
	# branchName = commits[commitName]['branch']
	# noBranchChildName = ''
	# for childName in commits[commitName]['children']:
		# if childName in commits and branchName == commits[childName]['branch']:
			# noBranchChildName = ''
			# break # the branch is already in a child
		# if childName in commits and commits[childName]['branch'] == '':
			# if noBranchChildName is not '':
				# noBranchChildName = ''
				# break # more than one child with no branch
			# noBranchChildName = childName
	# if noBranchChildName is not '':
		# commits[noBranchChildName]['branch'] = branchName

# get commit levels
maxLevel = 0
for date in sorted(commitsByDate.keys(), reverse=True):
	commitName = commitsByDate[date]
	for parentCommitName in commits[commitName]['parents']:
		if parentCommitName in commits:
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
var height = ''' + str(len(branchNames) * 60) + ''';
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

for commitName in commits:
	print('''
		node = g.addNode("''' + commits[commitName]['nodetext'] + '''");
		node.innerid = "''' + commits[commitName]['branch'] + '''";
		''', file = f)
#	print(','.join(commits[commitName]['HEAD']))

for commitName in commits:
	for parentCommitName in commits[commitName]['parents']:
		if parentCommitName in commits:
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
print('</body></html>', file = f)

