#!/usr/bin/python3
import os
import sys
import argparse
import subprocess

banner = """-------------------------------------------
          \r[+] NonGhost - version 0.0 - by @n0n [+]
          \r-------------------------------------------
"""

help_message = f"""Description:
    NonGhost redirects all internet traffic through TOR.
    Essentially, it's TorGhost but recreated by a grasshopper.
    O.G project -> https://github.com/SusmithKrishnan/torghost

Usage: python3 {sys.argv[0]} <mode>

Available modes:
    python3 {sys.argv[0]} stop    # Stop NonGhost
    python3 {sys.argv[0]} start   # Start NonGhost
    python3 {sys.argv[0]} switch  # New tor exit node
    python3 {sys.argv[0]} install # Install NonGhost
"""

def print_error(msg):
	error = f"\033[91m{msg}\033[0m"
	print(error)

def check_requirements():
	try:
		from stem import Signal
		from stem.control import Controller
		return True
	except ModuleNotFoundError:
		return False

def check_privs():
	if os.getuid() == 0: return True

def write_tor_config():
	print("[+] Writing tor configuration file")
	tor_config_file = "/etc/tor/nonghostrc"
	with open(tor_config_file, 'w') as tor_config:
		tor_config.write("""
			\rVirtualAddrNetwork 10.0.0.0/10
			\rAutomapHostsOnResolve 1
			\rTransPort 9040
			\rDNSPort 5353
			\rControlPort 9051
			\rRunAsDaemon 1\n""")

def write_resolv_conf():
	print("[+] Writing resolv.conf")
	resolv_conf = "/etc/resolv.conf"
	os.system(f"cp {resolv_conf} {resolv_conf}.bak")
	with open(resolv_conf, 'w') as resolv_file:
		resolv_file.write("nameserver 127.0.0.1\n")

def start_nonghost():

	if not check_requirements():
		print_error("\n[-] Dependencies were missing.")
		print_error(f"[-] Installing requirements first.")
		install_nonghost()



	print("[+] Starting nonghost")
	write_tor_config()
	write_resolv_conf()

	iptables_rules = f"""
		NON_TOR="192.168.1.0/24 192.168.0.0/24"
		TOR_UID={subprocess.getoutput('id -ur debian-tor')}
		TRANS_PORT="9040"
		iptables -F
		iptables -t nat -F
		iptables -t nat -A OUTPUT -m owner --uid-owner $TOR_UID -j RETURN
		iptables -t nat -A OUTPUT -p udp --dport 53 -j REDIRECT --to-ports 5353
		for NET in $NON_TOR 127.0.0.0/9 127.128.0.0/10; do
		 iptables -t nat -A OUTPUT -d $NET -j RETURN
		done
		iptables -t nat -A OUTPUT -p tcp --syn -j REDIRECT --to-ports $TRANS_PORT
		iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
		for NET in $NON_TOR 127.0.0.0/8; do
		 iptables -A OUTPUT -d $NET -j ACCEPT
		done
		iptables -A OUTPUT -m owner --uid-owner $TOR_UID -j ACCEPT
		iptables -A OUTPUT -j REJECT
	"""
	commands = {
		"[+] Stoping tor service": "systemctl stop tor",
		"[+] Terminating any processes on port 9051": "fuser -k 9051/tcp > /dev/null 2>&1",
		"[+] Running new tor daemon": "sudo -u debian-tor tor -f /etc/tor/nonghostrc > /dev/null",
		"[+] Setting up iptables rules": iptables_rules
	}

	for message, command in commands.items():
		print(message)
		os.system(command)

def stop_nonghost():
	print("[+] Stopping nonghost")

	iptables_flush = """
		iptables -P INPUT ACCEPT
		iptables -P FORWARD ACCEPT
		iptables -P OUTPUT ACCEPT
		iptables -t nat -F
		iptables -t mangle -F
		iptables -F
		iptables -X
	"""

	commands = {
		"[+] Restoring resolv.conf": "mv /etc/resolv.conf.bak /etc/resolv.conf",
		"[+] Flushing iptables to default": iptables_flush,
		"[+] Terminating any processes on port 9051": "fuser -k 9051/tcp > /dev/null 2>&1",
		"[+] Restarting NetworkManager": "systemctl restart NetworkManager"
	}
	
	for message, command in commands.items():
		print(message)
		os.system(command)

def switch_tor():
	print("[+] Switching tor exit node.")
	with Controller.from_port(port=9051) as controller:
		controller.authenticate()
		controller.signal(Signal.NEWNYM)

def install_nonghost():
	print("[+] Installing requirements for NonGhost\n")
	install_path = "/usr/local/bin/nonghost"
	os.system("apt update && apt install -y python3-stem iptables tor")
	print("\n[+] Install NonGhost system-wide", end="")
	while True:
		answer = str(input("(Y/n)?? "))
		if answer.lower() == 'y':
			print(f"[+] Installing NonGhost to: {install_path}")
			nonghost_source = open(sys.argv[0].strip()).read()
			with open(install_path, 'w') as f:
				f.write(nonghost_source)
			os.system(f"chmod +x {install_path}")
			break
		elif answer.lower() == 'n':
			print("[+] No system-wide installation")
			break


if __name__ == "__main__":
	modes = {
		"stop":    stop_nonghost,
		"start":   start_nonghost,
		"switch":  switch_tor,
		"install": install_nonghost
	}
	available_modes = list(modes.keys())
	parser = argparse.ArgumentParser(prog="NonGhost", add_help=False)
	parser.add_argument("mode", choices=available_modes, nargs="?")
	parser.add_argument('-h', '--help', action="store_true")
	args = parser.parse_args()

	print(banner, end="")

	try:
		if not check_privs():
			print_error("[+] Run with sudo pls :)")
		elif not args.mode or args.help:
			print(help_message)
		else:
			modes[args.mode]()
	except Exception as e:
		print_error(e)
		sys.exit()
