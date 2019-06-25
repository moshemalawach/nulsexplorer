import aioipfs
import asyncio
import aiohttp
import logging

from nulsexplorer.modules.register import register_tx_processor

LOGGER = logging.getLogger('ipfs_module')


async def add_file(fileobject, filename):
    async with aiohttp.ClientSession() as session:
        from nulsexplorer.web import app
        url = "http://%s:%d/api/v0/add" % (app['config'].ipfs.host.value,
                                           app['config'].ipfs.port.value)
        data = aiohttp.FormData()
        data.add_field('path',
                       fileobject,
                       filename=filename)

        resp = await session.post(url, data=data)
        return await resp.json()


async def get_ipfs_api(timeout=60):
    from nulsexplorer.web import app
    host = app['config'].ipfs.host.value
    port = app['config'].ipfs.port.value

    return aioipfs.AsyncIPFS(host=host, port=port, read_timeout=timeout)


async def get_json(hash, timeout=2):
    # loop = asyncio.get_event_loop()
    api = await get_ipfs_api(timeout=timeout)
    try:
        result = await api.cat(hash)
        result = json.loads(result)
    except (concurrent.futures.TimeoutError, json.JSONDecodeError):
        result = None
    finally:
        await api.close()

    return result


async def pin_add(hash, timeout=5):
    # loop = asyncio.get_event_loop()
    api = await get_ipfs_api(timeout=timeout)
    try:
        result = None
        async for ret in api.pin.add(hash):
            result = ret
    except (concurrent.futures.TimeoutError, json.JSONDecodeError):
        result = None
    finally:
        await api.close()

    return result


async def add_json(value):
    # loop = asyncio.get_event_loop()
    api = await get_ipfs_api()
    try:
        result = await api.add_json(value)
    finally:
        await api.close()

    return result['Hash']


async def process_transfer_ipfs_remark(tx):
    # This function takes a tx dict and modifies it in place.
    # we assume we have access to a config since we are in a processor
    from nulsexplorer.web import app
    if tx.remark.startswith(b'IPFS;'):
        parts = tx.remark.split(b';')
        info = {
            'type': 'ipfs',
            'success': False
        }

        if app['config'].ipfs.enabled.value:
            try:
                if parts[1] == b"A":
                    # Ok, we have an aggregate.
                    # Maybe check object size to avoid ddos attack ?
                    info['aggregate'] = await get_json(parts[2])
                elif parts[1] == b"P":
                    info['post'] = await get_json(parts[2])
                else:
                    info['extended'] = await get_json(parts[1])

                info['success'] = True
            except Exception as e:
                LOGGER.warning("Can't retrieve the ipfs hash %s" % parts[1])
                LOGGER.exception(e)

        tx.module_data.update(info)

register_tx_processor(process_transfer_ipfs_remark, step="pre")
