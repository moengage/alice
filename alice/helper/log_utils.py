import logging
import os
from alice.helper.common_utils import getDictFromJson

LOG = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d]')
handler.setFormatter(formatter)
LOG.addHandler(handler)
config_file = os.environ["config"]
config = getDictFromJson(config_file)
debug = config.get('debug', False)
if debug:
    LOG.setLevel(logging.DEBUG)
else:
    LOG.setLevel(logging.INFO)