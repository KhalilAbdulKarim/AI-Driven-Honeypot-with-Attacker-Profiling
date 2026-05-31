# import socket
# import threading
# import uuid
# from pathlib import Path

# import paramiko
# from paramiko import channel

# from honeypot.fake_shell import get_prompt, handle_command, ShellSession
# from honeypot.logger import SessionLogger

# _BASE_DIR = Path(__file__).parent.parent
# KEY_PATH = _BASE_DIR / "keys" / "host_rsa"
# KEY_PATH.parent.mkdir(exist_ok=True)

# _CONNECTION_LIMIT = threading.Semaphore(200)


# def _load_or_generate_key() -> paramiko.RSAKey:
#     if KEY_PATH.exists():
#         return paramiko.RSAKey(filename=str(KEY_PATH))
#     key = paramiko.RSAKey.generate(2048)
#     key.write_private_key_file(str(KEY_PATH))
#     print(f"[keygen] new host key written to {KEY_PATH}")
#     return key


# HOST_KEY = _load_or_generate_key()


# class HoneypotInterface(paramiko.ServerInterface):
#     """Accepts every login attempt — that's the point."""

#     def __init__(self, logger: SessionLogger):
#         self.logger = logger
#         self.event = threading.Event()

#     def check_channel_request(self, kind, chanid):
#         if kind == "session":
#             return paramiko.OPEN_SUCCEEDED
#         return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

#     def check_auth_password(self, username, password):
#         self.logger.log_auth(username, password, success=True)
#         return paramiko.AUTH_SUCCESSFUL

#     def check_auth_publickey(self, username, key):
#         fingerprint = key.get_fingerprint().hex()
#         self.logger.log_auth(username, f"pubkey:{fingerprint}", success=False)
#         return paramiko.AUTH_FAILED

#     def get_allowed_auths(self, username):
#         return "password"

#     def check_channel_shell_request(self, channel):
#         self.event.set()
#         return True

#     def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
#         return True

#     def check_channel_exec_request(self, channel, command):
#         cmd = command.decode(errors= "replace")
#         tmp_session = ShellSession()
#         response = handle_command(cmd, tmp_session)
#         channel.send((response + "\r\n").encode())
#         channel.sendall((response + "\r\n").encode())
#         channel.send_exit_status(0)
#         return True

# def _handle_session(client_sock: socket.socket, addr: tuple):

#     session_id = str(uuid.uuid4())[:8]
#     client_ip, client_port = addr
#     logger = SessionLogger(session_id, client_ip, client_port)
#     print(f"[connect] {client_ip}:{client_port} → session {session_id}")

#     transport = paramiko.Transport(client_sock)
#     transport.add_server_key(HOST_KEY)
#     transport.local_version = "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6"

#     server = HoneypotInterface(logger)
#     try:
#         transport.start_server(server=server)
#     except paramiko.SSHException:
#         logger.close()
#         return

#     channel = transport.accept(timeout=20)
#     if channel is None:
#         logger.close()
#         return

#     if not server.event.wait(timeout=10):
#         logger.close()
#         return

#     channel.settimeout(300)

#     # use ShellSession instead of bare cwd string
#     session = ShellSession()
#     channel.send(get_prompt(session).encode())

#     buf = b""
#     try:
#         while transport.is_active():
#             data = channel.recv(1024)
#             if not data:
#                 break
#             for byte in data:
#                 c = bytes([byte])
#                 if c == b"\r" or c == b"\n":
#                     channel.send(b"\r\n")
#                     command = buf.decode(errors="replace").strip()
#                     buf = b""
#                     if command:
#                         response = handle_command(command, session)
#                         logger.log_command(command, response)
#                         if session.exited:
#                             channel.send(b"logout\r\n")
#                             break
#                         if response:
#                             channel.send((response + "\r\n").encode())
#                     channel.send(get_prompt(session).encode())
#                 elif c == b"\x7f" or c == b"\x08":
#                     if buf:
#                         buf = buf[:-1]
#                         channel.send(b"\x08 \x08")
#                 elif c == b"\x03":
#                     buf = b""
#                     channel.send(b"^C\r\n")
#                     channel.send(get_prompt(session).encode())
#                 elif len(buf) < 4096:
#                     buf += c
#                     channel.send(c)
#     except socket.timeout:
#         pass
#     except Exception as e:
#         print(f"[session error] {session_id}: {e}")
#     finally:
#         logger.close()
#         channel.close()
#         transport.close()


# def _handle_session_guarded(client_sock: socket.socket, addr: tuple):
#     with _CONNECTION_LIMIT:
#         _handle_session(client_sock, addr)


# def start_server(host: str = "0.0.0.0", port: int = 2222):
#     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
#         sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#         sock.bind((host, port))
#         sock.listen(100)
#         print(f"[honeypot] listening on {host}:{port}")
#         try:
#             while True:
#                 client, addr = sock.accept()
#                 t = threading.Thread(target=_handle_session_guarded, args=(client, addr), daemon=True)
#                 t.start()
#         except KeyboardInterrupt:
#             print("\n[honeypot] shutting down")

import socket
import threading
import uuid
from pathlib import Path

import paramiko

from honeypot.fake_shell import get_prompt, handle_command, ShellSession
from honeypot.logger import SessionLogger

_BASE_DIR = Path(__file__).parent.parent
KEY_PATH  = _BASE_DIR / "keys" / "host_rsa"
KEY_PATH.parent.mkdir(exist_ok=True)

_CONNECTION_LIMIT = threading.Semaphore(200)


def _load_or_generate_key() -> paramiko.RSAKey:
    if KEY_PATH.exists():
        return paramiko.RSAKey(filename=str(KEY_PATH))
    key = paramiko.RSAKey.generate(2048)
    key.write_private_key_file(str(KEY_PATH))
    print(f"[keygen] new host key written to {KEY_PATH}")
    return key


HOST_KEY = _load_or_generate_key()


class HoneypotInterface(paramiko.ServerInterface):
    """Accepts every login attempt — that's the point."""

    def __init__(self, logger: SessionLogger):
        self.logger       = logger
        self.event        = threading.Event()
        self.auth_count   = 0
        self.username     = None

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        self.auth_count += 1
        self.username    = username
        print(f"[auth] {self.logger.client_ip} — {username}:{password} "
              f"(attempt #{self.auth_count})")
        self.logger.log_auth(username, password, success=True)
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_publickey(self, username, key):
        fingerprint = key.get_fingerprint().hex()
        self.logger.log_auth(username, f"pubkey:{fingerprint}", success=False)
        return paramiko.AUTH_FAILED

    def check_auth_none(self, username):
        """Some scanners try null auth — log it."""
        self.logger.log_auth(username, "", success=False)
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return "password"

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(
        self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
        return True

    def check_channel_exec_request(self, channel, command):
        """Handle non-interactive commands e.g. ssh host 'id'"""
        cmd         = command.decode(errors="replace").strip()
        tmp_session = ShellSession()
        response    = handle_command(cmd, tmp_session)
        self.logger.log_command(cmd, response)
        if response:
            channel.sendall((response + "\r\n").encode())
        channel.send_exit_status(0)
        self.event.set()
        return True

    def check_channel_subsystem_request(self, channel, name):
        """Reject SFTP and other subsystems gracefully."""
        return False


def _run_shell(channel, transport, logger, session_id):
    """Handle interactive shell session."""
    session = ShellSession()
    channel.send(get_prompt(session).encode())

    buf = b""
    try:
        while transport.is_active():
            data = channel.recv(1024)
            if not data:
                break

            for byte in data:
                c = bytes([byte])

                if c in (b"\r", b"\n"):
                    channel.send(b"\r\n")
                    command = buf.decode(errors="replace").strip()
                    buf = b""

                    if command:
                        response = handle_command(command, session)
                        logger.log_command(command, response)

                        if session.exited:
                            channel.send(b"logout\r\n")
                            return

                        if response:
                            channel.send((response + "\r\n").encode())

                    channel.send(get_prompt(session).encode())

                elif c in (b"\x7f", b"\x08"):
                    # backspace
                    if buf:
                        buf = buf[:-1]
                        channel.send(b"\x08 \x08")

                elif c == b"\x03":
                    # ctrl+c
                    buf = b""
                    channel.send(b"^C\r\n")
                    channel.send(get_prompt(session).encode())

                elif c == b"\x04":
                    # ctrl+d — EOF
                    channel.send(b"logout\r\n")
                    return

                elif c == b"\x1b":
                    # escape sequences — swallow silently
                    pass

                elif len(buf) < 4096:
                    buf += c
                    channel.send(c)

    except socket.timeout:
        pass
    except Exception as e:
        print(f"[shell error] {session_id}: {e}")


def _handle_session(client_sock: socket.socket, addr: tuple):
    session_id         = str(uuid.uuid4())[:8]
    client_ip, client_port = addr
    logger             = SessionLogger(session_id, client_ip, client_port)
    print(f"[connect] {client_ip}:{client_port} → session {session_id}")

    transport = paramiko.Transport(client_sock)
    transport.add_server_key(HOST_KEY)
    # masquerade as a real Ubuntu OpenSSH server
    transport.local_version = "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6"

    server = HoneypotInterface(logger)
    try:
        transport.start_server(server=server)
    except (paramiko.SSHException, EOFError, ConnectionResetError):
        # scanner probed port but didn't complete handshake
        logger.close()
        return
    except Exception as e:
        print(f"[transport error] {session_id}: {e}")
        logger.close()
        return

    channel = transport.accept(timeout=20)
    if channel is None:
        # authenticated but opened no channel — still log the auth
        logger.close()
        return

    channel.settimeout(300)

    # wait for shell or exec request
    if not server.event.wait(timeout=10):
        logger.close()
        return

    try:
        _run_shell(channel, transport, logger, session_id)
    finally:
        logger.close()
        try:
            channel.close()
        except Exception:
            pass
        try:
            transport.close()
        except Exception:
            pass


def _handle_session_guarded(client_sock: socket.socket, addr: tuple):
    with _CONNECTION_LIMIT:
        _handle_session(client_sock, addr)


def start_server(host: str = "0.0.0.0", port: int = 2222):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.listen(100)
        print(f"[honeypot] listening on {host}:{port}")
        try:
            while True:
                client, addr = sock.accept()
                t = threading.Thread(
                    target=_handle_session_guarded,
                    args=(client, addr),
                    daemon=True,
                )
                t.start()
        except KeyboardInterrupt:
            print("\n[honeypot] shutting down")