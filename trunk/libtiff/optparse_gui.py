'''A drop-in replacement for :pythonlib:`optparse` ("import iocbio.optparse_gui as optparse")

Provides an identical interface to
:pythonlib:`optparse`.OptionParser, in addition, it displays an
automatically generated `wx <http://www.wxpython.org>`_ dialog in order to enter the
options/args, instead of parsing command line arguments.

This code is based on `optparse_gui module
<http://code.google.com/p/optparse-gui/>`_. Unfortunately the owner of
optparse_gui did not respond to a request to join the optparse_gui
group. By now this module has become more complete with more features.

Module content
--------------
'''
#Author: Pearu Peterson
#Created: September 2009

__all__ = ['OptionParser', 'Option']

import os
import signal
import sys
import re
import shutil
import tempfile
import optparse
import wx
import subprocess as std_subprocess
if os.name=='nt':
    from . import killableprocess as subprocess
else:
    subprocess = std_subprocess

multiprocessing = None
try:
    import multiprocessing # Python <=2.5 users should install http://code.google.com/p/python-multiprocessing/
except ImportError:
    pass

import traceback
import Queue as queue

from .utils import splitcommandline

#try:
#    import matplotlib
#except ImportError:
#    matplotlib = None
#if matplotlib is not None:
#    matplotlib.use('Agg') # to avoid crashes with other backends

__version__ = 0.9

debug = 1

bug_report_email = 'iocbio-bugs@googlegroups.com'
smtp_server = 'cens.ioc.ee'

bug_report_email = None # disables the Bug Report button

signal_map = {}
for n,v in signal.__dict__.items ():
    if isinstance(v, int):
        signal_map[v] = n

def pretty_signal (s):
    r = signal_map.get(s)
    if r is None:
        r = signal_map.get(abs(s))
        if r is None:
            return str(s)
    return '%s[%s]' % (s,r)

def fix_float_string(s):
    if not s: return '0'
    if s[-1] in 'eE+-': return s + '0'
    return s

def fix_int_string (s):
    if s in ['+','-']: return s + '0'
    return s

def get_fixed_option_value (option, s):
    if option.type=='float': return fix_float_string(s)
    if option.type=='int': return fix_int_string(s)
    if option.type=='long': return fix_int_string(s)
    if option.type=='choice':
        choices = map(str, option.choices)
        try:
            return option.choices[choices.index(str(s))]
        except ValueError:
            pass
    return s

def os_kill(pid, s):
    if os.name=='nt':
        if s==signal.SIGTERM or s==signal.SIGINT:
            import win32api
            handle = win32api.OpenProcess(1, 0, pid)
            return (0 != win32api.TerminateProcess(handle, 127))
        if s==signal.SIGINT:
            import ctypes
            return (0 != ctypes.windll.kernel32.GenerateConsoleCtrlEvent (1, pid))
    return os.kill (pid, s)


class SysOutListener:
    debug_stream = '__stdout__'
    def __init__ (self, queue):
        self.queue = queue

    def write(self, string):
        if debug:
            stream = getattr (sys, self.debug_stream)
            if multiprocessing is not None or not string.startswith('\r'):
                stream.write(string)
            stream.flush()
        if multiprocessing is None:
            self.queue.put(string)
        else:
            if not self.queue._closed:
                self.queue.put(string)
        #wx.WakeUpIdle() # it does not seem to have effect, so using wx.Timer below

    def flush (self):
        if debug:
            stream = getattr (sys, self.debug_stream)
            stream.flush()

class SysErrListener (SysOutListener):
    debug_stream = '__stderr__'

    def write (self, string):
        if not self.queue._closed:
            self.queue.put('@STDERR START@')
        SysOutListener.write (self, string)
        if not self.queue._closed:
            self.queue.put('@STDERR END@')

class FunctionWrapper (object):

    def __init__ (self, func, log_queue = None):
        self.log_queue = log_queue
        self.func = func

    def __call__(self, *args, **kw):
        if self.log_queue is not None:
            saved_streams =  sys.stdout, sys.stderr
            sys.stdout = SysOutListener(self.log_queue)
            sys.stderr = SysErrListener(self.log_queue)
        
        status = 0
        try:
            self.func(*args, **kw)
        except:
            print "Exception in runner process:"
            print '-'*60
            traceback.print_exc(file=sys.stdout)
            print '-'*60        
            status = 1

        if self.log_queue is not None:
            sys.stdout, sys.stderr = saved_streams
        return status

class OptionValidator (wx.PyValidator):

    def __init__ (self, option):
        wx.PyValidator.__init__ (self)
        self.option = option
        self.Bind (wx.EVT_CHAR, self.OnChar)

    def Clone (self):
        return OptionValidator(self.option)
    
    def Validate (self, win):
        return True

    def OnChar(self, event):
        key = event.GetKeyCode()
        if key < wx.WXK_SPACE or key == wx.WXK_DELETE or key > 255:
            event.Skip ()
            return
        if self.option.type == 'choice':
            return

        textCtrl = self.GetWindow()
        i = textCtrl.GetInsertionPoint()
        char = chr(key)
        text = textCtrl.GetValue()
        new_text = get_fixed_option_value(self.option, text[:i] + char + text[i:])
        try:
            self.option.TYPE_CHECKER[self.option.type](self.option, self.option.dest, new_text)
        except optparse.OptionValueError, msg:
            if not wx.Validator_IsSilent():
                wx.Bell()
            print >> sys.stderr, msg
            return
        event.Skip()


class OptionPanel( wx.Panel ):
    
    def __init__(self, parent, option_list, main_frame):
        wx.Panel.__init__ (self, parent)

        sizer = wx.FlexGridSizer(cols=3, hgap=5, vgap=5)
        sizer.AddGrowableCol(1)

        destinations_list = []
        for option in option_list:

            help = option.help or 'specify %s option. Default: %%default.' % (option.get_opt_string())
            if '%default' in help:
                if option.default == optparse.NO_DEFAULT:
                    help = help.replace ('%default', 'none')
                else:
                    if option.action == 'store_false':
                        help = help.replace ('%default', str(not option.default if option.default is not None else option.default))
                    else:
                        help = help.replace ('%default', str(option.default))

            if option.action == 'store':
                label_txt = option.get_opt_string() + '='
                label = wx.StaticText(self, -1, label_txt )
                label.SetHelpText( help)
                sizer.Add (label, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)

                if option.type == 'choice':
                    if option.default == optparse.NO_DEFAULT:
                        option.default = option.choices[0]
                    ctrl = wx.ComboBox(
                        self, -1, choices = map(str,option.choices),
                        value = str(option.default),
                        style = wx.CB_DROPDOWN | wx.CB_READONLY | wx.CB_SORT 
                    )
                    sizer.Add (ctrl, 0, wx.EXPAND)
                    sizer.Add ((20,20),0)
                elif option.type in ['string', 'int', 'float']:
                    ctrl = wx.TextCtrl( self, -1, "", style=wx.TE_PROCESS_ENTER)
                    if option.default not in [optparse.NO_DEFAULT, None]:
                        ctrl.Value = str(option.default)
                    sizer.Add (ctrl, 0, wx.EXPAND)
                    sizer.Add ((20,20),0)
                elif option.type == 'multiline':
                    ctrl = wx.TextCtrl( self, -1, "", size=(300,100), 
                                        style = wx.TE_MULTILINE|wx.TE_PROCESS_ENTER )
                    if option.default not in [optparse.NO_DEFAULT, None]:
                        ctrl.Value = option.default
                    sizer.Add (ctrl, 0, wx.EXPAND)
                    sizer.Add ((20,20),0)
                elif option.type in ['file', 'directory']:
                    ctrl = wx.TextCtrl( self, -1, "")
                    if option.default not in [optparse.NO_DEFAULT, None]:
                        ctrl.Value = option.default
                    sizer.Add (ctrl, 0, wx.EXPAND)

                    browse = wx.Button( self, label='Browse..' )
                    browse.SetHelpText( 'Click to open %s browser' % (option.type) )
                    wx.EVT_BUTTON(self, browse.GetId(), main_frame.OnSelectPath)
                    main_frame.browse_option_map[browse.GetId()] = option, ctrl
                    sizer.Add(browse, 0, wx.ALIGN_CENTRE|wx.ALL, 1 )
                else:
                    raise NotImplementedError (`option.type`)
                destinations_list.append(option.dest)

            elif option.action in ['store_true', 'store_false']:
                if option.dest in destinations_list:
                    continue
                ctrl = wx.CheckBox( self, -1, option.get_opt_string())
                #ctrl = wx.ToggleButton( self, -1, option.get_opt_string())
                if option.default not in [None, optparse.NO_DEFAULT]:
                    if option.action=='store_false':
                        ctrl.SetValue(not option.default)
                    else:
                        ctrl.SetValue(option.default)
                sizer.Add (ctrl, 0, wx.EXPAND)
                #sizer.Add ((20,20),0)
                sizer.Add (wx.StaticText(self,-1,help),0,wx.ALIGN_CENTER_VERTICAL)
                sizer.Add ((20,20),0)
                destinations_list.append(option.dest)
            elif option.action == 'help':
                ctrl = wx.Button( self, -1, 'Help')
                sizer.Add (ctrl, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
                #sizer.Add ((20,20),0)
                sizer.Add (wx.StaticText(self,-1,"print help message"),0,wx.ALIGN_CENTER_VERTICAL)
                sizer.Add ((20,20),0)
                self.Bind(wx.EVT_BUTTON, main_frame.OnHelp, id=ctrl.GetId())
            elif option.action == 'store_const':
                if option.dest in destinations_list:
                    continue
            else:
                raise NotImplementedError (`option.action`)

            if option.type in option.TYPE_CHECKER:
                ctrl.SetValidator(OptionValidator(option))

            ctrl.SetHelpText( help )
            main_frame.option_controls[ option ] = ctrl


        self.SetSizer(sizer)
        self.Fit()
        #sizer.SetSizeHints(self)

class OptparseFrame (wx.Frame):

    def capture_std_streams(self):
        global multiprocessing
        if multiprocessing is None:
            self.log_queue = queue.Queue()
        else:
            try:
                self.log_queue = multiprocessing.Queue()
            except WindowsError, msg:
                print 'multiprocessing.Queue raised WindowsError: %s' % (msg)
                print 'Disableing multiprocessing'
                multiprocessing = None
                self.log_queue = None
                return
                self.log_queue = queue.Queue()
        self._saved_streams =  sys.stdout, sys.stderr
        sys.stdout = SysOutListener(self.log_queue)
        sys.stderr = SysErrListener(self.log_queue)

    def restore_std_streams (self):
        if self.log_queue is not None:
            sys.stdout, sys.stderr = self._saved_streams
            if multiprocessing is not None:
                self.log_queue.close()
            self.log_queue = None

    def __init__(self, option_parser):

        self.option_parser = option_parser
        self.option_parser.result = None 
        self.capture_std_streams()
        run_methods = getattr(option_parser, 'run_methods', ['subprocess', 'subcommand'])

        self.option_controls = {}
        self.browse_option_map = {}
        self.process_list = []

        wx.Frame.__init__(self, None, title="Optparse Dialog: %s" % (os.path.basename(sys.argv[0])))
        p = wx.Panel(self)

        provider = wx.SimpleHelpProvider()
        wx.HelpProvider_Set(provider)

        nb = wx.Notebook(p)
        
        option_panel = OptionPanel(nb, option_parser.option_list, self)
        option_panel.SetHelpText (option_parser.description or 'Main options')
        nb.AddPage(option_panel, 'Main Options')

        pages = []
        for group in option_parser.option_groups:
            if group in pages:
                continue
            option_panel = OptionPanel(nb, group.option_list, self)
            option_panel.SetHelpText (group.description or 'Group options')
            nb.AddPage(option_panel, group.title)
            pages.append(group)

        sizer_a = wx.BoxSizer (wx.VERTICAL)
        self.args_ctrl = args_ctrl = wx.TextCtrl(p, -1, '', size = ( -1, 80 ), 
                                                 style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER )
        args_ctrl.SetHelpText ('''\
Arguments can be either separated by a space or a newline. Arguments
that contain spaces must be entered like so: "arg with space"\
''')
        label = wx.StaticText(p, -1, 'Arguments:' )
        label.SetHelpText( 'Enter arguments here' )
        sizer_a.Add (label, 0, wx.EXPAND)
        sizer_a.Add (args_ctrl, 0, wx.EXPAND)
        args_ctrl.Fit ()

        sizer_b = wx.BoxSizer (wx.HORIZONTAL)


        cancel_b = wx.Button(p, -1, 'Cancel')
        cancel_b.SetHelpText('Cancel the program without saving')

        if debug>1:
            test_b = wx.Button(p, -1, 'Test')
            test_b.SetHelpText('Test options')

        run_b = None
        if option_parser.runner is not None or 1:
            self.run_b = run_b = wx.Button(p, -1, 'Run')
            run_b.SetHelpText('Run script with specified options and arguments.')

        batch_b = None
        if 0:
            self.batch_b = batch_b = wx.Button(p, -1, 'Batch')
            batch_b.SetHelpText('Run script with specified options and arguments in batch mode and exit.')

        self.exit_b = exit_b = wx.Button(p, -1, 'Exit')
        exit_b.SetHelpText('Exit without running the script. Any running process will be terminated.')

        send_b = None
        if bug_report_email:
            send_b = wx.Button (p, -1, 'Send Bug Report')
            send_b.SetHelpText ('Send bug report to %r. The bug report will include some environment data, used options and arguments, the content of the log window. If you want to add some notes then enter them to log window before pressing the Send Bug Report button.' % (bug_report_email))

        runner_mth = None
        if multiprocessing is None or option_parser.runner is None:
            self.run_method = 'subcommand'
        else:
            self.run_method = run_methods[0]
            if len (run_methods)>1:
                runner_mth = wx.ComboBox(
                    p, -1, choices = run_methods,
                    value = run_methods[0],
                    style = wx.CB_DROPDOWN | wx.CB_READONLY | wx.CB_SORT 
                    )
                runner_mth.SetHelpText ('Specify how to run application. Selecting subprocess means using multiprocessing.Process. Selecting subcommand means running the application with --no-gui option and using specified options. If application uses wx then one should select subcommand.')

        sizer_b.Add(cancel_b, 0, wx.ALL, 2)
        if debug>1:
            sizer_b.Add(test_b, 0, wx.ALL, 2)
        if run_b is not None:
            sizer_b.Add(run_b, 0, wx.ALL, 2)
            if runner_mth is not None:
                sizer_b.Add(runner_mth, 0, wx.ALL, 2)
        if batch_b is not None:
            sizer_b.Add(batch_b, 0, wx.ALL, 2)
        sizer_b.Add(exit_b, 0, wx.ALL, 2)
        if send_b is not None:
            sizer_b.Add(send_b, 0, wx.ALL, 2)

        self.log_window = log_window = wx.TextCtrl (p, -1, '', style = wx.TE_MULTILINE,
                                                    size = ( -1, 120 ))
        log_window.SetFont(wx.Font(8, wx.MODERN, wx.NORMAL, wx.NORMAL, False))
        log_window.SetHelpText ('Shows the standard output and error messages of a running process.')

        if wx.Platform != "__WXMSW__" or 1:
            help_b = wx.ContextHelpButton(p)
            sizer_b.Add((20,20),1)
            sizer_b.Add(help_b, 0, wx.RIGHT, 2)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(nb, 0, wx.EXPAND)
        sizer.Add(sizer_a, 0, wx.EXPAND, 5 )
        sizer.Add(sizer_b, 0, wx.EXPAND|wx.BOTTOM, 5)
        sizer.Add(log_window, 1, wx.EXPAND)

        p.SetSizer(sizer)
        p.Fit ()
        sizer.SetSizeHints(p)

        self.Fit ()

        self.timer = wx.Timer(self)


        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=cancel_b.GetId())
        if run_b is not None:
            self.Bind(wx.EVT_BUTTON, self.OnRun, id=run_b.GetId())
            if runner_mth is not None:
                self.Bind(wx.EVT_COMBOBOX, self.OnSelectRunnerMethod, id=runner_mth.GetId())
        if batch_b is not None:
            self.Bind(wx.EVT_BUTTON, self.OnBatch, id=batch_b.GetId())
        if debug>1:
            self.Bind(wx.EVT_BUTTON, self.OnTest, id=test_b.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnExit, id=exit_b.GetId())
        if send_b is not None:
            self.Bind(wx.EVT_BUTTON, self.OnSend, id=send_b.GetId())
        self.Bind(wx.EVT_IDLE, self.OnUpdateLogWindow)
        self.Bind(wx.EVT_TIMER, self.OnUpdateLogWindow, self.timer)

        self.previous_position = 0
        self._running_count = 0

    def OnSend(self, event):
        msg = ''

        msg += '-'*40 + '\n'
        msg += 'Environment\n'
        msg += '='*40 + '\n'
        msg += 'os.getcwd(): %r\n' % (os.getcwd())
        msg += 'sys.argv: ' + `sys.argv` + '\n'
        msg += 'sys.version: ' + `sys.version` + '\n'
        msg += 'sys.prefix: ' + `sys.prefix` + '\n'
        user = None
        for k in ['USER', 'LOGNAME', 'HOME', 'PYTHONPATH', 'PYTHONSTARTUP', 'LD_LIBRARY_PATH', 'PATH',
                  'LTSP_CLIENT','SSH_CONNECTION']:
            v = os.environ.get (k, None)
            if v is not None:
                msg += '%s: %r\n' % (k,v)

                if user is None and k in ['USER', 'LOGNAME']:
                    user = v
        msg += 'Installation path: %r\n' % (os.path.dirname (__file__))
        try:
            from . import version
            msg += 'Version: %s\n' % (version.version)
        except Exception, msg:
            msg += '%s\n' % (msg)
            pass
        msg += '-'*40 + '\n'

        msg += '\n'
        msg += '-'*40 + '\n'
        msg += 'Options\n'
        msg += '='*40 + '\n'    
        try:
            values, args = self.option_parser.parse_options_args
            self.set_result()
            values, args = self.option_parser.get_result (values)
            msg += 'args=%r\n' % (args)
            for option in self.option_parser._get_all_options():
                if option.dest:
                    value = getattr(values, option.dest, None)
                    if value is not None:
                        msg += '%s[dest=%s]: %r\n' % (option.get_opt_string(), option.dest, value)
        except Exception, m:
            msg += 'Failed to get option results: %s\n' % (m)
        msg += '-'*40 + '\n'

        msg += '\n'
        msg += '-'*40 + '\n'
        msg += 'Content of log window\n'
        msg += '='*40 + '\n'
        msg += self.log_window.GetValue() + '\n'
        msg += '-'*40 + '\n'

        message = msg

        user_email = user + "@" + smtp_server
        import smtplib
        from email.MIMEText import MIMEText
        msg = MIMEText(msg)
        msg['Subject'] = '[IOCBio bug report] %s' % (sys.argv[0])
        msg['From'] = user_email
        msg['To'] = bug_report_email

        try:
            s = smtplib.SMTP()
            s.connect(smtp_server)
            # Send the email - real from, real to, extra headers and content ...
            s.sendmail(user_email, bug_report_email, msg.as_string())
            s.close()
            print 'Bug report succesfully sent to %r' % (bug_report_email)
        except Exception, msg:
            print 'Failed to send bug report: %s' % (msg)
            f = open('iocbio_bug_report.txt', 'w')
            f.write (message)
            f.close()
            print 'Please find the file "iocbio_bug_report.txt" in the current working directory and send it to %r using your favorite E-mail program.' % (bug_report_email)

    def OnSelectRunnerMethod(self, event):
        self.run_method = event.GetString()

    def OnUpdateLogWindow(self, event):
        if self.log_queue is not None and not self.log_queue.empty():
            log_window = self.log_window
            is_stderr_message = None
            while 1:
                try:
                    v = self.log_queue.get_nowait()
                except queue.Empty:
                    break
                if v=='@STDERR START@':
                    is_stderr_message = True
                elif v=='@STDERR END@':
                    is_stderr_message = False
                else:
                    # todo: use is_stderr_message to switch styles
                    for line in v.splitlines(True):
                        if line.startswith('\r'):
                            log_window.Remove(self.previous_position, log_window.GetLastPosition())
                            line = line[1:]
                        self.previous_position = log_window.GetInsertionPoint()
                        log_window.AppendText(line)
            self.log_window.Refresh()

        if self.process_list:
            for index, (process, method) in enumerate(self.process_list):
                if method=='subprocess':
                    if not process.is_alive():
                        self._cleanup_process(process, method)
                        del self.process_list[index]
                elif method=='subcommand':
                    if process.poll() is not None:
                        self._cleanup_process(process, method)
                        del self.process_list[index]
                else:
                    raise NotImplementedError (`method`)
            self.cleanup_runner()

    def OnHelp (self, event):
        self.option_parser.print_help()

    def OnTest (self, event):
        values, args = self.option_parser.parse_options_args
        self.set_result()
        new_values, new_args = self.option_parser.get_result (values)
        print new_values, new_args

    def OnBatch (self, event):
        self.interrupt_runner()
        self.set_result()
        self.restore_std_streams()
        self.Close(True)

    def OnCancel (self, event):
        while self.process_list:
            self.interrupt_runner()
        self.result = None
        self.restore_std_streams()
        self.Close(True)
        sys.exit(0)

    def _start_process (self, method, show_info=[True]):
        self.set_result()
        values, args = self.option_parser.parse_options_args
        new_options, new_args = self.option_parser.get_result (values)
        if method=='subprocess':
            process = multiprocessing.Process(target=FunctionWrapper(self.option_parser.runner,
                                                                     self.log_queue), 
                                              args=(self.option_parser, new_options, new_args))
            process.start ()
            return process
        elif method=='subcommand':
            if multiprocessing is None:
                print 'Using multiprocessing package is disabled.'
                if sys.version[:3]<='2.5':
                    print 'Python 2.4, 2.5 users should install multiprocessing package from http://code.google.com/p/python-multiprocessing/'
            if show_info[0]:
                print 'Live session output is visible only in terminal.'
                print 'Wait for the runner process to finish..'
                show_info[0] = False
            self.option_parser.save_options(new_options, new_args)
            cmd_lst = []
            cmd_prefix = getattr(new_options, 'runner_subcommand', sys.executable)
            if cmd_prefix:
                cmd_lst.append(cmd_prefix)
            cmd_lst.append (sys.argv[0])
            cmd_lst.append ('--no-gui')
            cmd = ' '.join(cmd_lst)
            print 'Executing command:', cmd
            process = subprocess.Popen (cmd, shell=True,
                                        #stdout=std_subprocess.PIPE,
                                        stderr=std_subprocess.STDOUT)
            return process
        else:
            raise NotImplementedError (`method`)

    def _cleanup_process (self, process, method):
        if process is None:
            return
        if method=='subprocess':
            if process.exitcode is None:
                pid = process.pid
                print 'Runner %s (PID=%s) still running, trying to terminate' % (method, pid)
                process.terminate()
                process.join()
            print 'Runner %s has finished with exitcode=%s' % (method,  pretty_signal(process.exitcode))
        elif method=='subcommand':
            s = process.wait()
            if os.name=='nt':
                print 'Runner %s has finished with returncode=%s' % (method,  pretty_signal (s))
            else:
                pid = process.pid
                print 'Runner %s (PID=%s) has finished with returncode=%s' % (method, pid, pretty_signal(s))
        else:
            raise NotImplementedError (`method`)

    def _interrupt_process (self, process, method):
        if method=='subprocess':
            if process.is_alive():
                pid = process.pid
                os_kill(pid, signal.SIGINT)
                print
                print 'SIGINT signal has been sent to runner %s (PID=%s)' % (method, pid)
        elif method=='subcommand':
            if process.poll () is None:
                if os.name=='nt':
                    process.kill(True, s=signal.SIGINT)
                    print
                    print 'SIGINT signal has been sent to runner %s' % (method)
                else:
                    pid = process.pid
                    os_kill(pid, signal.SIGINT)
                    print
                    print 'SIGINT signal has been sent to runner %s (PID=%s)' % (method, pid)
        else:
            raise NotImplementedError (`method`)

    def _terminate_process (self, process, method):
        if method=='subprocess':
            if prosess.is_alive():
                print
                print 'Terminating runner %s' % (method)
                process.terminate()
        elif method=='subcommand':
            if process.poll() is None:
                if sys.version[:3]>='2.6':
                    print
                    print 'Terminating runner %s' % (method)
                    process.terminate ()
                else:
                    if os.name=='nt':
                        process.kill (True, s = signal.SIGTERM)
                    else:
                        os_kill (process.pid, signal.SIGTERM)
                    print
                    print 'SIGTERM signal has been sent to runner %s' % (method)
        else:
            raise NotImplementedError (`method`)

    def start_runner (self):
        if not self.process_list:
            self.exit_b.SetLabel('Stop')
            self.timer.Start(100)
        self.option_parser.run_method = self.run_method
        process = self._start_process(self.run_method)
        pid = process.pid
        print
        print 'Runner %s (PID=%s) has been started' % (self.run_method, pid)
        self.process_list.append((process, self.run_method))

    def cleanup_runner (self):
        if not self.process_list:
            self.timer.Stop()
            self.exit_b.SetLabel('Exit')

    def interrupt_runner (self):
        if self.process_list:
            process, run_method = self.process_list[-1]
            del self.process_list[-1]
            self._interrupt_process(process, run_method)
            self._cleanup_process(process, run_method)
        self.cleanup_runner()

    def terminate_runner(self):
        if self.process_list:
            process, run_method = self.process_list[-1]
            del self.process_list[-1]
            self._terminate_process(process, run_method)
            self._cleanup_process(process, run_method)
        self.cleanup_runner()

    def OnExit(self, event):
        if self.exit_b.GetLabel()=='Stop':
            self.interrupt_runner()
            return

        while self.process_list:
            self.terminate_runner()

        try:
            values, args = self.option_parser.parse_options_args
            self.set_result()
            values, args = self.option_parser.get_result(values)
            #self.option_parser.save_options(values, args)
        except optparse.OptionValueError, msg:
            print 'Ignoring %s' % (msg)
            pass

        self.restore_std_streams()
        self.Close(True)
        sys.exit(0)

    def OnRun(self, event):
        self.start_runner()

    def OnCloseWindow (self, event):
        while self.process_list:
            self.terminate_runner()
        self.restore_std_streams()
        self.result = None
        self.Destroy()

    def OnSelectPath(self, event):
        option, ctrl = self.browse_option_map[event.GetId()]
        path = os.path.abspath(ctrl.Value)
        if option.type == 'file':
            if os.path.isdir (path):
                default_file = ''
                default_dir = path
            else:
                default_file = path
                default_dir =os.path.dirname(path)
            dlg = wx.FileDialog(self,
                                message = 'Select file for %s' % (option.get_opt_string()),
                                defaultDir = default_dir, defaultFile=default_file)
        elif option.type == 'directory':
            if os.path.isfile(path):
                path = os.path.dirname (path)
            dlg = wx.DirDialog(self,
                               message = 'Select directory for %s' % (option.get_opt_string()),
                               defaultPath = path)
        else:
            raise NotImplementedError(`option.type`)
        if dlg.ShowModal() != wx.ID_OK:
            return
        cwd = os.path.abspath(os.getcwd())
        value = dlg.GetPath()
        if value.startswith(cwd):
            value = value[len(cwd)+1:]
        ctrl.Value = value

    def set_result(self):
        option_values = {}
        for option, ctrl in self.option_controls.iteritems():
            value = getattr(ctrl,'Value',None)
            if value != '' and value is not None:
                value = get_fixed_option_value(option, value)
                option_values[option] = value
            elif value is not None:
                option_values[option] = None
        args_buff = str(self.args_ctrl.GetValue())
        args =  splitcommandline(args_buff)
        self.option_parser.result = option_values, args

    def put_result(self):
        option_values, args = self.option_parser.result
        for option, ctrl in self.option_controls.iteritems():
            value = option_values.get(option)
            if value is not None:
                ctrl.SetValue(value)
        self.args_ctrl.SetValue(' '.join(args))

class UserCancelledError( Exception ):
    pass

def check_file(option, opt, value):
    try:
        value = str(value)
    except ValueError:
        raise OptionValueError(
            _("option %s: invalid %s value: %r") % (opt, what, value))
    #if value and not os.path.isfile(value):
    #    print 'Warning: path %r is not a file' % (value)
    return value

def check_directory(option, opt, value):
    try:
        value = str(value)
    except ValueError:
        raise OptionValueError(
            _("option %s: invalid %s value: %r") % (opt, what, value))
    #if value and not os.path.isdir(value):
    #    print 'Warning: path %r is not a directory' % (value)
    return value

class Option(optparse.Option):
    """Extends optparse.Option with file, directory and multiline types.
    """
    _SUPER = optparse.Option
    TYPES = _SUPER.TYPES + ('file', 'directory', 'multiline')
    TYPE_CHECKER = _SUPER.TYPE_CHECKER.copy()
    TYPE_CHECKER.update (file=check_file, directory=check_directory)


class OptionParser( optparse.OptionParser ):
    """Extends optparse.OptionParser with GUI support.
    """
    _SUPER = optparse.OptionParser
    """Holds base class.
    """
    
    def __init__( self, *args, **kwargs ):
        if 'option_class' not in kwargs:
            kwargs['option_class'] = Option
        self.runner = None
        self._SUPER.__init__( self, *args, **kwargs )

    def save_option_value (self, dest, value):
        return self._set_dest_value (dest, value)

    def _set_dest_value(self, dest, value, old_cwd = None):
        if value is None:
            return
        option = ([option for option in self._get_all_options () if option.dest == dest] + [None])[0]
        if option is None:
            print 'Could not find option with dest=%r for setting %r (dest not specified for option).' % (dest, value)
        else:
            if option.type in ['file', 'directory']:
                if old_cwd is not None:
                    value = os.path.join(old_cwd, value)
                else:
                    value = os.path.abspath(value)
                cwd = os.getcwd()
                if value.startswith(cwd):
                    value = value[len(cwd)+1:]
            if value == 'none':
                value = None
            else:
                try:
                    option.check_value(option.dest, str(value))
                except optparse.OptionValueError, msg:
                    print '_set_dest_value: ignoring %s' % msg
                    return
                option.default = value
        if value is None:
            try:
                del self.defaults[dest]
            except KeyError:
                pass
        else:
            self.defaults[dest] = value

    def get_history_file(self):
        import hashlib
        script_history = os.path.join(os.environ.get('HOME',''), '.optparse_history', 
                                      os.path.basename(sys.argv[0]) + hashlib.md5(os.path.abspath(sys.argv[0])).hexdigest())        
        return script_history


    def save_options (self, values, args):
        script_history = self.get_history_file()
        if debug>1:
            print 'Saving options to', script_history
        cwd = os.path.abspath(os.getcwd())
        dirname = os.path.dirname(script_history)
        if not os.path.isdir (dirname):
            os.makedirs(dirname)

        tmp_file = tempfile.mktemp()
            
        f = open(tmp_file, 'w')
        f.write ('#cwd:%r\n' % (cwd))
        f.write ('#args:%r\n' % (args,))
        for option in self._get_all_options():
            if option.dest:
                value = getattr(values, option.dest, None)
                if value is not None:
                    f.write('%s: %r\n' % (option.dest, value))
        f.close()        

        shutil.move(tmp_file, script_history)
        
    def load_options(self):
        script_history = self.get_history_file ()
        if debug>1:
            print 'Loading options from',script_history
        h_args = None
        h_cwd = None
        cwd = os.path.abspath(os.getcwd())
        if os.path.isfile(script_history):
            f = open (script_history)
            for line in f.readlines():
                try:
                    dest, value = line.split(':', 1)
                    value = eval(value)
                except Exception, msg:
                    print 'optparse_gui.load_options: failed parsing options file, line=%r: %s' % (line, msg)
                    continue
                if dest=='#args':
                    h_args = value
                elif dest=='#cwd':
                    h_cwd = value
                else:
                    self._set_dest_value(dest, value, h_cwd)
            f.close()        
        return h_args

    def parse_args( self, args = None, values = None ):
        '''Parse the command-line options.
        '''
        # load options history
        h_args = self.load_options()

        no_gui = '--no-gui' in sys.argv
        if no_gui:
            sys.argv.remove('--no-gui')
        # preprocess command line arguments and set to defaults
        pp_option_values, pp_args = self._SUPER.parse_args(self, args, values)

        if no_gui:
            self.save_options(pp_option_values, pp_args)
            return pp_option_values, pp_args

        for dest, value in pp_option_values.__dict__.iteritems():
            self._set_dest_value(dest, value)

        self.parse_options_args = (values, args)

        app = wx.App(redirect=False)
        try:
            dlg = OptparseFrame(self)
        except Exception, msg:
            traceback.print_exc(file=sys.stdout)
            raise
        if pp_args:
            dlg.args_ctrl.Value = ' '.join(pp_args)
        elif h_args is not None:
            dlg.args_ctrl.Value = ' '.join(h_args)
        dlg.Show (True)
        app.MainLoop()

        if self.result is None:
            print 'User has cancelled, exiting.'
            sys.exit(0)
        
        values, args = self.get_result(values)
        self.save_options(values, args)

        return values, args

    def error( self, msg ):
        print "AN ERROR OCCURRED WITH A MESSAGE: %s" % (msg)
        #app = wx.GetApp()
        #print app, msg
        #if app is None:    
        #    app = wx.App( False )
        #wx.MessageDialog( None, msg, 'Error!', wx.ICON_ERROR ).ShowModal()
        return self._SUPER.error( self, msg )

    def get_result(self, values):
        if values is None:
            values = self.get_default_values()
            
        option_values, args = self.result
         
        for option, value in option_values.iteritems():
            if option.action=='store_true':
                if isinstance(value, bool):
                    setattr( values, option.dest, value )
                continue
            if option.action=='store_false':
                if isinstance(value, bool):
                    setattr( values, option.dest, not value )
                continue
            
            if option.takes_value() is False:
                value = None

            option.process( option, value, values, self )
        return values, args

################################################################################

def sample_parse_args():
    usage = "usage: %prog [options] args"
    if 1 == len( sys.argv ):
        option_parser_class = OptionParser
    else:
        option_parser_class = optparse.OptionParser
        
    parser = option_parser_class( usage = usage, version='0.1' )
    parser.add_option("-f", "--file", dest="filename", default = r'c:\1.txt',
                      help="read data from FILENAME")
    parser.add_option("-t", "--text", dest="text", default = r'c:\1.txt',
                      help="MULTILINE text field")
    parser.add_option("-a", "--action", dest="action",
                      choices = ['delete', 'copy', 'move'],
                      help="Which action do you wish to take?!")
    parser.add_option("-n", "--number", dest="number", default = 23,
                      type = 'int',
                      help="Just a number")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose",
                      help = 'To be or not to be? ( verbose )' )
    
    (options, args) = parser.parse_args()
    return options, args

def sample_parse_args_issue1():
    usage = "usage: %prog [options] args"
    option_parser_class = OptionParser
        
    parser = option_parser_class( usage = usage, version='0.1' )
    parser.add_option("-f", "--file", dest="filename", default = r'c:\1.txt',
                      type = 'file',
                      help="read data from FILENAME")
    parser.add_option("-t", "--text", dest="text", default = r'c:\1.txt',
                      type = 'multiline',
                      help="MULTILINE text field")
    parser.add_option("-a", "--action", dest="action",
                      choices = ['delete', 'copy', 'move'],
                      help="Which action do you wish to take?!")
    parser.add_option("-n", "--number", dest="number", default = 23,
                      type = 'int',
                      help="Just a number")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose",
                      help = 'To be or not to be? ( verbose )' )

    group = optparse.OptionGroup(parser, "Dangerous Options",
                        "Caution: use these options at your own risk.  "
                        "It is believed that some of them bite.")
    group.add_option("-g", action="store_true", help="Group option.",
                     )
    parser.add_option_group(group)

    (options, args) = parser.parse_args()
    return options, args

def main():
    options, args = sample_parse_args_issue1()
    print 'args: %s' % repr( args )
    print 'options: %s' % repr( options )
    
if '__main__' == __name__:
    main()
