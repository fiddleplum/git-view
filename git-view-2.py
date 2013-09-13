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
commitsByDate = {}
for commitName in commits:
	commitsByDate[commits[commitName]['date']] = commitName

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
print('<table id="commits" style="background-color: white; position: absolute; z-index: 2; table-layout: fixed; border: 0px solid black; left: 192px; top: 96px;" cellpadding=0 cellspacing=0><tr>', file = f)
for date in sorted(commitsByDate.keys(), reverse=True):
	commit = commits[commitsByDate[date]]
	print('''<td onmouseout="document.getElementById('info').style.visibility = 'hidden';" onmouseover="document.getElementById('info').style.visibility = 'visible'; document.getElementById('info').innerHTML=\'''' + commit['name'] + '<br />' + datetime.datetime.fromtimestamp(commit['date']).strftime('%Y-%m-%d %H:%M:%S') + '<br />' + commit['author'] + '<br />' + commit['desc'] + '''\';"><div style="text-align: center; width: 32px;">''' + commit['name'][:4] + '</div></td>', file = f)
print('</tr></table>', file = f)

# print first col
print('<table id="branches" style="background-color: white; position: absolute; z-index: 1; left: 0; top: 120px;" cellpadding=0 cellspacing=0>', file = f)
print('<tr><td class="branches">origin/production</td></tr>', file = f)
print('<tr><td class="branches">production</td></tr>', file = f)
print('<tr><td class="branches">origin/staging</td></tr>', file = f)
print('<tr><td class="branches">staging</td></tr>', file = f)
print('<tr><td class="branches">origin/master</td></tr>', file = f)
print('<tr><td class="branches">master</td></tr>', file = f)
for branchName in branches:
	if branchName in ['origin/production', 'production', 'origin/staging', 'staging', 'origin/master', 'master']:
		continue;
	print('<tr><td class="branches">' + branchName + '</td></tr>', file = f)
print('</table>', file = f)

# print graph
print('<table style="position: absolute; table-layout: fixed; border: 0px solid black; left: 192px; top: 120px;" cellpadding=0 cellspacing=0>', file = f)

evenRow = True
def printBranch(branch):
	global evenRow
	evenCol = True
	print('<tr>', file = f)
	for date in sorted(commitsByDate.keys(), reverse=True):
		commit = commits[commitsByDate[date]]
		color = ''
		if commit['name'] in branch['commits']:
			color = '#000000'
		else:
			if evenCol:
				if evenRow:
					color = '#ffa577'
				else:
					color = '#ff945e'
			else:
				if evenRow:
					color = '#80a9ff'
				else:
					color = '#4d87ff'
		print('<td style="align: center; background-color: ' + color + ';"><div style="text-align: center; width: 32px;"></div></td>', file = f)
		evenCol = not evenCol
	print('</tr>', file = f)
	evenRow = not evenRow

printBranch(branches['origin/production'])
printBranch(branches['production'])
printBranch(branches['origin/staging'])
printBranch(branches['staging'])
printBranch(branches['origin/master'])
printBranch(branches['master'])
for branchName in branches:
	branch = branches[branchName]
	if branchName in ['origin/production', 'production', 'origin/staging', 'staging', 'origin/master', 'master']:
		continue;
	printBranch(branch)

print('</table>', file = f)
print('''
<script language="javascript">
function update()
{
	document.getElementById('info').style.left = window.pageXOffset + 'px';
	document.getElementById('info').style.top = window.pageYOffset + 'px';
	document.getElementById('commits').style.top = (window.pageYOffset + 96) + 'px';
	document.getElementById('branches').style.left = window.pageXOffset + 'px';
	setTimeout('update()')
}
update();
</script>
</body></html>
''', file = f)

