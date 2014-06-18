#!/usr/bin/env python
# Copyright (c) 2012 maidsafe.net limited
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions and the following disclaimer in the documentation
#     and/or other materials provided with the distribution.
#     * Neither the name of the maidsafe.net limited nor the names of its
#     contributors may be used to endorse or promote products derived from this
#     software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
# TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import sys
import os
import subprocess
import signal
from subprocess import PIPE, STDOUT
from multiprocessing import Process, Pool
import multiprocessing
import utils
import re
import psutil
import time
import datetime
import random
import shutil
import vault_killer

processes = {}
stop_churn = 'd'


def SetupBootstraps(num, user_id):
  print("Setting up keys ... ")
  prog = utils.GetProg('vault_key_helper')
  proc = subprocess.Popen([prog, '-c', '-b', '-n', str(num + 6)],
                          shell = False, stdout = PIPE, stderr = None)
  print("Started bootstrap with PID " + str(proc.pid))
  i = 0
  line_limit = 50
  t_start = datetime.datetime.now()
  time_delta = datetime.datetime.now() - t_start
  timeout = 300000
  while i < line_limit and time_delta < datetime.timedelta(seconds=timeout):
    line = str(proc.stdout.readline(), encoding='utf8')
    print(line)
    if line.find("Endpoints") != -1:
      data = re.split(r':', line)
      ep = data[2].split()
      processes[2] = SetUpNextNode(data[1] + ':' + ep[0], 2)
      time.sleep(1)
      processes[3] = work(3)
      if processes[2] and processes[3]:
        print("Wait 5 secs for bootstrap")
        time.sleep(5)
        break
      else:
        proc.kill()
        return False
    i = i + 1
    time_delta = datetime.datetime.now() - t_start
  if i == line_limit or time_delta >= datetime.timedelta(seconds=timeout):
    proc.kill()
    return False
  proc.kill()
  print("Wait 10 secs for bootstrap nodes disappear from routingtable")
  time.sleep(10)
  RunNetwork(num)
  print("Wait 5 secs for network")
  time.sleep(5)
  return True

def SaveKeys(peer, keys_path, client_index, num_of_keys):
  result = -1
  prog = utils.GetProg('vault_key_helper')
  proc = subprocess.Popen([prog, '-ls', '-k', str(client_index),
                          '--keys_path', keys_path, '--peer=' + peer + ':5483'],
                          shell = False, stdout = PIPE, stderr = None)
  if utils.TimeOut(utils.LookingFor, (proc, 'PublicPmidKey stored and verified', 50, num_of_keys,),
                   timeout_duration=5*num_of_keys, default=False):
    print("keys successfully stored to network")
    result = 0
  else:
    print("failure in storing keys to network")
  proc.kill
  vault_killer.KillVaultKeyHelper()
  return result

def StoreChunk(key_index, chunk_index):
  prog = utils.GetProg('vault_key_helper')
  subprocess.call([prog, '-l1', '-k', str(key_index),
                  '--chunk_index=' + str(chunk_index)],
                  shell = False, stdout = None, stderr = None)

def FetchChunk(key_index, chunk_index):
  prog = utils.GetProg('vault_key_helper')
  subprocess.call([prog, '-l2', '-k', str(key_index),
                  '--chunk_index=' + str(chunk_index)],
                  shell = False, stdout = None, stderr = None)

def DeleteChunk(key_index, chunk_index):
  prog = utils.GetProg('vault_key_helper')
  subprocess.call([prog, '-l3', '-k', str(key_index),
                  '--chunk_index=' + str(chunk_index)],
                  shell = False, stdout = None, stderr = None)

def TestStore(num, index):
  prog = utils.GetProg('vault_key_helper')
  proc = subprocess.Popen([prog, '-lt', '-k', str(index),
                          '--chunk_set_count=' + str(num)],
                          shell = False, stdout = PIPE, stderr = None)
  if utils.TimeOut(utils.LookingFor, (proc, 'Stored chunk', 50, num,),
                   timeout_duration=60*num, default=False):
    print("test with store succeeded")
  else:
    print("test with store failed")
  proc.kill
  vault_killer.KillVaultKeyHelper()

def TestStoreWithDelete(num, index):
  prog = utils.GetProg('vault_key_helper')
  proc = subprocess.Popen([prog, '-lw', '-k', str(index),
                          '--chunk_set_count=' + str(num)],
                          shell = False, stdout = PIPE, stderr = None)
  if utils.TimeOut(utils.LookingFor, (proc, 'Delete chunk', 100, num,),
                   timeout_duration=60*num, default=False):
    print("test with delete succeeded")
  else:
    print("test with delete failed")
  proc.kill
  vault_killer.KillVaultKeyHelper()

def TestProlonged(key_index, chunk_index):
  StoreChunk(key_index, chunk_index)
  time.sleep(10)
  FetchChunk(key_index, chunk_index)
  time.sleep(10)
  DeleteChunk(key_index, chunk_index)
  time.sleep(10)
  FetchChunk(key_index, chunk_index)

def SetUpKeys(num):
  print("Setting up keys ... ")
  prog = utils.GetProg('vault_key_helper')
  CreateChunkStores(num)
  return subprocess.call([prog, '-c', '-n', str(num) ],
                         shell = False, stdout = None, stderr = None)

def CreateChunkStores(num):
  RemoveChunkStores(num)
  for dir_num in range(int(num)):
    directory = os.path.join(os.curdir, '.cs' + str(dir_num))
    if not os.path.exists(directory):
      os.makedirs(directory)

def RemoveChunkStores(num):
  for dir_num in range(int(num)):
    directory = os.path.join(os.curdir, '.cs' + str(dir_num))
    if os.path.exists(directory):
          shutil.rmtree(directory)

def preexec_function():
    # Ignore the SIGINT signal by setting the handler to the standard
    # signal handler SIG_IGN.
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def work(number):
  prog = utils.GetProg('vault')
  log_file = open('vault_' + str(number) + '.txt', 'w')
  return subprocess.Popen([prog, '--log_no_async', 'true',
                          '--log_vault', 'V', '--log_nfs', 'V', '--log_*', 'E',
                          '--disable_ctrl_c=true',
                          '--identity_index=' + str(number),
                          '--chunk_path=.cs' + str(number)],
                          shell = False, stdout = log_file, stderr = log_file)


def RunNetwork(number_of_vaults):
  for vault in range(4, number_of_vaults):
    processes[vault]= work(vault)
    print("Vault " + str(vault) + " is starting up ... ")
    time.sleep(1)

def SignalHandler(signal, frame):
  print("Exiting churn ")
  global stop_churn
  stop_churn = 'q'

signal.signal(signal.SIGINT, SignalHandler)

def Churn(percent_per_minute):
  num_vaults = len(processes)
  churn_interval = (60 * 100) / (num_vaults * percent_per_minute)
  print("Running churn test at a rate of every " + str(churn_interval) + " seconds one node drop and another join")
  print("press Ctrl-C to stop")
  stopped = []
  for i in range(num_vaults + 2, num_vaults + 5):
    stopped.append(i)
  global stop_churn
  while  stop_churn != 'q':
    time.sleep(churn_interval)
    if stop_churn != 'q':
      selected_index = random.choice(processes.keys())
      print("node with index : " + str(selected_index) + " is going to stop")
      KillProc(selected_index)
    
      if len(stopped) > 0:
        selected_join = stopped.pop(random.randint(0, len(stopped) - 1))
        print("node with index : " + str(selected_join) + " is going to join")
        processes[selected_join] = work(selected_join, utils.GetIp(), None)

      stopped.append(selected_index)
  stop_churn = 'g'

def KillProc(selected_index):
  selected_stop = processes.pop(selected_index)
  selected_stop.kill()

def SetUpNextNode(endpoint, index):
  prog = utils.GetProg('vault')
  log_file = open('vault_' + str(index) + '.txt', 'w')
  return subprocess.Popen([prog, '--log_no_async', 'true',
                          '--log_vault', 'V', '--log_nfs', 'V', '--log_*', 'E',
                          '--peer=' + endpoint.lstrip(),
                          '--disable_ctrl_c=true',
                          '--identity_index=' + str(index),
                          '--chunk_path=.cs' + str(index)],
                          shell = False, stdout = log_file, stderr = log_file)


def SanityCheck(num, user_id):
  pid = SetupBootstraps(num, user_id)
  if pid == False:
    print("Vault Sanity Check failed")
    return False
  else:
    print("Vault Sanity Check Passed")
    return True

def PrintVaultMenu():
  utils.ClearScreen()
  procs = utils.CountProcs('vault')
  print(str(procs) + " Vaults running on this machine")
  print ("================================")
  print ("MaidSafe Quality Assurance Suite | Vault Actions")
  print ("================================")
  print ("1: Bootstrap and set up vaults")
  if procs == 0:
    print ("2: Set up vaults only (bootstrap elsewhere)")
  else:
    print ("3: Run simple test - store then fetch")
    print ("4: Run simple test with delete")
    print ("5: Run prolonged test - store fetch then delete")
    print ("6: Store keys to network")
    print ("7: Random churn on this machine")
    print ("8: Kill all vaults on this machine")
  return procs

def RunBootstrapAndVaultSetup():
  num = 0
  while 12 > num:
    number = input("Please input number of vaults to run (minimum and default 12): ")
    if number == "":
      num = 12
    elif not number.isdigit():
      continue
    else:
      num = int(number)
  RemoveChunkStores(num)
  SanityCheck(num + 2, None)
  # SaveKeys(utils.GetIp())

def ValidOption(procs, option):
  if not option.isdigit():

    return False
  if option == "2" and procs != 0:
    return False
  if int(option) > 2 and procs == 0:
    return False
  return True

def GetPositiveNumber(message):
  number = 0
  while number < 1:
    number = input(message)
    number = int(number)
  return number

def StartVaultsWithGivenBootstrap():
  number = GetPositiveNumber("Please input number of vaults to run: ")
  ip = input("Please input ip address of bootstrap machine: ")
  prog = utils.GetProg('vault_key_helper')
  print(prog)
  CreateChunkStores(number)
  subprocess.call([prog, '-c', '-n', str(int(number) + 3)])
  keys_path = input("Please input the absolute/relative path to the keys_file: ")
  index = GetPositiveNumber("Please input the key_index to be used as client: ")
  num_keys = GetPositiveNumber("Please input how many keys in the keys_file: ")
  if SaveKeys(utils.GetIp(), keys_path, index, num_keys) == 0:
    RunNetwork(int(number) + 3, ip, None)
  else:
    input("Could not store keys, giving up! (press any key)")

def VaultMenu():
  option = 'a'
  utils.ResetScreen()
  while(option != 'm'):
    procs = PrintVaultMenu()
    option = input("Please select an option (m for main QA menu): ").lower()
    if not ValidOption(procs, option):
      continue
    if option == "1":
      RunBootstrapAndVaultSetup()
    elif (option == "2"):
      StartVaultsWithGivenBootstrap()
    elif (option == "3"):
      number = GetPositiveNumber("Please input number of chunks in test: ")
      index = GetPositiveNumber("Please input the key_index to be used as client: ")
      TestStore(number, index)
    elif (option == "4"):
      number = GetPositiveNumber("Please input number of rounds in test: ")
      index = GetPositiveNumber("Please input the key_index to be used as client: ")
      TestStoreWithDelete(number, index)
    elif (option == "5"):
      key_index = GetPositiveNumber("Please input the key_index to be used as client: ")
      chunk_index = GetPositiveNumber("Please input the chunk_index to be used as data: ")
      TestProlonged(key_index, chunk_index)
    elif (option == "6"):
      keys_path = input("Please input the absolute/relative path to the keys_file: ")
      index = GetPositiveNumber("Please input the key_index to be used as client: ")
      num_keys = GetPositiveNumber("Please input how many keys in the keys_file: ")
      SaveKeys(utils.GetIp(), keys_path, index, num_keys)
    elif (option == "7"):
      churn_rate = GetPositiveNumber("Please input rate (%% churn per minute): ")
      Churn(churn_rate)
    elif (option == "8"):
      vault_killer.KillLifeStuff()
      processes.clear()

#  utils.ClearScreen()

def main():
  print("This is the suite of QA anaysis info for vaults")
  VaultMenu()
if __name__ == "__main__":
  sys.exit(main())

