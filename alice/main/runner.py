import logging
import requests
import simplejson as json
import traceback
from enum import Enum
from flask import Flask, request, jsonify, abort
from logging import Formatter, FileHandler

from alice.checker_impl import CheckImpl
from alice.commons.base import Base, PushPayloadParser
from alice.config.message_template import *
from alice.helper.constants import *
from alice.helper.file_utils import write_to_file_from_top, clear_file
from alice.helper.github_helper import GithubHelper, PRFilesNotFoundException
from alice.helper.log_utils import LOG
from alice.helper.slack_helper import SlackHelper


class RunChecks:

    def execute_check(self, ci, check):
        LOG.debug("************* Starting check=%s *****************" % check)
        response = getattr(ci, check)()
        LOG.debug("for check=%s, response=%s"%(check, response))

    def run_checks(self, request, data):
        ci = CheckImpl(PushPayloadParser(request, payload=data))
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
                        self.execute_check(ci, check)
                except Exception,e:
                    LOG.debug("Exception in Run Checks", exc_info=traceback)
                    if isinstance(e, AttributeError):
                        raise CheckNotFoundException(check)
                    else:
                        raise Exception(str(e)+ISSUE_FOUND.format(issue_link=issue_link))
            return response
        LOG.info("skipped because '%s' is not sensitive branch" % ci.base_branch)
        return {"msg":"skipped because '%s' is not sensitive branch" %ci.base_branch}



class CheckNotFoundException(Exception):
    def __init__(self, method_name):
        super(CheckNotFoundException, self).__init__(DOC_CHECK_NOT_FOUND.format(check_name=method_name, doc_link=extend_alice))



