from django.contrib import admin

from nodeconductor.structure import admin as structure_admin

from .models import SlurmService, SlurmServiceProjectLink, Allocation


admin.site.register(SlurmService, structure_admin.ServiceAdmin)
admin.site.register(SlurmServiceProjectLink, structure_admin.ServiceProjectLinkAdmin)
admin.site.register(Allocation, structure_admin.ResourceAdmin)
