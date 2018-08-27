from logging import getLogger
import aiocron
import asyncio
from datetime import date, time, timezone, datetime, timedelta

LOGGER = getLogger("JOBS")

@aiocron.crontab('0 */4 * * *', start=False)
async def update_addresses_balances():
    from nulsexplorer.model.blocks import get_last_block_height
    from nulsexplorer.web.controllers.addresses import addresses_unspent_txs
    LOGGER.info("updating addresses balances")
    last_block = await get_last_block_height()
    unspent = await addresses_unspent_txs(last_block, output_collection="cached_unspent")
    await asyncio.sleep(0)

def start_jobs():
    update_addresses_balances.start()
