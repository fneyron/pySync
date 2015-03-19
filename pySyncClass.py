#/usr/bin/env python

import re
import pysftp
import os
from ftplib import FTP
import ConfigParser
from argparse import ArgumentParser
import logging
from logging import handlers
import sys


class pySync:
    """ Server object with login, pass, key , ... """
    port = ''
    key = ''
    host = ''
    password = ''
    login = ''
    action = ''
    protocol = ''
    name = ''
    logger = ''

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def checkSFTPConnectInfo(self):
        if not self.password:
            connectInfo = {
                'host': self.host,
                'username': self.login,
                'private_key': self.key,
                'port': int(self.port)
                }
        else:
            connectInfo = {
                'host': self.host,
                'username': self.login,
                'password': self.password,
                'port': int(self.port)
                }
        return connectInfo

    def get(self, proto, src, dst):
        (srcPath, srcName) = self.splitDirName(src)
        regex = re.compile('(' + srcName + ')')
        if proto == 'sftp':
            self.checkCreateLocalDir(dst)
            with pysftp.Connection(**self.checkSFTPConnectInfo()) as sftp:
                files = [m.group(0) for l in sftp.listdir(srcPath)
                         for m in [regex.search(l)] if m]
                for f in files:
                    sftp.get(f, localpath=os.path.join(dst, f))

    def splitDirName(self, path):
        (directory, name) = path.rsplit('/', 1)
        directory = directory if directory else '/'
        return (directory, name)

    def countLocalFiles(self, pattern):
        (srcPath, srcName) = self.splitDirName(pattern)
        regex = re.compile('(' + srcName + ')')
	try:
		files = [m.group(0) for l in os.listdir(srcPath)
			 for m in [regex.search(l)] if m]
        	return len(files)
	except OSError as e:
		self.log('info', 'Missing directory: %s' % e)

    def put(self, proto, src, dst):
        (srcPath, srcName) = self.splitDirName(src)
        regex = re.compile('(' + srcName + ')')
        self.checkCreateLocalDir(srcPath)
        if proto == 'sftp':
            with pysftp.Connection(**self.checkSFTPConnectInfo()) as sftp:
                self.checkCreateSFTPDir(dst)
                files = [m.group(0) for l in os.listdir(srcPath)
                         for m in [regex.search(l)] if m]
                for f in files:
                    sftp.put(f, remotepath=os.path.join(dst, f))
        elif proto == 'ftp':
            self.ftp = FTP(self.host, self.login, self.password)
            self.checkCreateFTPDir(dst)
            files = [m.group(0) for l in os.listdir(srcPath)
                     for m in [regex.search(l)] if m]
            for f in files:
                self.ftp.storbinary("STOR " + os.path.join(dst, f),
                               open(os.path.join(srcPath, f), 'rb'))
        else:
            self.log('info',
                     'Protocol: %s doesn\'t exist' % proto, self.name)
    def countRemoteFiles(self, pattern, proto):
        if proto == 'ftp':
		(dstPath, dstName) = self.splitDirName(pattern)
		regex = re.compile('(' + dstName + ')')
		try:
			files = [m.group(0) for l in self.ftp.nlst(dstPath)
				 for m in [regex.search(l)] if m]
			return len(files)
		except OSError as e:
			self.log('info', 'Missing directory: %s' % e)
 
    def checkCreateLocalDir(self, path):
        if not (os.path.isdir(path)):
            return os.makedirs(path)

    def log(self, level, msg):
        logger = logging.getLogger(self.logger)
        getattr(logger, level)(msg, extra={'server': self.name})

    def checkCreateFTPDir(self, path):
            tree = ''
            # making dir tree
            for directory in path.split('/'):
                if directory:
                    if directory not in self.ftp.nlst(tree):
			#print "directory not exist on ftp"
                        self.ftp.mkd(os.path.join(tree, directory))
                    tree = os.path.join(tree, directory)
