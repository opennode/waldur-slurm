from . import views


def register_in(router):
    router.register(r'slurm', views.SLURMServiceViewSet, base_name='slurm')
    router.register(r'slurm-service-project-link', views.SLURMServiceProjectLinkViewSet,
                    base_name='slurm-spl')
    router.register(r'slurm-allocation', views.AllocationViewSet, base_name='slurm-allocation')
