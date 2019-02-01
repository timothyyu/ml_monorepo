import properties
import re
import os
# from calc.optmaster import Forecast

def load_source_config(name):
    config_file = "%s/sources/%s.py" % (os.environ["CONFIG_DIR"], name)
    config = eval(open(config_file, 'rb').read())

    # Fill in missing optional values with defaults
    config.setdefault('sub_dirs', "")
    config.setdefault('prefix', "")
    config.setdefault('flag', "")
    config.setdefault('tz', "UTC")
    config.setdefault('modtime_grace', 1.5)
    config.setdefault("exec_regex",None)

    config["modtime_grace"] = int(config["modtime_grace"])
    prefix_regex = re.sub("%[a-zA-Z]", "[0-9]+", config["prefix"])
    config["local_regex"] = prefix_regex + config["regex"] + "\.[0-9a-f]{8}"
    config["sub_dirs"] = config["sub_dirs"].split(":")

    return config

def load_trade_config(filename):
    p = properties.Properties()
    p.load(open(filename))
    config = p.getPropertyDict()

    #convert any floats that happen to be in there
#     for key, value in config.iteritems():
#         try:
#             config[key] = float(value)
#         except ValueError:
#             pass

    config['servers'] = config['servers'].strip().split()
    config['servers'] = [a.split(':') for a in config['servers']]
    config['servers'] = [(a[0], int(a[1])) for a in config['servers']]
    return config

# def load_opt_config(config_file):
#     p = properties.Properties()
#     p.load(open(config_file))
#     config = p.getPropertyDict()

#     sigma_hand = dict()
#     rvars = list()
#     for key, value in config.iteritems():
#         if key[0:6] == "sigma_":
#             (calc_frac, hand_value) = value.split(" ")
#             calc_frac = float(calc_frac)
#             hand_value = float(hand_value)
#             if (calc_frac < 0 or calc_frac > 1):
#                 raise Exception("Invalid calc_frac value")
#             sigma_hand[key[6:]] = (calc_frac, hand_value)
#         elif key.startswith("rvar_"):
#             fields = value.split(" ")
#             namesiter = iter(fields)
#             names = zip(namesiter, namesiter)
#             (xnames, coeffs) = zip(*names)
#             xnames = list(xnames)
#             coeffs = list(coeffs)
#             coeffs = [float(coeff) for coeff in coeffs]
#             rvars.append(Forecast(name=key[5:], xnames=xnames, coeffs=coeffs, horizon=None, weight=None, allow_missing=None))
#         else:
#             config[key] = float(value)
#     return (config, rvars, sigma_hand)
