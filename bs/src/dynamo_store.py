import os
import time
import boto3

# ----------------------------
# ENV CONFIG
# ----------------------------

LOCAL_MODE = os.getenv("LOCAL_MODE") == "true"

AWS_REGION = (
    os.getenv("AWS_REGION")
    or os.getenv("AWS_DEFAULT_REGION")
    or "us-east-1"
)

# Default table name (override in Lambda env)
DDB_TABLE = os.getenv("ARTIFACTS_TABLE", "ArtifactsTable")

# ----------------------------
# LOCAL MODE: in-memory DB
# ----------------------------

if LOCAL_MODE:
    print("⚠️ LOCAL_MODE enabled → using in-memory fake DB")

    _MEMDB = {}  # { id: item }

    def put_artifact(item: dict):
        _MEMDB[item["id"]] = item

    def get_artifact_by_id(aid: int):
        return _MEMDB.get(aid)

    def scan_all():
        return list(_MEMDB.values())

    def reset_all():
        _MEMDB.clear()

else:
    # ----------------------------
    # REAL AWS DYNAMODB
    # ----------------------------
    dynamo = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamo.Table(DDB_TABLE)

    def put_artifact(item: dict):
        table.put_item(Item=item)

    def get_artifact_by_id(aid: int):
        resp = table.get_item(Key={"id": aid})
        return resp.get("Item")

    def scan_all():
        items = []
        start_key = None
        while True:
            if start_key:
                resp = table.scan(ExclusiveStartKey=start_key)
            else:
                resp = table.scan()

            items.extend(resp.get("Items", []))

            if "LastEvaluatedKey" not in resp:
                break

            start_key = resp["LastEvaluatedKey"]
        return items

    def reset_all():
        # DynamoDB doesn't support "truncate", so manually delete items
        items = scan_all()
        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={"id": item["id"]})