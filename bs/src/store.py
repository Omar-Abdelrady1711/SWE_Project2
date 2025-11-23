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
