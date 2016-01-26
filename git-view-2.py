#!/usr/bin/env python3

import subprocess
import os
import sys
import time
import cgi
import datetime

gitPath = '/usr/bin/git'

if len(sys.argv) < 3:
	print("--Instructions--")
	print("./git-view-2.py <path-to-git-repo> <maximum-number-of-commits-on-each-branch> [no-merges] [sort-branches-by-date]")
	print("  The script will create an HTML file, 'html/git-view-2.html', that you can view in any browser.")
	print("  The HTML file is a giant table, where the columns are commits and the rows are branches")
	print("    of the repository pointed to via <path-to-git-repo>.")
	print("  Since some repositories can have a large history, you can set the <maximum-number-of-commits-on-each-branch>")
	print("    to only process that number of commits on any given branch.")
	print("  You also may want to ignore merges so that you can just see the content changes (beware of content changes")
	print("    from merge conflicts, though), by adding 'no-merges'.")
	print("  You also may want to sort the branches by their last commit date, so you can see which branches are stale,")
	print("    by adding 'sort-branches-by-date'.")
	print("  Once the HTML file is being viewed, feel free to scroll around to see what branches have which commits.")
	print("  Green commits mean that the commit is also in 'origin/production', blue for 'origin/staging', and red for 'origin/master',")
	print("    with green overriding blue overriding red. Black means it is in none of these branches.")
	print("  Green branches mean that every commit in that branch is also in 'origin/production', and similarly for blue and red branches.")
	print("    If a branch has at least one commit in none of the special branches, then it is black.")
	print("  You may also hover over a commit id at the top to get details on the commit.")
	exit(0)

# get params
path = sys.argv[1]
if path[-1] != "/":
	path = path + "/"

numCommits = int(sys.argv[2])

noMerges = False
sortBranchesByDate = False
for arg in sys.argv:
	if arg == 'no-merges':
		noMerges = True
	if arg == 'sort-branches-by-date':
		sortBranchesByDate = True

def callGit (args, failOnError = True):
	pr = subprocess.Popen([gitPath] + args.split(' '), cwd=path, shell = False, stdout = subprocess.PIPE, stderr = subprocess.PIPE )
	(out, error) = pr.communicate()
	if len(error) != 0 and failOnError:
		print('Error: ' + error.decode('UTF-8'))
		return None
	else:
		return out.decode('UTF-8').split('\n')

def newCommit (name):
	commit = {}
	commit['name'] = name
	commit['date'] = 0
	commit['author'] = ''
	commit['desc'] = ''
	commit['count'] = 0
	return commit

def newBranch (name):
	branch = {}
	branch['name'] = name
	branch['commits'] = set()
	branch['latestcommit'] = ''
	branch['display'] = name
	branch['local'] = True
	return branch

# make sure we have all the infos
callGit('fetch -p', False)

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
		branches[branchName[8:]]['display'] = branchName[8:].partition('/')[2] + ' (' + branchName[8:].partition('/')[0] + ')'
		branches[branchName[8:]]['local'] = False
	else:
		branches[branchName] = newBranch(branchName)

# get commits
commits = {}

for branchName in branches:
	branch = branches[branchName]
	count = 0
	lastCommitName = ''
	if noMerges:
		mergeOption = '--no-merges '
	else:
		mergeOption = ''
	logLines = callGit('log --date=raw ' + mergeOption + '-n ' + str(numCommits) + ' ' + ('heads/' if branch['local'] else 'remotes/') + branch['name'] + ' --')
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
				commit = newCommit(name)
				commits[name] = commit
				skipCommit = False
			else:
				skipCommit = True
			lastCommitName = name
			if branch['latestcommit'] == '':
				branch['latestcommit'] = name
			branch['commits'].add(name)
		elif logLine.startswith('Date'):
			if not skipCommit:
				try:
					commits[lastCommitName]['date'] = int(logLine[8:-6])
				except ValueError:
					continue
		elif logLine.startswith('Author'):
			if not skipCommit:
				commits[lastCommitName]['author'] = logLine[8:].replace("<", r"&lt;").replace(">", r"&gt;")
		else:
			if not skipCommit:
				if len(commits[lastCommitName]['desc']) > 0:
					commits[lastCommitName]['desc'] += '<br />'
				commits[lastCommitName]['desc'] += logLine.replace("&", r"&amp;").replace("<", r"&lt;").replace(">", r"&gt;")

# get tags
tags = callGit('tag')
for tag in tags:
	if tag is '':
		continue
	lines = callGit('show ' + tag)
	if lines is not None:
		for line in lines:
			if line.startswith('commit'):
				commitName = line[7:]
				if commitName not in commits:
					continue
				commit = newCommit(tag)
				commit['date'] = commits[commitName]['date'] + 1
				commit['desc'] = 'TAG to ' + commitName
				commits[tag] = commit	

# get sorted by dates
commitsByDate = sorted(commits.values(), key = lambda commit : commit['date'])
commitsByDate.reverse()
count = 0
for commit in commitsByDate:
	commit['count'] = count
	count = count + 1

# filter out branches by count
for commit in commitsByDate:
	if commit['count'] >= numCommits:
		for branchName in branches:
			branch = branches[branchName]
			if commit['name'] in branch['commits']:
				branch['commits'].remove(commit['name'])
		del commits[commit['name']]
commitsByDate = commitsByDate[:numCommits]

# sort branch names
if sortBranchesByDate:
	branchNames = sorted(branches, key = lambda branchName : (commits[branches[branchName]['latestcommit']]['date'] if branches[branchName]['latestcommit'] in commits else 0))
else:
	branchNames = sorted(branches, key = lambda branchName : branches[branchName]['display'])

# print html
f = open('html/git-view-2.html', 'w')
print('''<html>
<style>
td { height: 24px; overflow: hidden; white-space: nowrap; }
td.branches { text-align: left; overflow: hidden; white-space: nowrap; }
td.branches div { width: 251px; margin-left: 5px; }
#cells td, #commits td { text-align: center; min-width: 48px; height: 24px; overflow: hidden; }
.white { background-color: white; }
.grey { background-color: #ddddff; }
.notmerged { background-color: #000000; color: #ffffff; }
.master { background-color: #ff0000; color: #ffffff; }
.staging { background-color: #3388ff; }
.production { background-color: #00aa00; }
</style><body>
''', file = f)

# info area
for i in range(0, len(commitsByDate)):
	commit = commitsByDate[i]
	print('<div id="info_' + commit['name'] + '" style="background-color: white; visibility: hidden; overflow: hidden; position: absolute; z-index: 3; left: 0; top: 0; width: 90%; height: 84px;" onmouseover="this.style.height=\'auto\'" onmouseout="this.style.height=\'84px\'">' + commit['name'] + '<br />' + datetime.datetime.fromtimestamp(commit['date']).strftime('%Y-%m-%d %H:%M:%S') + ' ' + commit['author'] + '<br />' + commit['desc'] + '</div>', file = f )

# print first row
print('<table id="commits" style="background-color: white; position: absolute; z-index: 2; table-layout: fixed; border: 0px solid black; left: 256px; top: 96px; height: 24px;" cellpadding=0 cellspacing=0><tr>', file = f)
for i in range(0, len(commitsByDate)):
	commit = commitsByDate[i]
	background = ''
	if commit['desc'].startswith('TAG'):
		commitName = commit['name']
		background = 'yellow';
	elif commit['desc'].startswith('Merge'):
		commitName = commit['name'][:5]
		background = 'orange';
	else:
		commitName = commit['name'][:5]
		background = 'white';
	print('''<td onmouseover="if(activeInfo != null) activeInfo.style.visibility = 'hidden'; activeInfo = document.getElementById('info_''' + commit['name'] + ''''); activeInfo.style.visibility = 'visible';" style="background: ''' + background + ''';">''' + commitName + '</td>', file = f)
print('</tr></table>', file = f)

# print first col
def printBranchLabel(branchName):
	global branches
	if branchName in branches:
		color = '#ffffff';
		text_color = '#000000'
		if branches[branchName]['level'] == 0:
			color = '#000000'
			text_color = '#ffffff'
		elif branches[branchName]['level'] == 1:
			color = '#ff0000'
			text_color = '#ffffff'
		elif branches[branchName]['level'] == 2:
			color = '#3388ff'
		elif branches[branchName]['level'] == 3:
			color = '#00aa00'
		if branches[branchName]['latestcommit'] in commits:
			print('<tr><td class="branches" style="background-color: ' + color + '; color: ' + text_color + ';"><div onclick="moveTo(' + str(commits[branches[branchName]['latestcommit']]['count']) + ');">' + branches[branchName]['display'] + '</div></td></tr>', file = f)
		else:
			print('<tr><td class="branches" style="background-color: ' + color + '; color: ' + text_color + ';"><div>' + branches[branchName]['display'] + '</div></td></tr>', file = f)

# print graph
print('<table id="cells" style="position: absolute; table-layout: fixed; border: 0px solid black; left: 256px; top: 120px;" cellpadding=0 cellspacing=0>', file = f)

evenRow = True
def printBranch(branch):
	global evenRow
	evenCol = True
	branch['level'] = 3
	commits_html = ''
	for i in range(0, len(commitsByDate)):
		commit = commitsByDate[i]
		className = ''
		text = ''
		if commit['name'] in branch['commits']:
			if 'origin/production' in branches and commit['name'] in branches['origin/production']['commits']:
				className = 'production'
				branch['level'] = min(branch['level'], 3)
			elif 'origin/staging' in branches and commit['name'] in branches['origin/staging']['commits']:
				className = 'staging'
				branch['level'] = min(branch['level'], 2)
			elif 'origin/master' in branches and commit['name'] in branches['origin/master']['commits']:
				className = 'master'
				branch['level'] = min(branch['level'], 1)
			else:
				className = 'notmerged'
				branch['level'] = min(branch['level'], 0)
		else:
			if evenCol or evenRow:
				className = 'grey'
			else:
				className = 'white'
		commits_html += '''<td class="''' + className + '''">''' + text + '''</td>\n'''
		evenCol = not evenCol
	print('<tr>' + commits_html + '</tr>', file = f)
	evenRow = not evenRow

if 'origin/production' in branches:
	printBranch(branches['origin/production'])
if 'production' in branches:
	printBranch(branches['production'])
if 'origin/staging' in branches:
	printBranch(branches['origin/staging'])
if 'staging' in branches:
	printBranch(branches['staging'])
if 'origin/master' in branches:
	printBranch(branches['origin/master'])
if 'master' in branches:
	printBranch(branches['master'])
for branchName in branchNames:
	if branchName in ['origin/production', 'production', 'origin/staging', 'staging', 'origin/master', 'master']:
		continue;
	printBranch(branches[branchName])

print('</table>', file = f)

print('<table id="branches" style="background-color: white; overflow: hidden; white-space: nowrap; position: absolute; z-index: 1; left: 0px; top: 120px; width: 256px;" cellpadding=0 cellspacing=0>', file = f)
printBranchLabel('origin/production')
printBranchLabel('production')
printBranchLabel('origin/staging')
printBranchLabel('staging')
printBranchLabel('origin/master')
printBranchLabel('master')
for branchName in branchNames:
	if branchName in ['origin/production', 'production', 'origin/staging', 'staging', 'origin/master', 'master']:
		continue;
	printBranchLabel(branchName)
print('</table>', file = f)

print('''
<script language="javascript">
var activeInfo = null;

var targetX = 0;
var sliding = false;
function update()
{
	if(sliding)
	{
		var offset = Math.floor((targetX - window.pageXOffset) / 2);
		if(Math.abs(offset) < 2)
		{
			offset = targetX - window.pageXOffset;
			sliding = false;
		}
		window.scrollTo(window.pageXOffset + offset, window.pageYOffset);
	}

	if(activeInfo != null)
	{
		activeInfo.style.top = window.pageYOffset + 'px';
		activeInfo.style.left = window.pageXOffset + 'px';
	}
	document.getElementById('commits').style.top = (window.scrollY + 96) + 'px';
	document.getElementById('branches').style.left = (window.pageXOffset + 256 - document.getElementById('branches').offsetWidth) + 'px';

	setTimeout('update()', 500)
}
function moveTo(count)
{
	sliding = true;
	targetX = count * 48;
}
update();
</script>
</body></html>
''', file = f)

