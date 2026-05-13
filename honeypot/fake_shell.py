import posixpath
import re

HOSTNAME = "ubuntu-server"
USERNAME = "root"

FAKE_FS = {
    "/": ["bin", "etc", "home", "root", "tmp", "var", "proc"],
    "/etc": ["passwd", "shadow", "hosts", "crontab", "ssh"],
    "/root": [".bashrc", ".ssh", "readme.txt"],
    "/tmp": [],
    "/var": ["log", "www"],
    "/proc": ["cpuinfo", "meminfo", "version"],
    "/bin": ["bash", "sh", "ls", "cat", "grep", "find", "ps", "netstat"],
}

FAKE_FILES = {
    "/etc/passwd": (
        "root:x:0:0:root:/root:/bin/bash\n"
        "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
        "www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin\n"
    ),
    "/etc/shadow": (
        "root:$6$rounds=656000$saltsaltsalt$hashedpasswordhere:19000:0:99999:7:::\n"
        "daemon:*:19000:0:99999:7:::\n"
    ),
    "/etc/hosts": "127.0.0.1 localhost\n127.0.1.1 ubuntu-server\n",
    "/etc/crontab": (
        "# /etc/crontab: system-wide crontab\n"
        "SHELL=/bin/sh\n"
        "PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin\n"
        "17 * * * * root cd / && run-parts --report /etc/cron.hourly\n"
        "25 6 * * * root test -x /usr/sbin/anacron || run-parts --report /etc/cron.daily\n"
    ),
    "/root/readme.txt": "Internal server — do not distribute credentials.\n",
    "/root/.bashrc": (
        "# ~/.bashrc: executed by bash(1) for non-login shells.\n"
        "export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n"
        "alias ll='ls -alF'\n"
    ),
    "/proc/version": "Linux version 5.15.0-91-generic (buildd@lcy02-amd64-032) (gcc version 11.4.0) #101-Ubuntu SMP\n",
    "/proc/cpuinfo": (
        "processor\t: 0\nvendor_id\t: GenuineIntel\n"
        "model name\t: Intel(R) Xeon(R) CPU E5-2676 v3 @ 2.40GHz\n"
        "cpu cores\t: 1\n"
    ),
    "/proc/meminfo": (
        "MemTotal:        1014688 kB\nMemFree:          123456 kB\n"
        "MemAvailable:    654321 kB\nSwapTotal:       1048572 kB\nSwapFree:         987654 kB\n"
    ),
}

UNAME = "Linux ubuntu-server 5.15.0-91-generic #101-Ubuntu SMP x86_64 GNU/Linux"
UPTIME = " 14:32:01 up 47 days,  3:12,  1 user,  load average: 0.08, 0.03, 0.01"

_WHICH_MAP = {
    "bash": "/bin/bash", "sh": "/bin/sh", "python3": "/usr/bin/python3",
    "python": "/usr/bin/python3", "perl": "/usr/bin/perl",
    "wget": "/usr/bin/wget", "curl": "/usr/bin/curl",
    "nc": "/bin/nc", "ncat": "/usr/bin/ncat", "netcat": "/bin/nc",
    "ls": "/bin/ls", "cat": "/bin/cat", "grep": "/bin/grep",
    "find": "/usr/bin/find", "ps": "/bin/ps", "netstat": "/bin/netstat",
    "ss": "/usr/sbin/ss", "ifconfig": "/sbin/ifconfig",
    "ip": "/sbin/ip", "iptables": "/sbin/iptables",
    "whoami": "/usr/bin/whoami", "id": "/usr/bin/id",
    "uname": "/bin/uname", "hostname": "/bin/hostname",
    "uptime": "/usr/bin/uptime", "pwd": "/bin/pwd",
    "echo": "/bin/echo", "env": "/usr/bin/env",
    "crontab": "/usr/bin/crontab", "chmod": "/bin/chmod",
    "chown": "/bin/chown", "mkdir": "/bin/mkdir",
    "touch": "/usr/bin/touch", "rm": "/bin/rm",
    "df": "/bin/df", "free": "/usr/bin/free",
}


class ShellSession:
    def __init__(self):
        self.cwd = "/root"
        self.history: list[str] = []
        self.tmp_files: dict[str, str] = {}
        self.tmp_dirs: set[str] = set()
        self.exited: bool = False
        self.env: dict[str, str] = {
            "HOME": "/root",
            "USER": "root",
            "LOGNAME": "root",
            "SHELL": "/bin/bash",
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "TERM": "xterm-256color",
            "LANG": "en_US.UTF-8",
            "PWD": "/root",
        }

    def all_files(self) -> dict[str, str]:
        return {**FAKE_FILES, **self.tmp_files}

    def resolve_path(self, path: str) -> str:
        if not path.startswith("/"):
            path = self.cwd + "/" + path
        return posixpath.normpath(path)

    def is_dir(self, path: str) -> bool:
        return path in FAKE_FS or path in self.tmp_dirs

    def fs_contents(self, path: str) -> list[str] | None:
        if path in FAKE_FS or path in self.tmp_dirs:
            base_entries = list(FAKE_FS.get(path, []))
            file_children = [
                p[len(path):].lstrip("/").split("/")[0]
                for p in self.tmp_files
                if p.startswith(path + "/")
            ]
            dir_children = [
                p[len(path):].lstrip("/").split("/")[0]
                for p in self.tmp_dirs
                if p.startswith(path + "/")
            ]
            all_children = list(dict.fromkeys(base_entries + file_children + dir_children))
            return all_children
        return None


def get_prompt(session: "ShellSession") -> str:
    display = "~" if session.cwd == "/root" else session.cwd
    return f"{USERNAME}@{HOSTNAME}:{display}# "


def _expand_vars(text: str, session: ShellSession) -> str:
    for k, v in session.env.items():
        text = text.replace(f"${k}", v).replace(f"${{{k}}}", v)
    return text


def _handle_redirect(parts: list[str], session: ShellSession):
    """Strip > redirection from parts, return (clean_parts, write_path | None)."""
    if ">" in parts:
        idx = parts.index(">")
        write_path = parts[idx + 1] if idx + 1 < len(parts) else None
        if write_path:
            write_path = session.resolve_path(write_path)
        return parts[:idx], write_path
    return parts, None


def handle_command(raw: str, session: ShellSession) -> str:
    """Execute a command against session state; returns response string."""
    raw = raw.strip()
    if not raw or raw.startswith("#"):
        return ""

    # simple pipe: run left side, ignore right (we log both halves)
    if "|" in raw:
        left = raw.split("|")[0].strip()
        return handle_command(left, session)

    parts = raw.split()
    parts, redirect_path = _handle_redirect(parts, session)
    base = parts[0]

    session.history.append(raw)
    session.env["PWD"] = session.cwd

    # --- navigation / session control ---
    if base in ("exit", "logout", "quit"):
        session.exited = True
        return "logout"

    if base in ("bash", "sh"):
        return ""  # stay in the same shell silently

    # --- identity ---
    if base == "whoami":
        return USERNAME

    if base == "id":
        return "uid=0(root) gid=0(root) groups=0(root)"

    # --- system info ---
    if base == "uname":
        if "-a" in parts:
            return UNAME
        if "-r" in parts:
            return "5.15.0-91-generic"
        if "-n" in parts:
            return HOSTNAME
        return "Linux"

    if base == "hostname":
        return HOSTNAME

    if base == "uptime":
        return UPTIME

    if base == "pwd":
        return session.cwd

    # --- environment ---
    if base in ("env", "printenv"):
        if len(parts) > 1 and base == "printenv":
            return session.env.get(parts[1], "")
        return "\n".join(f"{k}={v}" for k, v in session.env.items())

    if base == "echo":
        text = " ".join(parts[1:]) if len(parts) > 1 else ""
        text = _expand_vars(text, session)
        if redirect_path:
            session.tmp_files[redirect_path] = text + "\n"
            # also expose parent dir
            parent = posixpath.dirname(redirect_path)
            fname = posixpath.basename(redirect_path)
            if parent in FAKE_FS and fname not in FAKE_FS[parent]:
                FAKE_FS[parent] = list(FAKE_FS[parent]) + [fname]
            return ""
        return text

    # --- filesystem listing ---
    if base == "ls":
        target = session.cwd
        flags = [p for p in parts[1:] if p.startswith("-")]
        args = [p for p in parts[1:] if not p.startswith("-")]
        if args:
            target = session.resolve_path(args[0])
        contents = session.fs_contents(target)
        if contents is None:
            return f"ls: cannot access '{args[0] if args else target}': No such file or directory"
        if not contents:
            return ""
        long = any(f in flags for f in ("-l", "-la", "-al", "-lh"))
        if long:
            lines = [f"total {4 * len(contents)}"]
            for item in contents:
                full = target.rstrip("/") + "/" + item
                is_dir = session.is_dir(full)
                perm = "drwxr-xr-x" if is_dir else "-rw-r--r--"
                size = "4096" if is_dir else str(len(session.all_files().get(full, "")) or 512)
                lines.append(f"{perm} 2 root root {size:>6} Jan 15 09:12 {item}")
            return "\n".join(lines)
        return "  ".join(contents)

    if base == "cd":
        arg = parts[1] if len(parts) > 1 else "~"
        target = "/root" if arg == "~" else session.resolve_path(arg)
        if session.is_dir(target):
            session.cwd = target
            session.env["PWD"] = target
            return ""
        return f"bash: cd: {arg}: No such file or directory"

    if base == "cat":
        if len(parts) < 2:
            return ""
        path = session.resolve_path(parts[1])
        content = session.all_files().get(path)
        if content is not None:
            return content.rstrip("\n")
        return f"cat: {parts[1]}: No such file or directory"

    if base in ("head", "tail"):
        if len(parts) < 2:
            return ""
        path = session.resolve_path(parts[1])
        content = session.all_files().get(path)
        if content is None:
            return f"{base}: cannot open '{parts[1]}' for reading: No such file or directory"
        lines = content.splitlines()
        n = 10
        for i, p in enumerate(parts[1:], 1):
            if p.startswith("-n"):
                try:
                    n = int(p[2:]) if len(p) > 2 else int(parts[i + 1])
                except (ValueError, IndexError):
                    pass
        return "\n".join(lines[:n] if base == "head" else lines[-n:])

    if base == "grep":
        if len(parts) < 3:
            return ""
        pattern = parts[1]
        path = session.resolve_path(parts[2])
        content = session.all_files().get(path, "")
        matches = [line for line in content.splitlines() if pattern in line]
        return "\n".join(matches)

    if base == "find":
        start = session.cwd
        args = parts[1:]
        name_filter = None
        if "-name" in args:
            idx = args.index("-name")
            if idx + 1 < len(args):
                name_filter = args[idx + 1].strip("*")
        results = []
        for path in list(FAKE_FS.keys()) + list(session.tmp_files.keys()):
            if not path.startswith(start):
                continue
            if name_filter and name_filter not in posixpath.basename(path):
                continue
            results.append(path)
        return "\n".join(results) if results else ""

    if base == "mkdir":
        if len(parts) < 2:
            return "mkdir: missing operand"
        for arg in parts[1:]:
            if arg.startswith("-"):
                continue
            path = session.resolve_path(arg)
            session.tmp_dirs.add(path)
        return ""

    if base == "touch":
        if len(parts) < 2:
            return ""
        for arg in parts[1:]:
            path = session.resolve_path(arg)
            if path not in session.all_files():
                session.tmp_files[path] = ""
        return ""

    if base == "rm":
        if len(parts) < 2:
            return "rm: missing operand"
        removed = []
        for arg in parts[1:]:
            if arg.startswith("-"):
                continue
            path = session.resolve_path(arg)
            if path in session.tmp_files:
                del session.tmp_files[path]
                removed.append(path)
            elif path in FAKE_FILES:
                return f"rm: cannot remove '{arg}': Permission denied"
        return ""

    if base in ("chmod", "chown"):
        return ""  # silently succeed

    # --- process / network ---
    if base in ("ps",):
        return (
            "  PID TTY          TIME CMD\n"
            "    1 ?        00:00:02 systemd\n"
            "  423 ?        00:00:00 sshd\n"
            "  891 pts/0    00:00:00 bash\n"
            "  892 pts/0    00:00:00 ps"
        )

    if base == "top":
        return (
            "top - 14:32:01 up 47 days,  3:12,  1 user,  load average: 0.08, 0.03, 0.01\n"
            "Tasks:  73 total,   1 running,  72 sleeping,   0 stopped\n"
            "%Cpu(s):  0.3 us,  0.1 sy,  0.0 ni, 99.5 id\n"
            "MiB Mem :    990.9 total,    120.5 free,    234.7 used\n\n"
            "  PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND\n"
            "    1 root      20   0  168936  13456   8320 S   0.0   1.3   0:02.41 systemd\n"
            "  423 root      20   0   72312   7168   6144 S   0.0   0.7   0:00.08 sshd"
        )

    if base == "ifconfig" or (base == "ip" and len(parts) > 1 and parts[1] in ("addr", "a")):
        return (
            "eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\n"
            "      inet 10.0.2.15  netmask 255.255.255.0  broadcast 10.0.2.255\n"
            "      ether 08:00:27:4b:c3:9a  txqueuelen 1000  (Ethernet)\n\n"
            "lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536\n"
            "      inet 127.0.0.1  netmask 255.0.0.0"
        )

    if base in ("netstat", "ss"):
        return (
            "Active Internet connections (only servers)\n"
            "Proto Recv-Q Send-Q Local Address           Foreign Address         State\n"
            "tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN\n"
            "tcp        0      0 0.0.0.0:80              0.0.0.0:*               LISTEN"
        )

    if base == "df":
        return (
            "Filesystem      Size  Used Avail Use% Mounted on\n"
            "/dev/xvda1       20G  4.2G   15G  23% /\n"
            "tmpfs           496M     0  496M   0% /dev/shm"
        )

    if base == "free":
        return (
            "              total        used        free      shared  buff/cache   available\n"
            "Mem:         990912      240128      122880        1024      627904      605184\n"
            "Swap:       1048572           0     1048572"
        )

    # --- cron / persistence ---
    if base == "crontab":
        if "-l" in parts:
            return "# no crontab for root"
        if "-e" in parts:
            return ""
        return f"crontab: {parts[1] if len(parts) > 1 else 'unknown'}: command not found"

    # --- user / auth ---
    if base == "last":
        return (
            "root     pts/0        10.0.2.2         Mon Jan 15 09:12   still logged in\n"
            "root     pts/0        10.0.2.2         Sun Jan 14 22:45 - 23:01  (00:15)\n\n"
            "wtmp begins Sun Jan 14 22:45:01 2024"
        )

    if base == "w":
        return (
            " 14:32:01 up 47 days,  3:12,  1 user,  load average: 0.08, 0.03, 0.01\n"
            "USER     TTY      FROM             LOGIN@   IDLE JCPU   PCPU WHAT\n"
            "root     pts/0    10.0.2.2         09:12    0.00s  0.04s  0.00s w"
        )

    if base == "passwd":
        return "passwd: Authentication token manipulation error"

    if base in ("sudo", "su"):
        return f"[sudo] password for {USERNAME}: \nSorry, try again."

    # --- history ---
    if base == "history":
        if not session.history:
            return ""
        lines = []
        for i, cmd in enumerate(session.history, 1):
            lines.append(f"  {i:3}  {cmd}")
        return "\n".join(lines)

    # --- download tools ---
    if base in ("wget", "curl"):
        url = next((p for p in parts[1:] if not p.startswith("-")), "")
        host = url.split("/")[2] if "//" in url else url
        if base == "curl":
            return f"curl: (6) Could not resolve host: {host}"
        return (
            f"--2024-01-15 14:32:01--  {url}\n"
            f"Resolving {host}... failed: Name or service not known.\n"
            f"wget: unable to resolve host address '{host}'"
        )

    # --- package managers ---
    if base in ("apt", "apt-get", "yum", "dnf"):
        return "E: Could not open lock file /var/lib/dpkg/lock-frontend - open (13: Permission denied)"

    # --- interpreters ---
    if base in ("python", "python3"):
        return (
            'Python 3.10.12 (main, Nov 20 2023, 15:14:05) [GCC 11.4.0] on linux\n'
            'Type "help", "copyright", "credits" or "license" for more information.\n'
            '>>>'
        )

    if base == "perl":
        return ""

    # --- which/type ---
    if base in ("which", "type"):
        if len(parts) < 2:
            return ""
        target = parts[1]
        path = _WHICH_MAP.get(target)
        if path:
            return path if base == "which" else f"{target} is {path}"
        return f"{parts[1]}: not found" if base == "which" else f"bash: type: {parts[1]}: not found"

    # --- misc ---
    if base == "clear":
        return "\x1b[2J\x1b[H"

    if base == "lsb_release":
        return (
            "No LSB modules are available.\n"
            "Distributor ID:\tUbuntu\nDescription:\tUbuntu 22.04.3 LTS\n"
            "Release:\t22.04\nCodename:\tjammy"
        )

    if base == "date":
        return "Mon Jan 15 14:32:01 UTC 2024"

    if base == "iptables":
        if "-L" in parts:
            return (
                "Chain INPUT (policy ACCEPT)\ntarget     prot opt source               destination\n\n"
                "Chain FORWARD (policy ACCEPT)\ntarget     prot opt source               destination\n\n"
                "Chain OUTPUT (policy ACCEPT)\ntarget     prot opt source               destination"
            )
        return ""

    return f"bash: {base}: command not found"
