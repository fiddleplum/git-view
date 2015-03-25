#!/usr/bin/env python3.2

import subprocess
import os
import sys
import time
import cgi
import datetime

gitPath = '/usr/bin/git'

if len(sys.argv) < 2:
	print("Syntax: py git-view-2.py <path-to-git-repo> <maximum-number-commits-on-each-branch> <no-merge>")
	exit(0)

path = sys.argv[1]
if path[-1] != "/":
	path = path + "/"

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
		branches[branchName[8:]]['local'] = False
	else:
		branches[branchName] = newBranch(branchName)

# get commits
commits = {}

for branchName in branches:
	branch = branches[branchName]
	count = 0
	lastCommitName = ''
	if (len(sys.argv) >= 4) and (sys.argv[3] == 'no-merges'):
		mergeOption = '--no-merges '
	else:
		mergeOption = ''
	logLines = callGit('log --date=raw ' + mergeOption + (('-n ' + sys.argv[2] + ' ') if len(sys.argv) == 3 else '') + ('heads/' if branch['local'] else 'remotes/') + branch['name'] + ' --')
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
if len(sys.argv) >= 3:
	max_count = int(sys.argv[2])
	for commit in commitsByDate:
		if commit['count'] >= max_count:
			for branchName in branches:
				branch = branches[branchName]
				if commit['name'] in branch['commits']:
					branch['commits'].remove(commit['name'])
			del commits[commit['name']]
	commitsByDate = commitsByDate[:max_count]

# print html
f = open('html/git-view-2.html', 'w')
print('''<html>
<style>
td { height: 24px; }
td.branches { text-align: right; padding-right: 5px; white-space: nowrap; }
</style><body>
''', file = f)

# info area
print('<div id="info" style="background-color: white; visibility: hidden; position:absolute; z-index: 3; left: 0; top: 0; width: 90%; height: 84px;"></div>', file = f )

# print first row
print('<table id="commits" style="background-color: white; position: absolute; z-index: 2; table-layout: fixed; border: 0px solid black; left: 256px; top: 84px; height: 36px;" cellpadding=0 cellspacing=0><tr>', file = f)
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
	print('''<td onmouseout="document.getElementById('info').style.visibility = 'hidden';" onmouseover="document.getElementById('info').style.visibility = 'visible'; document.getElementById('info').innerHTML=\'''' + commit['name'] + '<br />' + datetime.datetime.fromtimestamp(commit['date']).strftime('%Y-%m-%d %H:%M:%S') + ' ' + commit['author'] + '<br />' + commit['desc'] + '''\';" style="background: ''' + background + ''';"><div style="text-align: center; width: 48px; ">''' + commitName + '</div></td>', file = f)
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
			print('<tr><td class="branches" style="background-color: ' + color + '; color: ' + text_color + ';"><div onclick="moveTo(' + str(commits[branches[branchName]['latestcommit']]['count']) + ');">' + branchName + '</div></td></tr>', file = f)
		else:
			print('<tr><td class="branches" style="background-color: ' + color + '; color: ' + text_color + ';"><div>' + branchName + '</div></td></tr>', file = f)

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
		text_color = '#000000'
		text = ''
		if commit['name'] in branch['commits']:
			if 'origin/production' in branches and commit['name'] in branches['origin/production']['commits']:
				color = '#00aa00'
				branch['level'] = min(branch['level'], 3)
			elif 'origin/staging' in branches and commit['name'] in branches['origin/staging']['commits']:
				color = '#3388ff'
				branch['level'] = min(branch['level'], 2)
			elif 'origin/master' in branches and commit['name'] in branches['origin/master']['commits']:
				color = '#ff0000'
				text_color = '#ffffff'
				branch['level'] = min(branch['level'], 1)
			else:
				color = '#000000'
				text_color = '#ffffff'
				branch['level'] = min(branch['level'], 0)
		else:
			if evenCol or evenRow:
				color = '#ddddff'
			else:
				color = '#ffffff'
		commits_html += '''<td style="align: center; background-color: ''' + color + '''; color: ''' + text_color + ''';" onmouseout="document.getElementById('info').style.visibility = 'hidden';" onmouseover="document.getElementById('info').style.visibility = 'visible'; document.getElementById('info').innerHTML=\'''' + commit['name'] + '<br />' + datetime.datetime.fromtimestamp(commit['date']).strftime('%Y-%m-%d %H:%M:%S') + '<br />' + commit['author'] + '<br />' + commit['desc'] + '''\';"><div style="text-align: center; width: 48px;">''' + text + '''</div></td>'''
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

print('<table id="branches" style="background-color: white; position: absolute; z-index: 1; left: 0px; top: 120px; width: 256px;" cellpadding=0 cellspacing=0>', file = f)
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
	document.getElementById('commits').style.top = (window.pageYOffset + 84) + 'px';
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

