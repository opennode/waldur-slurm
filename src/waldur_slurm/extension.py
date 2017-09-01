from nodeconductor.core import NodeConductorExtension


class SLURMExtension(NodeConductorExtension):
    class Settings:
        WALDUR_SLURM = {
            'ACCOUNT_NAME_PREFIX': 'waldur_',
            'PRIVATE_KEY_PATH': '/etc/waldur/id_rsa',
        }

    @staticmethod
    def django_app():
        return 'waldur_slurm'

    @staticmethod
    def rest_urls():
        from .urls import register_in
        return register_in
