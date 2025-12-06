import os
import boto3

LOCAL_MODE = os.getenv("LOCAL_MODE") == "true"

AWS_REGION = (
    os.getenv("AWS_REGION")
    or os.getenv("AWS_DEFAULT_REGION")
    or "us-east-1"
)

# Phase-2 env var from SAM (or default)
DDB_TABLE = os.getenv("ARTIFACTS_TABLE", "ArtifactsTable")

# ----------------------------
# LOCAL MODE: in-memory DB
# ----------------------------

if LOCAL_MODE:
    print("⚠️ LOCAL_MODE enabled → using in-memory fake DB")

    _ARTIFACTS: dict[int, dict] = {}
    _RATINGS: dict[int, dict] = {}

    def put_artifact(item: dict):
        _ARTIFACTS[item["id"]] = item

    def get_artifact_by_id(aid: int):
        return _ARTIFACTS.get(aid)

    # === these are the ones your DynamoStore wrapper imports ===
    def scan_all_items():
        return list(_ARTIFACTS.values())

    def delete_artifact_by_id(aid: int) -> bool:
        existed = aid in _ARTIFACTS
        _ARTIFACTS.pop(aid, None)
        _RATINGS.pop(aid, None)
        return existed

    def clear_all_items():
        _ARTIFACTS.clear()
        _RATINGS.clear()

    def put_rating(aid: int, rating: dict):
        _RATINGS[aid] = rating

    def get_rating_by_id(aid: int):
        return _RATINGS.get(aid)

# ----------------------------
# REAL AWS DYNAMODB
# ----------------------------
else:
    dynamo = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamo.Table(DDB_TABLE)

    def put_artifact(item: dict):
        table.put_item(Item=item)

    def get_artifact_by_id(aid: int):
        resp = table.get_item(Key={"id": aid})
        return resp.get("Item")

    # === HERE is where that snippet you pasted goes ===
    def scan_all_items():
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

    def delete_artifact_by_id(aid: int) -> bool:
        table.delete_item(Key={"id": aid})
        return True

    def clear_all_items():
        items = scan_all_items()
        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={"id": item["id"]})

    # ---- rating helpers: store rating inside the same artifact item ----
    def put_rating(aid: int, rating: dict):
        table.update_item(
            Key={"id": aid},
            UpdateExpression="SET rating = :r",
            ExpressionAttributeValues={":r": rating},
        )

    def get_rating_by_id(aid: int):
        resp = table.get_item(Key={"id": aid})
        item = resp.get("Item")
        if not item:
            return None
        return item.get("rating")
