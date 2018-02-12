from __future__ import absolute_import

import logging
from abc import ABCMeta, abstractmethod

import six

logger = logging.getLogger(__name__)


class BatchError(Exception):
    pass


@six.add_metaclass(ABCMeta)
class BatchClient:

    @abstractmethod
    def list_accounts(self):
        """
        Get account list.
        :return: [list] account list
        """
        raise NotImplementedError()

    @abstractmethod
    def get_account(self, name):
        """
        Get account info.
        :param name: [string] batch account name
        :return: [structures.Account object]
        """
        raise NotImplementedError()

    @abstractmethod
    def create_account(self, name, description, organization, parent_name=None):
        """
        Create account.
        :param name: [string] account name
        :param description: [string] account description
        :param organization: [string] account organization name
        :param parent_name: [string] account parent name. Optional.
        :return: None
        """
        raise NotImplementedError()

    @abstractmethod
    def delete_account(self, name):
        """
        Delete account.
        :param name: [string] account name
        :return: None
        """
        raise NotImplementedError()

    @abstractmethod
    def set_resource_limits(self, account, quotas):
        """
        Set account limits.
        :param account: [string] account name
        :param quotas: [structures.Quotas object] limits
        :return: None
        """
        raise NotImplementedError()

    @abstractmethod
    def get_association(self, user, account):
        """
        Get association user and account.
        :param user: [string] user name
        :param account: [string] account name
        :return: [structures.Association object]
        """
        raise NotImplementedError()

    @abstractmethod
    def create_association(self, username, account, default_account=None):
        """
        Create association user and account
        :param username: [string] user name
        :param account: [string] account name
        :param default_account: [string] default account name. Optional.
        :return: None
        """
        raise NotImplementedError()

    @abstractmethod
    def delete_association(self, username, account):
        """
        Delete_association user and account.
        :param username: [string] user name
        :param account: [string] account name
        :return: None
        """
        raise NotImplementedError()

    @abstractmethod
    def get_usage_report(self, accounts):
        """
        Get usages records.
        :param accounts: [string] account name
        :return: [dict]
        """
        raise NotImplementedError()


@six.add_metaclass(ABCMeta)
class BatchProvider:
    @staticmethod
    @abstractmethod
    def get_client_class():
        """
        Get BatchClient interface implementation.
        :return: [BatchClient class]
        """
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def get_price(allocation, package):
        """
        Get allocation price.
        :param allocation: [Allocation object]
        :param package: [Package object]
        :return: [number]
        """
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def get_details(allocation):
        """
        Get usages info.
        :param allocation: [Allocation object]
        :return: [dict]
        """
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def get_quotas(allocation):
        """
        Get allocation quotas.
        :param allocation: [Allocation object]
        :return: [structures.Quotas object]
        """
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def update_allocation_usage(allocation, usage):
        """
        Update allocation usage.
        :param allocation: [Allocation object]
        :param usage: [dict].
        :return: None
        """
        raise NotImplementedError()
