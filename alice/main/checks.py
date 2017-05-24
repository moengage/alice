from alice.main.actor import Actor


class Checks(object):
    def __init__(self, pr_payload):
        self.actor = Actor(pr=pr_payload)


    def tech_review(self):
        """
        checks for +1 in review approved
        :return:
        """
        return self.actor.validate_tech_approval()


    def github_comment_guidelines(self):
        """
        add comment on opened PR
        :return:
        """
        return self.actor.comment_on_pr()

    def notify_channel_on_merge(self):
        """
        store merged PR data to respective channel
        :return:
        """
        return self.actor.notify_channel_on_merge()

    def notify_lead_on_given_action(self):
        """
        keep lead posted on particular action on sensitive branch
        :return:
        """
        # if self.pr.is_opened:
        return self.actor.notify_on_action()

    def remind_direct_release_guideline_on_merge(self):
        """
        remind the member who had raised PR to any of the sensitive branch to follow specific release guideline
        :return:
        """
        return self.actor.remind_direct_release_guideline_on_merge()

    def close_dangerous_pr(self):
        """
        senses
        :return:
        """
        return self.actor.close_dangerous_pr()

    def notify_on_sensitive_files_touched(self):
        return self.actor.notify_if_sensitive_modified()

    def product_review(self):
        return self.actor.validate_product_approval()

    def notify_code_freeze(self):
        return self.actor.notify_code_freeze()

    def notify_qa_sign_off(self):
        return self.actor.notify_qa_sign_off()



    """ TO DO """
    # def notify_qa_sign_off(self):
    #     return self.actor.notify_qa_sign()
    #
    # def notify_to_add_release_notes_for_next_release(self):
    #     pass
    #
    # def announce_code_freeze(self):
    #     pass
    #
    # def ci_lint_checker(self):
    #     pass
    #
    # def ci_unit_tests(self):
    #     pass

