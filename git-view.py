#!/usr/bin/env python3.2

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
#		print("Error running git " + args + ":\n" + error.decode('UTF-8'))
		return None
	else:
		return out.decode('UTF-8').split('\n')

def newCommit (name):
	commit = {}
	commit['name'] = name
	commit['branches'] = set() # set of branches at this commit
	commit['merge'] = [] # list of branch names from a merge
	commit['parents'] = [] # list of parents commits (from merges or just previous commits)
	commit['children'] = [] # list of children commits
	commit['level'] = 0
	return commit

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

# add only the remotes we care about
remoteBranchNames = []
for branchName in activeBranchNames:
	remoteBranchNames.append('origin/' + branchName)
activeBranchNames.extend(remoteBranchNames)

# get commits
headCommits = []
commits = {}
commitsByDate = {}
remotes = []
merges = []

for branchName in activeBranchNames:
	count = 0
	lastCommit = None
	logLines = callGit('log --date=raw ' + (('-n ' + sys.argv[2] + ' ') if len(sys.argv) == 3 else '') + branchName)
	if logLines is None:
		continue # not a valid branch, so ignore it
	for logLine in logLines:
		if logLine.startswith('commit '):
			name = logLine[7:]
			if name not in commits:
				commit = newCommit(name)
				commits[name] = commit
			if lastCommit is None:	
				commits[name]['branches'].add(branchName)
			lastCommit = name
		elif logLine.startswith('Date'):
			date = int(logLine[8:-6])
			commits[lastCommit]['date'] = date
			commitsByDate[date] = lastCommit
		elif logLine.startswith('    Merge branch \''):
			fromBranchNameEndIndex = logLine.find('\'', 18)
			firstRemote = (logLine[fromBranchNameEndIndex + 2:fromBranchNameEndIndex + 4] == 'of')
			fromBranch = ('origin/' if firstRemote else '') + logLine[18:fromBranchNameEndIndex]
			branchNames.add(fromBranch)
			toBranchNameStartIndex = logLine.find('into ')
			if toBranchNameStartIndex != -1:
				toBranch = logLine[5 + toBranchNameStartIndex:]
				branchNames.add(toBranch)
			else:
				toBranch = 'master' # if no to branch is named, it defaults to master
				# BUG : this is slightly broken, because it may be either master or origin/master
			merges.append([lastCommit, fromBranch, toBranch])
		elif logLine.startswith('    Merge pull request'):
			fromBranchNameStartIndex = logLine.rfind(' ') + 1
			toBranch = ''
			fromBranch = logLine[fromBranchNameStartIndex:]
			branchNames.add(fromBranch)
			merges.append([lastCommit, fromBranch, toBranch])

# get parents of each commit
dummyCommits = {}
for commitName in commits:
	commits[commitName]['parents'] = (callGit('rev-list --parents -n 1 ' + commitName)[0].split(' '))[1:]
	for parentCommitName in commits[commitName]['parents']:
		if parentCommitName in commits and commitName not in commits[parentCommitName]['children']:
			commits[parentCommitName]['children'].append(commitName)
		elif parentCommitName not in commits and parentCommitName not in dummyCommits:
			# make a dummy commit
			commit = newCommit(parentCommitName)
			commit['date'] = min(commitsByDate) - 1
			dummyCommits[parentCommitName] = commit
			commitsByDate[commit['date']] = parentCommitName
commits.update(dummyCommits)

# fill in branch info based on merge comments
for merge in merges:
	commitName = merge[0]
	fromBranch = merge[1]
	toBranch = merge[2]
	if commits[commitName]['parents'][0] in commits:
		if toBranch != '':
			commits[commitName]['branches'].add(toBranch)
			commits[commits[commitName]['parents'][0]]['branches'].add(toBranch)
		else:
			commits[commits[commitName]['parents'][0]]['branches'].update(commits[commitName]['branches'])
	if commits[commitName]['parents'][1] in commits:
		if fromBranch != '':
			commits[commits[commitName]['parents'][1]]['branches'].add(fromBranch)

# propagate the branches to the ancestors
for date in sorted(commitsByDate.keys(), reverse=True):
	commitName = commitsByDate[date]
	if len(commits[commitName]['parents']) == 1:
		if commits[commitName]['parents'][0] in commits:
			if len(commits[commits[commitName]['parents'][0]]['children']) == 1:
				if len(commits[commits[commitName]['parents'][0]]['branches']) == 0:
					commits[commits[commitName]['parents'][0]]['branches'].update(commits[commitName]['branches'])
			elif len(commits[commits[commitName]['parents'][0]]['children']) == 2:
				for branchName in commits[commitName]['branches']:
					if branchName in ['master', 'staging', 'production', 'origin/master', 'origin/staging', 'origin/production']:
						commits[commits[commitName]['parents'][0]]['branches'].add(branchName)

		# noBranchParentName = ''
		# for parentName in commits[commitName]['parents']:
			# if parentName in commits and branchName in commits[parentName]['branches']:
				# noBranchParentName = ''
				# break # the branch is already in a parent
			# if parentName in commits and len(commits[parentName]['branches']) == 0:
				# if noBranchParentName is not '':
					# noBranchParentName = ''
					# break # more than one parent with no branch
				# noBranchParentName = parentName
		# if noBranchParentName is not '':
			# commits[noBranchParentName]['branches'].add(branchName)

# propogate the branches to the descendants
# for date in sorted(commitsByDate.keys(), reverse=False):
	# commitName = commitsByDate[date]
	# for branchName in commits[commitName]['branches']:
		# noBranchChildName = ''
		# for childName in commits[commitName]['children']:
			# if childName in commits and branchName in commits[childName]['branches']:
				# noBranchChildName = ''
				# break # the branch is already in a child
			# if childName in commits and len(commits[childName]['branches']) == 0:
				# if noBranchChildName is not '':
					# noBranchChildName = ''
					# break # more than one child with no branch
				# noBranchChildName = childName
		# if noBranchChildName is not '':
			# commits[noBranchChildName]['branches'].add(branchName)

# get commit levels
maxLevel = 0
count = 0
for date in sorted(commitsByDate.keys(), reverse=True):
	commitName = commitsByDate[date]
	commits[commitName]['level'] = count
	count = count + 1
	# for parentCommitName in commits[commitName]['parents']:
		# if parentCommitName in commits:
			# commits[parentCommitName]['level'] = max(commits[parentCommitName]['level'], commits[commitName]['level'] + 1)
	maxLevel = max(maxLevel, commits[commitName]['level'])

# get node text for each commit
for commitName in commits:
	commits[commitName]['nodetext'] = commits[commitName]['name'][:8] + ' ' + str(commits[commitName]['date'])

# print html
f = open('html/git-view.html', 'w')
print('<html><body>', file = f )

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

/* only do all this when document has finished loading (needed for RaphaelJS */
window.onload = function()
{
	var g = new Graph();
	var levels = {};

''', file = f)

for commitName in commits:
	print('''
		node = g.addNode("''' + commits[commitName]['nodetext'] + '''");
		node.innerid = "''' + ' '.join(commits[commitName]['branches']) + '''";
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

