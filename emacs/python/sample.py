# -*- codeing: utf-8 -*-
# Note:
# 1. 由于本机windows没有启动consul agent,将无法使用测试桩
# 2. 调试单个用例时，注释掉stopmock函数

import unittest
import subprocess
from HTMLTestRunner import HTMLTestRunner

microservice_name  = 'recommend'
#mock_info = None
mock_info = {"mockport":12345, "consuldepend": ["storagehotel", "data"]}
mock_process = None

import sys
mswindows = (sys.platform == "win32")

def startmock(case_path):
    if mswindows:
        print("ignore start mock in windows")
        return

    if not mock_info:
        print("no mock")
        return

    global microservice_name, mock_process
    import os, time
    mockfile = "%s/mock/mock.%s.json" % (case_path, microservice_name)
    print("mockfile is %s" % mockfile)
    if not os.path.isfile(mockfile):
        print("mock file does not exist")
        exit(-1)

    print "start mock"
    currentdir = os.getcwd() #获取当前工作目录
    os.chdir("%s/mock" % case_path)
    try:
        if mswindows:
            mock_process = subprocess.Popen("java -jar ../../../lib/mock/moco-runner-0.12.0-standalone.jar http -p %d -c %s > mock.log" %(mock_info["mockport"], os.path.basename(mockfile)), shell=True, stdout = subprocess.PIPE, stderr = subprocess.PIPE, creationflag=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            mock_process = subprocess.Popen("java -jar ../../../lib/mock/moco-runner-0.12.0-standalone.jar http -p %d -c %s > mock.log" %(mock_info["mockport"], os.path.basename(mockfile)), shell=True, stdout = subprocess.PIPE, stderr = subprocess.PIPE, preexec_fn = os.setpgrp)
    except:
        print("popen mock failed")
        exit(-1)

    print("mock pid:%d" % mock_process.pid)
    print("mock pgid:%d" % os.getpgid(mock_process.pid))

    os.chdir(currentdir)

    #consul 注册
    registerconsul()
    time.sleep(60)


def stopmock():
    if mswindws:
        print("ignore stop mock in windows")
        return

    if not mock_info:
        return

    global mock_process
    import os, signal
    if mock_process:
        print("stop mock")
        try:
            if mswindows:
                command = 'taskkill /F /T /PID %d' % mock_process.pid
                os.system(command)
            else:
                # mock_process.terminate()
                os.killpg(mock_process.pid, signal.SIGTERM)
        except:
            print("mock terminate failed")
            import traceback, sys
            print >> sys.stderr, "Error in"
            traceback.print_exc()
            exc_info = sys.exc_info()
            exit(-1)

    #consul 注册
    deregisterconsul()


def registerconsul():
    if mswindows:
        print("igonore consul register in windows")
        return

    print("register consul")
    mock_port = mock_info["mockport"]
    for node in mock_info["consuldepend"]:
        process = subprocess.Popen('''curl -X PUT -d '{"id": "%s-test", "name": "%s", "address": "127.0.0.1", "port":%d, "tags": ["test mock"], "checks": [{"http": "http://127.0.0.1:%d/health", "interval": "5s"}]}' http://127.0.0.1:8500/v1/agent/service/register''' % (node,node, mock_port, mock_port), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.stdout.readline()
        process.terminate()

def deregisterconsul():
    if mswindows:
        print("ignore consul deregister in windows")
        return

    print("deregister consul")
    mock_port = mock_info["mockport"]
    for node in mock_info["consuldepend"]:
        process = subprocess.Popen("curl -X PUT http://127.0.0.1:8500/v1/agent/service/deregister/%s-test" % (node), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.stdout.readline()
        process.terminate()


def modifyconfig(top_path):
    global microservice_name

    import os, re
    env_pattern = re.compile(r'.*"%s":([A-Z_]+)' % microservice_name)
    cfg_pattern = re.compile(r'(const.CONFIG = )(.*)')

    config_file = "%s%sconfig%s%s" %(top_path, os.path.sep, os.path.sep, "customize.py")

    w_str=''
    with open(config_file, 'r') as load_f:
        env = ''
        for line in load_f:
            if not line or line[0] == '#':
                w_str += line
                continue
            env_match = env_pattern.match(line)
            cfg_match = cfg_pattern.match(line)

            if env_match:
                env = env_match.group(1)
                print("correct env is %s" % env)
                w_str += line
            elif cfg_match:
                w_str += cfg_match.group(1) + env + '\n'
                print("old env is %s" % line)
            else:
                w_str += line


    with open(config_file, 'w') as write_f:
        write_f.write(w_str)


def prepare_env():
    import os, sys
    # case_path = os.getcwd()
    case_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    #AutoTest
    top_path = os.path.dirname(os.path.dirname(case_path))
    sys.path.append(top_path)

    moidfyconfig(top_path)

    import datetime
    now = datetime.datetime.now()
    today = now.strftime("%Y%m%d")
    release_path = "%s%srelease%s%s" %(top_path, os.path.sep, os.path.sep, today)
    print(release_path)

    if not os.path.isdir(release_path):
        os.makedirs(release_path)

    return (case_path, release_path)


def execute_cases(tuple):
    global microservice_name

    import os
    (case_path, release_path) = tuple

    suite = unittest.TestSuite()

    # 要求目录下需要放置init.py
    suite.addTests(unittest.defaultTestLoader.discover(case_path, "*.py", top_level_dir = None))

    print("get total cases: %d" % suite.countTestCases())

    report_filename = "%s%sReport_%s.html" %(release_path, os.path.sep, microservice_name)
    with open(report_filename, 'w') as f:
        runnner = HTMLTestRunner(stream=f, title = 'MicroService %s Test Report' % (microservice_name), description = 'generated by pytest', verbosity = 2)
        runner.run(suite)


def main():
    tuple = prepare_env()

    #启动mock
    startmock(tuple[0])

    execute_cases(tuple)

    #停止mock
    stopmock()


if __name__ == "__main__":
    main()
