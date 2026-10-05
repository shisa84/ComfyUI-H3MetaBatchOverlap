from comfy_api.latest import ComfyExtension

from .nodes import NODES


class H3MetaBatchOverlapExtension(ComfyExtension):
    async def get_node_list(self):
        return NODES


async def comfy_entrypoint() -> H3MetaBatchOverlapExtension:
    return H3MetaBatchOverlapExtension()
