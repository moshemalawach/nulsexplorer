# We will register here processors for the tx by types
# Pre-processor is before the insertion
TX_PREPROCESS_REGISTER = dict()

# Post-processor is after the insertion
TX_POSTPROCESS_REGISTER = dict()

# We will register here handlers for the tx types
TX_TYPES_REGISTER = dict()

def register_tx_type(tx_types, handler_class):
    if not isinstance(tx_types, (list, tuple)):
        tx_types = [tx_types]

    for tx_type in tx_types:
        TX_TYPES_REGISTER[tx_type] = handler_class

def register_tx_processor(handler, tx_types=0, step = "pre"):
    if not isinstance(tx_types, (list, tuple)):
        tx_types = [tx_types]

    registry = TX_PREPROCESS_REGISTER
    if step == "post":
        registry = TX_POSTPROCESS_REGISTER

    for tx_type in tx_types:
        registry.setdefault(tx_type, []).append(handler)

async def process_tx(tx, step="pre"):
    registry = TX_PREPROCESS_REGISTER
    if step == "post":
        registry = TX_POSTPROCESS_REGISTER

    for handler in registry.setdefault(0, []):
        await handler(tx)

    for handler in registry.setdefault(tx.type, []):
        await handler(tx)
