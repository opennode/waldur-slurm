from nodeconductor.core import executors as core_executors, tasks as core_tasks


class AllocationDeleteExecutor(core_executors.DeleteExecutor):

    @classmethod
    def get_task_signature(cls, volume, serialized_allocation, **kwargs):
        return core_tasks.BackendMethodTask().si(
            serialized_allocation,
            'delete_allocation',
            state_transition='begin_deleting'
        )
