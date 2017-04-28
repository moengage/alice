import logging
import os
from alice.helper.file_utils import get_dict_from_config_file

LOG = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d]')
handler.setFormatter(formatter)
LOG.addHandler(handler)
config_file = os.environ["config"]
config = get_dict_from_config_file(config_file)
debug = config.get('debug', False)
if debug:
    LOG.setLevel(logging.DEBUG)
else:
    LOG.setLevel(logging.INFO)