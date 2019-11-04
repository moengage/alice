import traceback

from alice.commons.base import PushPayloadParser
from alice.config.message_template import ISSUE_FOUND, DOC_CHECK_NOT_FOUND
from alice.helper.constants import ISSUE_LINK, EXTEND_ALICE
from alice.helper.log_utils import LOG
from alice.checker_impl import CheckImpl
from alice.helper.jenkins_helper import JenkinsHelper


class RunChecks(object):
    def execute_check(self, ci, check):
        LOG.debug("************* Starting check=%s *****************" % check)
        response = getattr(ci, check)()
        print(check)
        LOG.debug("for check= %s, response= %s"%(check, response))

    def run_checks(self, data):
        ci = CheckImpl(PushPayloadParser(payload=data))
        response = {}
        checks = ci.pr.config.checks
        if ci.pr.is_sensitive_branch:
            if len(checks) == 0:
                import inspect
                method_names = [attr for attr in dir(ci) if inspect.ismethod(getattr(ci, attr))]
                for check in method_names:
                    if check != "__init__":
                        self.execute_check(ci, check)
            else:
                try:
                    for check in checks:
                        try:
                            self.execute_check(ci, check)
                        except AttributeError:
                            LOG.debug("Exception in Run Checks", exc_info=traceback)
                            raise CheckNotFoundException(check)
                except Exception as e:
                    LOG.debug("Exception in Run Checks", exc_info=traceback)
                    if 'invalid_auth' not in str(e):
                        raise Exception(str(e) + ISSUE_FOUND.format(issue_link=ISSUE_LINK))
            return response
        else:
            JenkinsHelper(ci.pr).change_status(ci.pr.statuses_url, "success", context="shield-syntax-validator-python",
                                       description="Skipped Testing as not sensitive branch",
                                       details_link="")
            JenkinsHelper(ci.pr).change_status(ci.pr.statuses_url, "success", context="shield-unit-test-python",
                                       description="Skipped Testing as not sensitive branch",
                                       details_link="")

        LOG.info("skipped because '%s' is not sensitive branch" % ci.pr.base_branch)
        return {"msg": "skipped because '%s' is not sensitive branch" % ci.pr.base_branch}


class CheckNotFoundException(Exception):
    def __init__(self, method_name):
        super(CheckNotFoundException, self).__init__(DOC_CHECK_NOT_FOUND.format(check_name=method_name,
                                                                                doc_link=EXTEND_ALICE))
