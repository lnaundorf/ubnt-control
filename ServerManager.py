import socket
import struct
import ping
from paramiko import SSHClient, WarningPolicy

# Paramiko import will fail since it import Crypto and not crypto. Rename the folder to make it work. Tip from:
# http://redino.net/blog/2014/05/module-named-crypto-publickey/

ping_timeout = 0.1
ping_packet_size = 1

def wake_on_lan(macaddress):
    """ Switches on remote computers using WOL. """

    # Check macaddress format and try to compensate.
    if len(macaddress) == 12:
        pass
    elif len(macaddress) == 12 + 5:
        sep = macaddress[2]
        macaddress = macaddress.replace(sep, '')
    else:
        raise ValueError('Incorrect MAC address format')

    # Pad the synchronization stream.
    data = ''.join(['FFFFFFFFFFFF', macaddress * 20])
    send_data = ''

    # Split up the hex values and pack.
    for i in range(0, len(data), 2):
        send_data = ''.join([send_data,
                             struct.pack('B', int(data[i: i + 2], 16))])

    # Broadcast it to the LAN.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(send_data, ('<broadcast>', 7))


def shutdown(host, username, password):
    print "shutdown: " + host
    client = SSHClient()
    # TODO: verify host key
    client.set_missing_host_key_policy(WarningPolicy())
    client.connect(host, username=username, password=password)

    # in order for the following command to work, the user needs to have an entry in /etc/sudoers of the following form
    # remote ALL = (root) NOPASSWD: /sbin/shutdown
    stdin, stdout, stderr = client.exec_command('sudo shutdown -h now')
    print "stdin: " + str(stdin)
    print "stdout: " + str(stdout)
    print "stderr: " + str(stderr)
    client.close()


def server_is_up(host):
    delay = ping.do_one(host, ping_timeout, ping_packet_size)
    print "ping delay: " + str(delay)
    if delay is not None:
        return 1
    else:
        return 0;

