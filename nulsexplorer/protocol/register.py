
# We will register here handlers for the tx types
TX_TYPES_REGISTER = dict()

# We will register here processors for the tx by types
TX_PROCESSOR_REGISTER = dict()

def register_tx_type(tx_types, handler_class):
    if not isinstance(tx_types, (list, tuple)):
        tx_types = [tx_types]

    for tx_type in tx_types:
        TX_TYPES_REGISTER[tx_type] = handler_class

def register_tx_processor(tx_types, processor_function):
    if not isinstance(tx_types, (list, tuple)):
        tx_types = [tx_types]

    for tx_type in tx_types:
        TX_PROCESSOR_REGISTER[tx_type] = processor_function
