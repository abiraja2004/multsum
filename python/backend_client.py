#!/usr/bin/python
# -*- coding: utf-8 -*-

import re, traceback, time, select, os
from nltk.stem.porter import PorterStemmer
from multiprocessing.connection import Client
from subprocess import call

from backend_worker import BACKEND_ADDRESS, BACKEND_CONNECTION_FAMILY, BACKEND_PASSWORD

USE_BACKEND = True
RECV_TIMEOUT = 2000
RETRIES_BEFORE_QUITTING = 10000

conn = None
stemmer = None

##################################################################################
######### FUNCTIONS TO BE USED OUTSIDE OF THIS FILE ##############################
##################################################################################

def backend_check(recv_timeout=RECV_TIMEOUT):
  global conn
  try:
    if not conn:
      backend_open()
    conn.send({'command': 'PING'})
    print( 'Awaiting reply from backend for PING')
    ready = select.select([conn], [], [], recv_timeout)
    if ready[0]:
      response = conn.recv()
    else:
      return False
    print( 'Got response.')
    if response['status'] == 'OK' and response['value'] == 'PONG':
      conn.send({'command': 'CLOSE'})
      conn.close()
      conn = None
      return True
    else:
      print( 'Response was not OK.')
      conn.send({'command': 'CLOSE'})
      conn.close()
      conn = None
      return False
  except:
    print('Checking backend failed!')
    return False

def backend_is_initializing():
  global conn
  try:
    if not conn:
      backend_open()
    conn.send({'command': 'PING'})
    print('Awaiting reply from backend for PING')
    ready = select.select([conn], [], [], RECV_TIMEOUT)
    if ready[0]:
      response = conn.recv()
    else:
      return False
    print('Got response.')
    print response
    if response['status'] == 'FAIL' and response['value'] == 'Backend is initializing.':
      conn.send({'command': 'CLOSE'})
      conn.close()
      conn = None
      return True
    else:
      conn.send({'command': 'CLOSE'})
      conn.close()
      conn = None
      return False
  except:
    print('Checking backend failed!')
    return False

def backend_open():
  global conn
  print( 'backend_open()')
  if not conn:
    print( 'Connecting to backend.')
    conn = Client(BACKEND_ADDRESS, family=BACKEND_CONNECTION_FAMILY, authkey=BACKEND_PASSWORD)
    #conn.settimeout(100)

def backend_close():
  global conn
  print( 'backend_close()')
  if conn:
    try:
      conn.send({'command': 'CLOSE'})
      conn.close()
    except Exception, e:
      pass
    conn = None

def backend_carry_out(request):
  global conn
  reconnect_count = 0
  while True:
    try:
      if not conn:
        print( 'No connection')
        backend_open()
        print( 'Connection established!')
      else:
        print( 'There is a connection')
        
      conn.send(request)
      #print( 'Awaiting reply from backend for (\'%s\')'%(str(request)))
      ready = select.select([conn], [], [], RECV_TIMEOUT)
      #print( 'Connection is ready. (\'%s\')'%(str(request)))
      if ready[0]:
        #print( 'Running recv() (\'%s\')'%(str(request)))
        response = conn.recv()
        #print( 'recv() returned! (\'%s\')'%(str(request)))
      else:
        print( 'select timeout. (\'%s\')'%(str(request)))
        raise Exception('Timeout!')
      print( 'Got response.')
      if response['status'] == 'OK':
        return response['value']
      else:
        print( 'FAIL! Value: '+response['value'])
        return None
    except Exception, e:
      print( str(e))
      #number_iterations_with_constant_time = 5
      #waiting_time = max(1,reconnect_count-number_iterations_with_constant_time)*30
      waiting_time = 30 
      print( 'Retrying... Waiting %d seconds.'%(waiting_time))
      time.sleep(waiting_time)
      reconnect_count = reconnect_count+1
      conn = None
      if reconnect_count > RETRIES_BEFORE_QUITTING:
        print( str(traceback.format_exc()))
        print( str(e))
        raise
        return None
      #if reconnect_count >= 3:


def backend_get_representation(term):
  rep = backend_carry_out({'command': 'wordmodel', 'term': term})
  return rep

def backend_exit():
  try:
    if not conn:
      print( 'No connection')
      backend_open()
      print( 'Connection established!')
    else:
      print( 'There is a connection')

    conn.send({'command': 'EXIT_NOW'})
    conn.close()
    conn = None
    #backend_carry_out({'command': 'EXIT_NOW'})
  except Exception,e:
    print('Connection error. Check for ghost processes.')
