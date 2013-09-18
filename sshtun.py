import os
import re
import sys
import subprocess

"""

Create simple ssh tunnel with ssh client programm.

TODO: Run with out full path to ssh

"""
class SSHTun:
    tunnel_command_template = "/usr/bin/ssh -l %s -i %s -f -n -N -q -o 'ExitOnForwardFailure yes' -o 'PasswordAuthentication no' -L 127.0.0.1:%d:localhost:%d %s"
    tunnel_command = None
    lport = None
    rport = None
    rhost = None
    user = None
    keyfile = None
    pid = None
    min_pid = 300   # From kernel/pid.c see RESERVED_PIDS
    max_pid = 0

    #XXX: Add params check here
    def __init__(self, user, keyfile, lport, rport, rhost):
        self.user = user
        self.keyfile = keyfile
        self.lport = lport
        self.rport = rport
        self.rhost = rhost

        self.tunnel_command = self.tunnel_command_template % (self.user, self.keyfile, self.lport, self.rport, self.rhost)

    def start(self):

        t = subprocess.Popen(self.tunnel_command, stderr=subprocess.PIPE, shell=True, close_fds=True, stdout=subprocess.PIPE)
        t.wait()

        if t.returncode == 0:
            self.pid = self.__find_pid(t.pid)
        else:
            ## Kill previos tunnel
            #os.kill(self.__find_pid(), 1)
            #self.pid = self.start()

            # Try to find existing tunnel
            self.pid = self.__find_pid()

            if self.pid == None:
                raise Exception("Can't create new ssh tunnel")

        return self.pid

    """

    subprocess.Popen creates sheel and then ssh process.
    Popen object returns pid of that shell, not pid of ssh
    But ssh's pid can be pedicted as shell pid plus some small N number
    It works fine if new ssh tunnel was started without errors (Popen.returncode is zero)

    But ssh tunnel can ramain from previos run,
    and in this case all process should be checked to match ssh tunnel with same options

    XXX: Should i kill previos tunnel and create new one?

    """
    def __find_pid(self, pid_start_from = None):

        if pid_start_from == None:
            pid_start_from = self.min_pid

        # Find pid range on this system
        try:
            with open('/proc/sys/kernel/pid_max', 'r') as f:
                self.max_pid = int(f.readline())

        except Exception as e:
            raise Exception("Can't get pid_max from proc: %s" % e.args)

        # get all processes from /proc
        proc_arr = []
        for dir in os.listdir('/proc'):
            if re.search('^[0-9]+$', dir):
                proc_arr.append(int(dir))

        # search for process
        pid_to_check = pid_start_from + 1

        # search for process from predicted pid
        for i in range(self.min_pid, self.max_pid):

            if pid_to_check >= self.max_pid:
                pid_to_check = self.min_pid

            if pid_to_check in proc_arr:

                try:
                    with open('/proc/%d/cmdline' % pid_to_check, 'r') as f:
                        cmdline = f.readline().replace('\x00', ' ').rstrip('\n').strip()

                    if cmdline == self.tunnel_command.replace("'",''):
                        return pid_to_check
                except:
                    pass

            pid_to_check += 1

        return None

    def is_alive(self):
        try:
            os.kill(self.pid, 0)
        except:
            return None

        return True

    def stop(self):
        if not self.pid:
            self.pid = self.__find_pid()

        if self.pid:
           os.kill(self.pid, 15)

    def restart(self):
        self.stop()
        return self.start()

    def get_pid(self):
        return self.pid
