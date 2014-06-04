#!/usr/bin/env python3.2

import subprocess
import os
import sys
import time
import cgi
import datetime

gitPath = '/usr/bin/git'

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
	return branch

# make sure we have all the infos
callGit('fetch -p')

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
	lastCommitName = ''
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
				commits[lastCommitName]['author'] = logLine[8:]
		else:
			if not skipCommit:
				if len(commits[lastCommitName]['desc']) > 0:
					commits[lastCommitName]['desc'] += '<br />'
				commits[lastCommitName]['desc'] += logLine.replace("&", r"&amp;").replace("<", r"&lt;").replace(">", r"&gt;").replace("\"", r"&quot;").replace("\'", r"\'")

# get sorted by dates
commitsByDate = sorted(commits.values(), key = lambda commit : commit['date'])
commitsByDate.reverse()
count = 0
for commit in commitsByDate:
	commit['count'] = count
	count = count + 1

# print html
f = open('html/git-view-2.html', 'w')
print('''<html>
<style>
td { height: 24px; }
td.branches { text-align: right; padding-right: 5px; }
</style><body>
''', file = f)

# info area
print('<div id="info" style="background-color: white; visibility: hidden; position:absolute; z-index: 3; left: 0; top: 0; height: 96px;"></div>', file = f )

# print first row
print('<table id="commits" style="background-color: white; position: absolute; z-index: 2; table-layout: fixed; border: 0px solid black; left: 256px; top: 96px;" cellpadding=0 cellspacing=0><tr>', file = f)
for i in range(0, len(commitsByDate)):
	commit = commitsByDate[i]
	print('''<td onmouseout="document.getElementById('info').style.visibility = 'hidden';" onmouseover="document.getElementById('info').style.visibility = 'visible'; document.getElementById('info').innerHTML=\'''' + commit['name'] + '<br />' + datetime.datetime.fromtimestamp(commit['date']).strftime('%Y-%m-%d %H:%M:%S') + '<br />' + commit['author'] + '<br />' + commit['desc'] + '''\';"><div style="text-align: center; width: 48px;">''' + commit['name'][:5] + '</div></td>', file = f)
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
		print('<tr><td class="branches" style="background-color: ' + color + '; color: ' + text_color + ';"><div onclick="moveTo(' + str(commits[branches[branchName]['latestcommit']]['count']) + ');">' + branchName + '</div></td></tr>', file = f)

# print graph
print('<table style="position: absolute; table-layout: fixed; border: 0px solid black; left: 256px; top: 120px;" cellpadding=0 cellspacing=0>', file = f)

evenRow = True
def printBranch(branch):
	global evenRow
	evenCol = True
	branch['level'] = 3
	commits_html = ''
	for i in range(0, len(commitsByDate)):
		commit = commitsByDate[i]
		color = ''
		if commit['name'] in branch['commits']:
			if commit['name'] in branches['origin/production']['commits']:
				color = '#00aa00'
				branch['level'] = min(branch['level'], 3)
			elif commit['name'] in branches['origin/staging']['commits']:
				color = '#3388ff'
				branch['level'] = min(branch['level'], 2)
			elif commit['name'] in branches['origin/master']['commits']:
				color = '#ff0000'
				branch['level'] = min(branch['level'], 1)
			else:
				color = '#000000'
				branch['level'] = min(branch['level'], 0)
		else:
			if evenCol or evenRow:
				color = '#ddddff'
			else:
				color = '#ffffff'
		commits_html += '<td style="align: center; background-color: ' + color + ';"><div style="text-align: center; width: 48px;"></div></td>'
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
for branchName in sorted(branches):
	branch = branches[branchName]
	if branchName in ['origin/production', 'production', 'origin/staging', 'staging', 'origin/master', 'master']:
		continue;
	printBranch(branch)

print('</table>', file = f)

print('<table id="branches" style="background-color: white; position: absolute; z-index: 1; left: 0px; top: 120px;" cellpadding=0 cellspacing=0>', file = f)
printBranchLabel('origin/production')
printBranchLabel('production')
printBranchLabel('origin/staging')
printBranchLabel('staging')
printBranchLabel('origin/master')
printBranchLabel('master')
for branchName in sorted(branches):
	if branchName in ['origin/production', 'production', 'origin/staging', 'staging', 'origin/master', 'master']:
		continue;
	printBranchLabel(branchName)
print('</table>', file = f)

print('''
<script language="javascript">
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

	document.getElementById('info').style.left = window.pageXOffset + 'px';
	document.getElementById('info').style.top = window.pageYOffset + 'px';
	document.getElementById('commits').style.top = (window.pageYOffset + 96) + 'px';
	document.getElementById('branches').style.left = (window.pageXOffset + 256 - document.getElementById('branches').offsetWidth) + 'px';

	setTimeout('update()', 33)
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

