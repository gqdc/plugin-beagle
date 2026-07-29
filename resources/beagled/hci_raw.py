# hci_raw.py
#
# Remplacement minimal, sans dépendance externe, du sous-module bas niveau
# de PyBluez `bluetooth._bluetooth`, tel qu'utilisé par beagled.py / blescan.py.
#
# Ne couvre QUE ce qui est réellement appelé dans ces deux fichiers :
#   - hci_open_dev(dev_id)
#   - SOL_HCI, HCI_FILTER
#   - HCI_EVENT_PKT, EVT_INQUIRY_RESULT_WITH_RSSI, EVT_NUM_COMP_PKTS, EVT_DISCONN_COMPLETE
#   - hci_filter_new(), hci_filter_all_events(flt), hci_filter_set_ptype(flt, ptype)
#   - hci_send_cmd(sock, ogf, ocf, data)
#
# S'appuie uniquement sur le module socket standard de Python
# (socket.AF_BLUETOOTH / socket.BTPROTO_HCI, disponibles nativement sous
# Linux depuis Python 3.3). Aucune extension C, aucun pip install requis.
#
# Les valeurs numériques ci-dessous sont des constantes stables de l'ABI
# HCI du noyau Linux / BlueZ (bluetooth/hci.h), inchangées depuis des années.

import socket
import struct

# ---- Constantes HCI ----
SOL_HCI = 0          # niveau socket pour setsockopt/getsockopt HCI
HCI_FILTER = 2        # option socket "filtre HCI"

HCI_COMMAND_PKT = 0x01
HCI_EVENT_PKT = 0x04

EVT_DISCONN_COMPLETE = 0x05
EVT_NUM_COMP_PKTS = 0x13
EVT_INQUIRY_RESULT_WITH_RSSI = 0x22


class error(Exception):
    """Equivalent de bluetooth._bluetooth.error, pour compatibilité."""
    pass


def hci_open_dev(dev_id):
    """
    Equivalent de bluez.hci_open_dev(dev_id) de PyBluez :
    ouvre un socket HCI brut et le lie à l'adaptateur demandé (0 pour hci0, etc).
    Nécessite les mêmes droits que l'ancien code (root / CAP_NET_RAW).
    """
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW, socket.BTPROTO_HCI)
    sock.bind((dev_id,))
    return sock


HCI_FILTER_SIZE = 16  # taille réelle de struct hci_filter côté noyau sur cette
                       # plateforme (4+4+4+2=14 logiques, paddés à 16 par
                       # l'alignement 4 octets du compilateur ; vérifié
                       # empiriquement via setsockopt sur la machine cible)


def hci_filter_new():
    # struct hci_filter { uint32_t type_mask; uint32_t event_mask[2]; uint16_t opcode; }
    # 14 octets "logiques", mais paddés à 16 par le noyau sur cette architecture.
    return bytearray(HCI_FILTER_SIZE)


def hci_filter_all_events(flt):
    flt[4:12] = b'\xff' * 8


def hci_filter_set_ptype(flt, ptype):
    byte_index, bit_index = divmod(ptype, 8)
    flt[byte_index] |= (1 << bit_index)


def hci_send_cmd(sock, ogf, ocf, data=b''):
    """
    Construit et envoie un paquet de commande HCI brut :
    [type=0x01][opcode LE 16 bits][longueur][paramètres]
    """
    opcode = (ocf & 0x03ff) | (ogf << 10)
    pkt = struct.pack('<BHB', HCI_COMMAND_PKT, opcode, len(data)) + data
    sock.send(pkt)
