import xraydb


def edge_energy(edge_name):
    E0 = xraydb.xray_edge(*edge_name.split("_")).energy
    return E0
