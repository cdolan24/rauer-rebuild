import subprocess
import time
import requests
import os
import sys

SERVER_CMD = [
    sys.executable,
    '-m', 'uvicorn', 'src.api.main:app', '--host', '127.0.0.1', '--port', '8000', '--reload'
]

os.environ['GENERIC_BASE_URL'] = 'http://localhost:11434/v1'
os.environ['GENERIC_API_KEY'] = 'ollama'

def wait_for_server(timeout=30):
    url = 'http://127.0.0.1:8000/api/health'
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                return True, r.json()
        except Exception:
            time.sleep(1)
    return False, None

def run_server_and_test():
    print('Starting server with timeouts...')
    proc = subprocess.Popen(SERVER_CMD, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        ok, health = wait_for_server(timeout=60)
        if ok:
            print('Server started successfully. Health endpoint:', health)
        else:
            print('Server did not start within timeout.')
        # Gather diagnostics
        print('Diagnostics:')
        print('GENERIC_BASE_URL:', os.environ.get('GENERIC_BASE_URL'))
        print('GENERIC_API_KEY:', os.environ.get('GENERIC_API_KEY'))
        print('Ollama models:')
        try:
            ollama_proc = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=10)
            print(ollama_proc.stdout)
        except Exception as e:
            print('Ollama diagnostics failed:', e)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
    print('Server process terminated.')

if __name__ == '__main__':
    run_server_and_test()
