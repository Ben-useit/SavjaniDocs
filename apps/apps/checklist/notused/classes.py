from __future__ import unicode_literals

from common.classes import PropertyHelper


class DocumentRegisterHelper(PropertyHelper):
    @staticmethod
    @property
    def constructor(*args, **kwargs):
        return DocumentRegisterHelper(*args, **kwargs)

    def get_result(self, name):
        return self.instance.register.first().file_no

class DocumentQuotationHelper(PropertyHelper):
    @staticmethod
    @property
    def constructor(*args, **kwargs):
        return DocumentQuotationHelper(*args, **kwargs)

    def get_result(self, name):
        return self.instance.quotation_set.first().file_no
