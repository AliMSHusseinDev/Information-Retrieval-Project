"""Exercise the actual desktop launcher without opening a browser (any platform)."""
import queue
import socket
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    # Occupy the preferred port to require the launcher's free-port fallback.
    occupied = socket.socket()
    occupied.bind(('127.0.0.1', 0))
    occupied.listen()
    preferred = occupied.getsockname()[1]
    command = [sys.executable, '-u', 'launcher.py', '--no-browser', '--port', str(preferred)]
    process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True)
    lines = queue.Queue()
    threading.Thread(target=lambda: [lines.put(line) for line in process.stdout], daemon=True).start()
    try:
        line = lines.get(timeout=15)
        assert 'Lumen IR is ready at http://127.0.0.1:' in line, line
        selected_port = int(line.strip().rsplit(':', 1)[1])
        assert selected_port != preferred, line
        duplicate = subprocess.run(command, cwd=ROOT, input='\n', capture_output=True, text=True, timeout=15)
        assert duplicate.returncode == 0, duplicate.stderr
        assert 'already running' in duplicate.stdout, duplicate.stdout
        process.stdin.write('\n')
        process.stdin.flush()
        assert process.wait(timeout=10) == 0
        # A restart proves the OS lock and port record are released after exit.
        restart = subprocess.run(command, cwd=ROOT, input='\n', capture_output=True, text=True, timeout=15)
        assert restart.returncode == 0, restart.stderr
        assert 'Lumen IR is ready' in restart.stdout, restart.stdout
        print('PASS: local Waitress readiness, occupied-port fallback, duplicate launch, Enter shutdown, and restart.')
    finally:
        occupied.close()
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


if __name__ == '__main__':
    main()
