import os
"""Storage abstraction for artifacts and ratings (Dynamo or local).

Exposes a unified interface for CRUD operations and querying across
DynamoDB and local SQLite implementations. Last Updated: 2025-12-14.
"""
import os

def using_dynamo() -> bool:
    return (
        os.getenv("LOCAL_MODE") != "1"
        and os.getenv("AWS_ACCESS_KEY_ID")
        and os.getenv("AWS_SECRET_ACCESS_KEY")
        and os.getenv("DDB_TABLE")
    )

if using_dynamo():
    from bs.src.dynamo_store import DynamoStore as Store
else:
    from bs.src.local_store import LocalStore as Store

store = Store()
