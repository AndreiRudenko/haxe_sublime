# -*- coding: utf-8 -*-

import sys, os, subprocess, re, shlex
from socket import socket as py_socket

from subprocess import Popen, PIPE

import sublime, sublime_plugin

#plugin location
plugin_file = __file__
plugin_filepath = os.path.realpath(plugin_file)
plugin_path = os.path.dirname(plugin_filepath)

import Default
stexec = getattr( Default , "exec" )
ExecCommand = stexec.ExecCommand
AsyncProcess = stexec.AsyncProcess

try:
  STARTUP_INFO = subprocess.STARTUPINFO()
  STARTUP_INFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
  STARTUP_INFO.wShowWindow = subprocess.SW_HIDE
except (AttributeError):
    STARTUP_INFO = None

print("hello haxe_completion")


_haxe_completion_ = None

def plugin_unloaded():
    if _haxe_completion_:
        _haxe_completion_.shutdown()

class HaxeCompletion( sublime_plugin.EventListener ):

    def __init__(self):
        HaxeCompletion.current = self
        global _haxe_completion_
        _haxe_completion_ = self

        self.process = None
        self.haxe_path = "haxe"
        self.port = 6110

        print("[haxe_completion] __init__")

    def init(self, forced=False):
        if not forced:
            if self.process is not None:
                return;

        print("[haxe_completion] init")

        settings = sublime.load_settings('haxe_completion.sublime-settings')

        #kill any existing server
        self.shutdown(True)

        #defaults
        self.haxe_path = "haxe"
        self.port = 6110

        if settings.has("server_port") is True:
            self.port = settings.get("server_port")
            print("[haxe_completion] load custom port as {}".format(self.port))
        if settings.has("haxe_path") is True:
            self.haxe_path = settings.get("haxe_path")
            print("[haxe_completion] load custom haxe path as {}".format(self.haxe_path))

        print("[haxe_completion] trying to start cache server `" + self.haxe_path + "` port:" + str(self.port))

        #this only starts the completion cache host from haxe,
        #then each request is faster, in get()

        try:
            self.process = run_process_bg([self.haxe_path, "--wait", str(self.port)])
            print("[haxe_completion] started with `" + self.haxe_path + "` port:" + str(self.port))
            #Popen( [ self.haxe_path, "-v", "--wait", str(self.port) ], env = os.environ.copy(), startupinfo=STARTUP_INFO)

        except(OSError, ValueError) as e:
            reason = u'[haxe_completion] error starting server and connecting to it: \n%s' % e
            print(reason)
            return None

    def complete(self, cwd='', fname='', offset=0, mode='', hxml=[]):
        print("[haxe_completion] complete")

        self.init()
        view = sublime.active_window().active_view()

        haxe_cmd = [
            self.haxe_path,
            "--connect", "127.0.0.1:" + str(self.port),
            "--no-output",
            "--cwd", cwd,
            "--display", fname + "@" + str(offset) + mode,
            "-D", "display-details",
            "-D", "use_rtti_doc",
        ]

        # print("[haxe_completion] haxe complete args " + str(haxe_cmd+hxml))

        _proc, _result_buffer = run_process( haxe_cmd+hxml )
        _result = ""

        if _result_buffer:
            _result = _result_buffer.decode('utf-8')
            if _result:
                _result = _result.strip()

        if _proc:
            try:
                _proc.kill();
                _proc.wait();
            except:
                pass

        return _result

    def complete_stdin(self, cwd='', fname='', fdata='', offset=0, mode='', hxml=[]):
        # print("[haxe_completion] complete stdin")

        self.init()
        args = "--cwd " + cwd + "\n" + "--display " + fname + "@" + str(offset) + mode + "\n" + "-D display-stdin" + "\n" + "\n".join(hxml)
       
        socket = py_socket()
        socket.connect(('localhost', self.port))
        socket.send(bytes(args, 'utf-8'));
        socket.send(b"\x01");
        socket.send(bytes(fdata, 'utf-8'));
        socket.send(b"\x00");
        _result_buffer = self.recvall(socket)
        socket.close()
        _result = ""

        if _result_buffer:
            _result = _result_buffer.decode('utf-8')
            if _result:
                _result = _result.strip()

        return _result

    def recvall(self, sock):
        BUFF_SIZE = 4096
        data = b''
        while True:
            part = sock.recv(BUFF_SIZE)
            data += part
            if len(part) < BUFF_SIZE:
                break
        return data

    def reset(self):
        print("[haxe_completion] reset")
        self.shutdown()
        self.init()

    def shutdown(self, forced=False):
        if(forced == False):
            print("[haxe_completion] shutdown")

        if self.process is not None :
            self.process.terminate()
            self.process.kill()
            self.process.wait()

        self.process = None

def run_process( args ):
    _proc = run_process_bg(args)
    data = _proc.communicate()[0]
    return _proc, data

def run_process_bg( args ):
    _proc = None
    #this shell_cmd is not used by windows
    shell_cmd = ""
    for arg in args:
        #make sure lines from the hxml file don't trip up the shell
        shell_cmd += shlex.quote(arg) + " "

    if sys.platform == "win32":
        _proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, startupinfo=STARTUP_INFO)

    elif sys.platform == "darwin":
        # Use a login shell on OSX, otherwise the users expected env vars won't be setup
        _proc = subprocess.Popen(["/bin/bash", "-l", "-c", shell_cmd], stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, startupinfo=STARTUP_INFO, shell=False,
            preexec_fn=os.setsid)
    elif sys.platform == "linux":
        # Explicitly use /bin/bash on Linux, to keep Linux and OSX as
        # similar as possible. A login shell is explicitly not used for
        # linux, as it's not required
        _proc = subprocess.Popen(["/bin/bash", "-c", shell_cmd], stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, startupinfo=STARTUP_INFO, shell=False,
            preexec_fn=os.setsid)

    return _proc



class HaxeCompletionResetCommand( sublime_plugin.WindowCommand ):

    def run( self ) :
        global _haxe_completion_

        view = sublime.active_window().active_view()
        _haxe_completion_.reset()
