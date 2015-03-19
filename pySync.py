#!/usr/bin/env python

import shutil
import pySyncClass
import logging
from argparse import ArgumentParser
import ConfigParser
import os
import sys
import glob
from datetime import datetime, timedelta
from logging import handlers


def dateDefine(myDate, utc, *args):
    timeLaps = ['hours', 'days', 'day', 'hour']
    date = myDate.split()
    if (len(date) > 1 and date[1] in timeLaps
            and float(date[0]) and date[2] == 'ago'):
        if date[1] in ['hours', 'hour']:
            date = (datetime.utcnow() - timedelta(hours=int(date[0])))
        elif date[1] in ['days', 'day']:
            date = (datetime.utcnow() - timedelta(days=int(date[0])))
        return date

def rotatingLogFiles(rotate, path):
    shutil.rmtree(path)


def main(argv):
    # Default parameters
    defaultConfigFile = 'myServers.cfg'
    defaultLogLevel = logging.INFO
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s \
- %(server)s - %(message)s'
    logLevelTab = {'info': logging.INFO,
                   'debug': logging.DEBUG,
                   'error': logging.ERROR}
    utc = True
    when = '1 hour ago'
    # Get command parameters argv
    parser = ArgumentParser()
    parser.add_argument(
        '-c',
        '--config-file',
        help='Define configuration file to use',
        dest='config')
    parser.add_argument(
        '-d',
        '--date',
        default='1 hour ago',
        dest='when',
        help='Define a date to work with, it can be \'02/02/2015\' \
            or \'1 hour ago\' [default=%(default)s]')
    parser.add_argument(
        '-u',
        '--utc',
        action="store_true",
	dest='utc',
        help='Use UTC time')
    parser.add_argument(
        '-t',
        '--time',
        dest='time',
        help='Define a hour to work with (ie: 02h or 17h)')
    parser.add_argument(
        '-r',
        '--rotate',
        dest='rotate',
        default=7,
        help='Define how many days logs are kept \
        [default: logs are kept for %(default)s days]'
        )
    args = parser.parse_args(argv[1:])
    config = ConfigParser.ConfigParser()
    if not args.config:
	configFile = defaultConfigFile
    else:
	configFile = args.config
    if os.path.isfile(configFile):
        config.read(configFile)
    else:
        print('No config file present for reading')
        sys.exit(1)
    # Define log handler
    try:
        loggerName = "pysync"
        logFile = open(os.path.join(config.get('default', 'log_path'),
                               '%s.log' % loggerName), 'a')
	logger = logging.getLogger(loggerName)
        if config.get('default', 'log_level') in logLevelTab:
            logger.setLevel(logLevelTab[config.get('default', 'log_level')])
        else:
            logger.setLevel(logLevelTab[defaultLogLevel])
        ch = logging.StreamHandler()
        fh = handlers.TimedRotatingFileHandler(logFile.name,
                                               when='w0',
                                               interval=1,
                                               backupCount=4)
        formatter = logging.Formatter(LOG_FORMAT)
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)
        logger.addHandler(ch)
        logger.addHandler(fh)
    except ConfigParser.NoOptionError as e:
        print('Missing option: %s' % e)
        sys.exit(1)
    #Parsing configuration
    if args.utc:
        utc = args.utc
    if args.when:
        when = args.when
    for serverName in [e for e in config.sections()
                       if e != "default" and
                       config.get(e, 'active') == 'yes']:
	try:
	    config.get(serverName,'key')
	    loginMode = 'key'
	except ConfigParser.NoOptionError:
	    loginMode = 'password'
	    pass
        try:
	    params = {
		    'host': config.get(serverName, 'host'),
		    'port': config.get(serverName, 'port'),
		    'login': config.get(serverName, 'login'),
		    'logger': loggerName,
		    'name': serverName,
		    loginMode: config.get(serverName, loginMode)}
            server = pySyncClass.pySync(**params)
            src = config.get(serverName, 'source_directory')
            dst = config.get(serverName, 'destination_directory')
            action = config.get(serverName, 'action')
        except ConfigParser.NoOptionError as e:
            print('Missing option: %s' % e)
            sys.exit(1)
        if args.when and args.time:
            myDate = '%s-%s' % (args.when, args.time.replace('h', ''))
            date = datetime.strptime(myDate, '%Y/%m/%d-%H')
        elif dateDefine(when, utc):
            date = dateDefine(when, utc)
        else:
            server.log('error', 'Problem with date: %s' % args.when)
        logName = "logs-%s.*\.log\.gz" % date.strftime('%Y_%m_%d-%H')
        if action == 'download':
            dstPath = os.path.join(dst,
                                     date.strftime('%Y_%m_%d'))
            server.log('info',
                       'Retrieving logs matching: %s under: %s' %
                       (os.path.join(src, logName), dst))
            server.get(config.get(serverName, 'proto'),
                       os.path.join(src,
                                    logName),
                       dstPath)
            nLogFiles = server.countLocalFiles(os.path.join(dstPath, logName))
            if nLogFiles != 60 and not (args.time and args.when):
                server.log('error',
                           'Problem retrieving logs, %s logs downloaded' %
                           nLogFiles)
		os.system('./mail.py -s ' + serverName + ' -m "Problem retrieving logs, ' + str(nLogFiles) + '  logs downloaded"')
            else:
                server.log('info',
                           'Successfully pushing logs, %s logs uploaded' %
                           nLogFiles)
		try:
		    date = dateDefine(config.get(serverName, 'rotating_logs') +
				      ' days ago', utc)
		    shutil.rmtree(os.path.join(dst,
				  date.strftime('%Y_%m_%d')))
		except OSError as e:
		    server.log('debug', 'Removing old folder: %s' % e)
		    pass
        elif action == 'upload':
            srcPath = os.path.join(src,
                                     date.strftime('%Y_%m_%d'))
	    dstPath = os.path.join(dst, date.strftime('%Y_%m_%d'))
            server.log('info',
                       'Pushing logs matching: %s under: %s' %
                       (os.path.join(srcPath, logName), dstPath))
            server.put(config.get(serverName, 'proto'),
                       os.path.join(srcPath,
                                    logName),
                       os.path.join(dstPath))
	    nLogFiles = server.countRemoteFiles(os.path.join(dstPath, logName), config.get(serverName, 'proto'))
            if nLogFiles != 60 and not args.time:
                server.log('error',
                           'Problem retrieving logs, %s logs downloaded' %
                           nLogFiles)
		os.system('./mail.py -s ' + serverName + ' -m "Problem pushing logs, ' + str(nLogFiles) + '  logs uploaded"')
            else:
                server.log('info',
                           'Successfully pushing logs, %s logs uploaded' %
                           nLogFiles)

if __name__ == "__main__":
    main(sys.argv)
