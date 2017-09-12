from django.utils.functional import cached_property

from nodeconductor.structure.tests.fixtures import ProjectFixture

from . import factories


class SlurmFixture(ProjectFixture):

    @cached_property
    def service(self):
        return factories.SlurmServiceFactory(customer=self.customer)

    @cached_property
    def spl(self):
        return factories.SlurmServiceProjectLinkFactory(project=self.project, service=self.service)

    @cached_property
    def allocation(self):
        return factories.AllocationFactory(service_project_link=self.spl)
